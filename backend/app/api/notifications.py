from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.models import Notification
from app.notifications.delivery import email_configured
from app.notifications.dispatcher import dispatch_for_user
from app.schemas import (
    NotificationFeedOut,
    NotificationOut,
    PreferencesIn,
    UserOut,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _build_feed(
    db, user, limit: int = 50, unread_only: bool = False
) -> NotificationFeedOut:
    """Сглобява отговора. Отделена от рута, за да може да се ползва и от
    другите операции — извикване на самия рут би подало обектите на FastAPI
    вместо стойности."""
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))

    items = db.scalars(
        query.order_by(Notification.created_at.desc()).limit(limit)
    ).all()

    unread = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id, Notification.read_at.is_(None)
        )
    )

    return NotificationFeedOut(
        unread_count=unread or 0,
        email_delivery_enabled=email_configured(),
        items=[NotificationOut.model_validate(i) for i in items],
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: CurrentUser, db: DbSession) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Известието не е намерено."
        )
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification


@router.get("", response_model=NotificationFeedOut)
def list_notifications(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    unread_only: bool = Query(default=False),
) -> NotificationFeedOut:
    return _build_feed(db, user, limit, unread_only)


@router.post("/read-all", response_model=NotificationFeedOut)
def mark_all_read(user: CurrentUser, db: DbSession) -> NotificationFeedOut:
    now = datetime.now(timezone.utc)
    for notification in db.scalars(
        select(Notification).where(
            Notification.user_id == user.id, Notification.read_at.is_(None)
        )
    ).all():
        notification.read_at = now
    db.commit()
    return _build_feed(db, user)


@router.post("/check-now", response_model=NotificationFeedOut)
def check_now(user: CurrentUser, db: DbSession) -> NotificationFeedOut:
    """Оценява кредитите веднага, без да се чака нощната задача."""
    dispatch_for_user(db, user)
    return _build_feed(db, user)


@router.put("/preferences", response_model=UserOut)
def update_preferences(
    payload: PreferencesIn, user: CurrentUser, db: DbSession
) -> UserOut:
    user.notify_email = payload.notify_email
    user.notify_push = payload.notify_push
    user.alert_threshold_eur = payload.alert_threshold_eur
    user.risk_tolerance = payload.risk_tolerance
    db.commit()
    db.refresh(user)
    return user
