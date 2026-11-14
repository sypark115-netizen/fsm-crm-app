"""관리자 대시보드: 오늘 출근 현황 + 결재 대기 + 미발행 사진."""
from __future__ import annotations

from datetime import date

import streamlit as st
from sqlalchemy import func, select

from core.auth import require_role
from core.database import get_session
from core.models import Attendance, Photo, Role, User
from services import approvals

require_role(Role.ADMIN)

st.title("📊 대시보드")

with get_session() as s:
    total = s.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True), User.role == Role.WORKER))
    present = s.scalar(select(func.count()).select_from(Attendance)
                       .where(Attendance.work_date == date.today(), Attendance.check_in.is_not(None)))
    unpublished = s.scalar(select(func.count()).select_from(Photo).where(Photo.is_published.is_(False)))

pending = approvals.pending_count()
c1, c2, c3, c4 = st.columns(4)
c1.metric("오늘 출근", f"{present} / {total}")
c2.metric("결재 대기", pending)
c3.metric("미발행 현장사진", unpublished)
c4.metric("기준일", f"{date.today():%m/%d}")

if pending:
    st.warning(f"처리 대기 중인 결재 {pending}건이 있습니다.")
    st.page_link("views/admin/approvals.py", label="전자결재 바로가기", icon="✅")
