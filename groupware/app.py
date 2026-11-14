"""초경량 사내 그룹웨어 — 진입점.

실행:  streamlit run app.py
권한별 메뉴는 st.navigation 으로 '노출 자체'를 분기하고,
각 페이지는 require_role() 로 URL 직접 접근까지 한 번 더 차단한다.
"""
from __future__ import annotations

import streamlit as st

from core.auth import authenticate, current_user, login, logout
from core.database import init_db
from core.models import Role
from core.ui import inject_base_css, quick_nav


@st.cache_resource
def _bootstrap() -> bool:
    init_db()  # 테이블 생성 + 데모 계정 시드 (프로세스당 1회)
    return True


_bootstrap()

user = current_user()
st.set_page_config(
    page_title="현장 그룹웨어",
    page_icon="🏗️",
    # 현장 작업자는 모바일 세로 화면 → centered, 관리자/마케터는 PC → wide
    layout="centered" if user is None or user.role == Role.WORKER else "wide",
    initial_sidebar_state="collapsed" if user is None or user.role == Role.WORKER else "expanded",
)
inject_base_css()


# ───────────────────────── [화면 A] 로그인 ─────────────────────────
def login_page() -> None:
    st.title("🏗️ 현장 그룹웨어")
    st.caption("사원번호와 비밀번호로 로그인하세요.")
    with st.form("login", border=True):
        emp_no = st.text_input("사원번호", placeholder="예: W001", autocomplete="username")
        password = st.text_input("비밀번호", type="password", autocomplete="current-password")
        if st.form_submit_button("로그인", type="primary", width="stretch"):
            u = authenticate(emp_no, password)
            if u is None:
                st.error("사원번호 또는 비밀번호가 올바르지 않습니다.")
            else:
                login(u)
                st.rerun()
    with st.expander("데모 계정"):
        st.markdown("- 관리자 `A001` / `admin1234`\n- 마케터 `M001` / `mkt1234`\n- 작업자 `W001` / `1234`")


def logout_page() -> None:
    logout()
    st.rerun()


# ───────────────────────── 권한별 메뉴 ─────────────────────────
def _pages(spec: list[tuple[str, str, str]], default: str | None = None) -> list[st.Page]:
    return [st.Page(path, title=title, icon=icon, default=(path == default)) for path, title, icon in spec]


WORKER = [
    ("views/worker/checkin.py", "출퇴근 체크", "📍"),
    ("views/worker/requests.py", "연장근로·연차 신청", "📝"),
    ("views/worker/photo_upload.py", "현장 사진 업로드", "📷"),
]
ADMIN = [
    ("views/admin/dashboard.py", "대시보드", "📊"),
    ("views/admin/approvals.py", "전자결재 승인", "✅"),
    ("views/admin/attendance_overview.py", "전사 근태 조회", "🗓️"),
    ("views/admin/payroll.py", "급여 자동 산출", "💰"),
    ("views/admin/documents.py", "행정 증명서 발급", "📄"),
    ("views/admin/users.py", "권한·사용자 관리", "👥"),
]
MARKETING = [
    ("views/marketing/gallery.py", "현장사진 → 원클릭 발행", "🚀"),
    ("views/marketing/portfolio.py", "포트폴리오·블로그", "🖼️"),
    ("views/marketing/studio.py", "연출샷 스튜디오", "✨"),
]
ACCOUNT = [st.Page(logout_page, title="로그아웃", icon="🚪", url_path="logout")]

if user is None:
    nav = st.navigation([st.Page(login_page, title="로그인", icon="🔐")], position="hidden")
elif user.role == Role.WORKER:
    # 일반 직원: 급여·경영 메뉴는 아예 등록하지 않음 → 메뉴/URL 모두 존재하지 않음 (원천 차단)
    worker_pages = _pages(WORKER, WORKER[0][0])
    nav = st.navigation({"내 업무": worker_pages, "계정": ACCOUNT}, position="top")
    quick_nav(worker_pages)
elif user.role == Role.MARKETER:
    nav = st.navigation({"마케팅": _pages(MARKETING, MARKETING[0][0]),
                         "내 업무": _pages(WORKER[1:2]), "계정": ACCOUNT})
else:  # ADMIN — 전체 접근
    nav = st.navigation({"경영관리": _pages(ADMIN, ADMIN[0][0]), "마케팅": _pages(MARKETING),
                         "현장": _pages(WORKER), "계정": ACCOUNT}, expanded=True)

if user is not None:
    with st.sidebar:
        st.markdown(f"**{user.name}** · {user.department or ''}  \n<span class='gw-muted'>{user.emp_no} · {user.role.value}</span>",
                    unsafe_allow_html=True)

nav.run()
