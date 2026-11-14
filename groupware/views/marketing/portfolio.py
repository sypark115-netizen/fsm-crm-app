"""발행된 시공사례 갤러리 & 블로그 초안 관리."""
from __future__ import annotations

from pathlib import Path

import streamlit as st
from sqlalchemy import select

from core.auth import require_role
from core.config import PORTFOLIO_DIR
from core.database import get_session
from core.models import PortfolioItem, Role
from services import publishing

require_role(Role.ADMIN, Role.MARKETER)
st.title("🖼️ 포트폴리오·블로그")

tab_gallery, tab_posts = st.tabs(["시공사례 갤러리 (랜딩페이지 피드)", "블로그 초안"])

with tab_gallery:
    with get_session() as s:
        items = list(s.scalars(select(PortfolioItem).order_by(PortfolioItem.published_at.desc())))
    feed = PORTFOLIO_DIR / "portfolio.json"
    if feed.exists():
        st.download_button("portfolio.json (랜딩페이지 연동용)", feed.read_bytes(), file_name="portfolio.json",
                           mime="application/json")
    cols = st.columns(4)
    for i, it in enumerate(items):
        img = PORTFOLIO_DIR.parent / it.public_path
        if img.exists():
            cols[i % 4].image(str(img), caption=it.caption, width="stretch")

with tab_posts:
    for post in publishing.list_posts():
        with st.expander(f"{post.created_at:%Y-%m-%d} · {post.title}"):
            st.markdown(f"채널: `{post.channel}`" + (f" · [외부 링크]({post.external_url})" if post.external_url else ""))
            st.code(post.markdown, language="markdown")
            st.download_button("마크다운 다운로드", post.markdown.encode("utf-8"),
                               file_name=Path(post.file_path).name, key=f"md_{post.id}")
