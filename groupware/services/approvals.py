"""연장근로/연차 전자결재."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from core.database import get_session
from core.models import RequestStatus, RequestType, WorkRequest

MAX_OVERTIME_PER_DAY = 4.0  # 주 52시간(연장 12h/주) 가이드 내 일 단위 상한, 회사 정책에 맞게 조정


def submit(user_id: int, req_type: RequestType, target_date: date, hours: float, reason: str) -> WorkRequest:
    if not reason.strip():
        raise ValueError("사유를 입력해 주세요.")
    if req_type == RequestType.OVERTIME and not (0 < hours <= MAX_OVERTIME_PER_DAY):
        raise ValueError(f"연장근로는 0~{MAX_OVERTIME_PER_DAY:g}시간 사이로 입력해 주세요.")
    with get_session() as s:
        req = WorkRequest(user_id=user_id, type=req_type, target_date=target_date,
                          hours=hours if req_type == RequestType.OVERTIME else 0.0, reason=reason.strip())
        s.add(req)
        s.flush()
        return req


def list_requests(user_id: int | None = None, status: RequestStatus | None = None) -> list[WorkRequest]:
    with get_session() as s:
        q = select(WorkRequest).options(joinedload(WorkRequest.user)).order_by(WorkRequest.created_at.desc())
        if user_id is not None:
            q = q.where(WorkRequest.user_id == user_id)
        if status is not None:
            q = q.where(WorkRequest.status == status)
        return list(s.scalars(q))


def pending_count() -> int:
    with get_session() as s:
        return s.scalar(select(func.count()).select_from(WorkRequest)
                        .where(WorkRequest.status == RequestStatus.PENDING)) or 0


def decide(request_id: int, approver_id: int, approve: bool, reject_reason: str | None = None) -> None:
    with get_session() as s:
        req = s.get(WorkRequest, request_id)
        if req is None or req.status != RequestStatus.PENDING:
            raise ValueError("이미 처리되었거나 존재하지 않는 신청입니다.")
        req.status = RequestStatus.APPROVED if approve else RequestStatus.REJECTED
        req.approver_id, req.decided_at = approver_id, datetime.now()
        req.reject_reason = None if approve else (reject_reason or "")
        # TODO: 알림 채널(카카오 알림톡/슬랙 웹훅) 연동 지점
