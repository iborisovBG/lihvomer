from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.analytics.forecast import InsufficientData
from app.deps import CurrentUser, DbSession
from app.models import UserLoan
from app.schemas import LoanIn, LoanOut, LoanProjection
from app.services.projections import project_loan

router = APIRouter(prefix="/api/v1/user/loans", tags=["loans"])


def _owned_loan(db, user, loan_id: int) -> UserLoan:
    loan = db.scalar(
        select(UserLoan).where(UserLoan.id == loan_id, UserLoan.user_id == user.id)
    )
    if loan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Кредитът не е намерен."
        )
    return loan


@router.get("", response_model=list[LoanOut])
def list_loans(user: CurrentUser, db: DbSession) -> list[UserLoan]:
    return list(
        db.scalars(
            select(UserLoan)
            .where(UserLoan.user_id == user.id)
            .order_by(UserLoan.created_at)
        ).all()
    )


@router.post("", response_model=LoanOut, status_code=status.HTTP_201_CREATED)
def create_loan(payload: LoanIn, user: CurrentUser, db: DbSession) -> UserLoan:
    loan = UserLoan(user_id=user.id, **payload.model_dump())
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.put("/{loan_id}", response_model=LoanOut)
def update_loan(
    loan_id: int, payload: LoanIn, user: CurrentUser, db: DbSession
) -> UserLoan:
    loan = _owned_loan(db, user, loan_id)
    for field, value in payload.model_dump().items():
        setattr(loan, field, value)
    db.commit()
    db.refresh(loan)
    return loan


@router.delete(
    "/{loan_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_loan(loan_id: int, user: CurrentUser, db: DbSession) -> None:
    loan = _owned_loan(db, user, loan_id)
    db.delete(loan)
    db.commit()


@router.get("/projections", response_model=list[LoanProjection])
def projections(user: CurrentUser, db: DbSession) -> list[LoanProjection]:
    loans = db.scalars(
        select(UserLoan).where(UserLoan.user_id == user.id).order_by(UserLoan.created_at)
    ).all()

    try:
        return [project_loan(db, loan) for loan in loans]
    except InsufficientData as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
