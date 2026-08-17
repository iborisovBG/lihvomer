"""Свързва правилата, записа и доставката."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Notification, User
from app.notifications.delivery import (
    EmailNotConfigured,
    email_configured,
    send_email,
)
from app.notifications.rules import evaluate_user

logger = logging.getLogger(__name__)


def dispatch_for_user(db: Session, user: User) -> tuple[int, int, int]:
    """Връща (нови известия, изпратени имейли, грешки при изпращане)."""
    drafts = evaluate_user(db, user)
    created = 0

    for draft in drafts:
        exists = db.scalar(
            select(Notification.id).where(
                Notification.user_id == draft.user_id,
                Notification.dedupe_key == draft.dedupe_key,
            )
        )
        if exists:
            continue

        notification = Notification(
            user_id=draft.user_id,
            loan_id=draft.loan_id,
            kind=draft.kind,
            severity=draft.severity,
            dedupe_key=draft.dedupe_key,
            title_bg=draft.title_bg,
            body_bg=draft.body_bg,
            action_bg=draft.action_bg,
            payload=draft.payload,
        )
        db.add(notification)
        try:
            db.commit()
        except IntegrityError:
            # Друг работник е записал същото известие междувременно.
            db.rollback()
            continue
        created += 1

    sent = failed = 0
    if user.notify_email and email_configured():
        pending = db.scalars(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.emailed_at.is_(None),
            )
        ).all()
        for notification in pending:
            try:
                send_email(user.email, notification)
                notification.emailed_at = datetime.now(timezone.utc)
                notification.email_error = None
                sent += 1
            except EmailNotConfigured:
                break
            except Exception as exc:
                notification.email_error = f"{type(exc).__name__}: {exc}"
                failed += 1
                logger.warning(
                    "Известие %s не беше изпратено: %s", notification.id, exc
                )
        db.commit()

    return created, sent, failed


def dispatch_all(db: Session) -> dict:
    users = db.scalars(select(User).where(User.is_active.is_(True))).all()
    totals = {"users": len(users), "created": 0, "emailed": 0, "email_failed": 0}

    for user in users:
        created, sent, failed = dispatch_for_user(db, user)
        totals["created"] += created
        totals["emailed"] += sent
        totals["email_failed"] += failed

    totals["email_configured"] = email_configured()
    return totals
