"""권한·사용자 관리."""
from __future__ import annotations

import streamlit as st
from sqlalchemy import select

from core.auth import require_role
from core.database import get_session
from core.models import Role, User
from core.security import hash_password

admin = require_role(Role.ADMIN)
st.title("👥 권한·사용자 관리")

with get_session() as s:
    users = list(s.scalars(select(User).order_by(User.emp_no)))

edited = st.data_editor(
    [{"id": u.id, "사번": u.emp_no, "성명": u.name, "부서": u.department, "권한": u.role.value,
      "시급": u.hourly_wage, "재직": u.is_active} for u in users],
    column_config={"id": None, "사번": st.column_config.TextColumn(disabled=True),
                   "권한": st.column_config.SelectboxColumn(options=[r.value for r in Role], required=True)},
    hide_index=True, width="stretch", key="user_editor",
)
if st.button("변경사항 저장", type="primary"):
    blocked = False
    with get_session() as s:
        for row in edited:
            u = s.get(User, row["id"])
            if u.id == admin.id and (row["권한"] != Role.ADMIN.value or not row["재직"]):
                blocked = True
                continue
            u.name, u.department, u.role = row["성명"], row["부서"], Role(row["권한"])
            u.hourly_wage, u.is_active = int(row["시급"]), bool(row["재직"])
    if blocked:
        st.error("본인의 관리자 권한/재직 상태는 변경할 수 없어 해당 행은 건너뛰었습니다.")
    else:
        st.rerun()

st.subheader("신규 사용자")
with st.form("new_user", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    emp_no = c1.text_input("사번")
    name = c2.text_input("성명")
    role = c3.selectbox("권한", [r.value for r in Role], index=1)
    dept = c1.text_input("부서")
    wage = c2.number_input("시급", value=10_320, step=10)
    pw = c3.text_input("초기 비밀번호", type="password")
    if st.form_submit_button("추가"):
        if not (emp_no and name and pw):
            st.error("사번/성명/비밀번호는 필수입니다.")
        else:
            with get_session() as s:
                if s.scalar(select(User).where(User.emp_no == emp_no.upper())):
                    st.error("이미 존재하는 사번입니다.")
                else:
                    s.add(User(emp_no=emp_no.upper(), name=name, role=Role(role), department=dept,
                               hourly_wage=int(wage), password_hash=hash_password(pw)))
                    st.success(f"{name} 추가 완료")
