"""반응형 공통 스타일. 모바일(현장)에서 버튼을 크게, 여백을 줄인다."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding: 3.75rem 0.75rem 4rem !important; }
  .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
      width: 100%; min-height: 3.25rem; font-size: 1.1rem; }
  h1 { font-size: 1.6rem !important; }
}
.gw-badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.8rem;
            background:#1E6FFF; color:#fff; margin-left:6px; }
.gw-muted { color:#6b7280; font-size:0.85rem; }
</style>
"""


def inject_base_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def quick_nav(pages: list) -> None:
    """모바일에서는 상단 메뉴가 접히므로, 현장 작업자용 큰 이동 버튼을 화면 상단에 고정 노출."""
    cols = st.columns(len(pages))
    for col, page in zip(cols, pages):
        col.page_link(page, label=page.title, icon=page.icon, width="stretch")
