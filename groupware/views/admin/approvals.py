"""연장근로·연차 승인/반려."""
from __future__ import annotations

import streamlit as st

from core.auth import require_role
from core.models import RequestStatus, RequestType, Role
from services import approvals

admin = require_role(Role.ADMIN)
TYPE_LABEL = {RequestType.OVERTIME: "연장근로", RequestType.ANNUAL: "연차", RequestType.HALF_DAY: "반차"}

st.title("✅ 전자결재 승인")

# 자동 새로고침: 30초마다 대기건 갱신 (fragment 만 재실행)
@st.fragment(run_every="30s")
def pending_list() -> None:
    rows = approvals.list_requests(status=RequestStatus.PENDING)
    st.caption(f"대기 {len(rows)}건 · 30초마다 자동 갱신")
    for r in rows:
        with st.container(border=True):
            st.markdown(f"**{r.user.name}** ({r.user.emp_no}) · {TYPE_LABEL[r.type]} · "
                        f"{r.target_date:%Y-%m-%d}" + (f" · **{r.hours:g}시간**" if r.hours else ""))
            st.write(r.reason)
            c1, c2, c3 = st.columns([1, 1, 2])
            reject_reason = c3.text_input("반려 사유", key=f"rr_{r.id}", label_visibility="collapsed",
                                          placeholder="반려 사유(선택)")
            if c1.button("승인", key=f"ap_{r.id}", type="primary"):
                approvals.decide(r.id, admin.id, True)
                st.rerun(scope="fragment")
            if c2.button("반려", key=f"rj_{r.id}"):
                approvals.decide(r.id, admin.id, False, reject_reason)
                st.rerun(scope="fragment")


pending_list()

with st.expander("처리 완료 내역"):
    done = [r for r in approvals.list_requests() if r.status != RequestStatus.PENDING][:50]
    st.dataframe([{"신청자": r.user.name, "구분": TYPE_LABEL[r.type], "날짜": r.target_date, "시간": r.hours,
                   "결과": r.status.value, "처리일시": r.decided_at} for r in done],
                 hide_index=True, width="stretch")
