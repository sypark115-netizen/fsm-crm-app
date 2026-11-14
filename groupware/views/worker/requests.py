"""[화면 B-2] 연장근로·연차 전자결재 신청."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.auth import require_role
from core.models import RequestType, Role
from services import approvals

user = require_role(Role.WORKER, Role.ADMIN, Role.MARKETER)

TYPE_LABEL = {RequestType.OVERTIME: "연장근로", RequestType.ANNUAL: "연차", RequestType.HALF_DAY: "반차"}
STATUS_LABEL = {"pending": "⏳ 대기", "approved": "✅ 승인", "rejected": "❌ 반려"}

st.title("📝 연장근로·연차 신청")

with st.form("request_form", clear_on_submit=True):
    req_type = st.segmented_control("구분", list(TYPE_LABEL), format_func=TYPE_LABEL.get,
                                    default=RequestType.OVERTIME)
    target = st.date_input("날짜", value=date.today())
    hours = st.number_input("연장 근무 시간 (연장근로만)", min_value=0.0, max_value=approvals.MAX_OVERTIME_PER_DAY,
                            step=0.5, value=1.0)
    reason = st.text_area("사유", placeholder="예: OO현장 타일 마감 일정 지연으로 야간 작업")
    if st.form_submit_button("신청하기", type="primary", width="stretch"):
        try:
            approvals.submit(user.id, req_type or RequestType.OVERTIME, target, hours, reason)
            st.success("신청되었습니다. 관리자 대시보드에 즉시 반영됩니다.")
        except ValueError as e:
            st.error(str(e))

st.subheader("내 신청 내역")
rows = approvals.list_requests(user_id=user.id)
if not rows:
    st.caption("신청 내역이 없습니다.")
else:
    st.dataframe(pd.DataFrame([{
        "날짜": r.target_date, "구분": TYPE_LABEL[r.type], "시간": r.hours or None,
        "사유": r.reason, "상태": STATUS_LABEL[r.status.value], "반려사유": r.reject_reason or "",
    } for r in rows]), hide_index=True, width="stretch")
