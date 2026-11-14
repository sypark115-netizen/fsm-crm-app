"""세션 기반 인증 & 권한(RBAC)."""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st
from sqlalchemy import select

from core.database import get_session
from core.models import Role, User
from core.security import verify_password


@dataclass(frozen=True)
class CurrentUser:
    id: int
    emp_no: str
    name: str
    role: Role
    department: str | None


def authenticate(emp_no: str, password: str) -> CurrentUser | None:
    with get_session() as s:
        user = s.scalar(select(User).where(User.emp_no == emp_no.strip().upper(), User.is_active.is_(True)))
        if user is None or not verify_password(password, user.password_hash):
            return None
        return CurrentUser(user.id, user.emp_no, user.name, user.role, user.department)


def login(user: CurrentUser) -> None:
    st.session_state["user"] = user
    st.session_state["role"] = user.role.value  # 'admin' | 'worker' | 'marketer'


def logout() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def current_user() -> CurrentUser | None:
    return st.session_state.get("user")


def require_role(*roles: Role) -> CurrentUser:
    """페이지 최상단에서 호출. 메뉴 숨김과 별개로 URL 직접 접근도 차단한다."""
    user = current_user()
    if user is None:
        st.warning("로그인이 필요합니다.")
        st.stop()
    if roles and user.role not in roles:
        st.error("이 메뉴에 접근할 권한이 없습니다.")
        st.stop()
    return user
