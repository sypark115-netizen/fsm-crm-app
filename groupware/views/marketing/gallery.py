"""[화면 C-3] 현장 사진 갤러리 → 파란 노출 토글 → 원클릭 발행."""
from __future__ import annotations

import streamlit as st

from core.auth import require_role
from core.models import Role
from services import photos, publishing

user = require_role(Role.ADMIN, Role.MARKETER)
st.title("🚀 현장사진 → 원클릭 발행")

c1, c2 = st.columns([2, 1])
site = c1.selectbox("현장 필터", ["전체", *photos.site_names()])
only_new = c2.toggle("미발행만 보기", value=True)
items = photos.list_photos(site=None if site == "전체" else site, only_unpublished=only_new)

selected = sum(p.is_public and not p.is_published for p in items)
st.markdown(f"외부 노출 선택 <span class='gw-badge'>{selected}장</span>", unsafe_allow_html=True)

if not items:
    st.info("표시할 사진이 없습니다.")

PER_ROW = 4
for row_start in range(0, len(items), PER_ROW):
    cols = st.columns(PER_ROW)
    for col, p in zip(cols, items[row_start:row_start + PER_ROW]):
        with col.container(border=True):
            st.image(p.thumb_path, width="stretch")
            st.caption(f"**{p.site_name}** · {', '.join(p.tag_list) or '태그없음'}  \n"
                       f"{p.uploader.name} · {p.uploaded_at:%m/%d %H:%M}")
            if p.is_published:
                st.caption("✅ 발행됨")
            else:
                # 파란색 = theme.primaryColor (#1E6FFF). 토글 즉시 DB 반영
                val = st.toggle("외부 노출", value=p.is_public, key=f"pub_{p.id}")
                if val != p.is_public:
                    photos.set_public(p.id, val)
                    st.rerun()

st.divider()
if st.button(f"📰 블로그/포트폴리오 자동 발행 ({selected}장)", type="primary",
             disabled=selected == 0, width="stretch"):
    with st.spinner("포트폴리오 DB 적재 및 블로그 초안 생성 중…"):
        result = publishing.publish_selected(user.id)
    st.success(f"{result.item_count}장 → 포트폴리오 적재, 블로그 초안 {len(result.posts)}건 생성")
    for post in result.posts:
        with st.expander(post.title, expanded=True):
            st.code(post.markdown, language="markdown")
