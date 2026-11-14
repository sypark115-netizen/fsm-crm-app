"""[화면 B-3] 현장 시공 사진 업로드 (모바일 카메라/갤러리)."""
from __future__ import annotations

import streamlit as st

from core.auth import require_role
from core.config import PHOTO_TAGS
from core.models import Role
from services import photos

user = require_role(Role.WORKER, Role.ADMIN, Role.MARKETER)

st.title("📷 현장 사진 업로드")

known_sites = photos.site_names()
with st.form("photo_form", clear_on_submit=True):
    site = st.selectbox("현장명", options=known_sites, index=None, accept_new_options=True,
                        placeholder="현장명을 선택하거나 새로 입력")
    tags = st.pills("공정 태그", PHOTO_TAGS, selection_mode="multi")
    # 모바일 브라우저에서는 '사진 촬영 / 사진 보관함' 선택지가 자동 노출된다
    files = st.file_uploader("사진 (여러 장 선택 가능)", type=["jpg", "jpeg", "png", "webp"],
                             accept_multiple_files=True)
    if st.form_submit_button("업로드", type="primary", width="stretch"):
        if not files:
            st.error("사진을 1장 이상 선택해 주세요.")
        else:
            try:
                with st.spinner(f"{len(files)}장 처리 중… (리사이즈/회전 보정)"):
                    saved = photos.save_uploads(user.id, site or "", tags or [], files)
                st.success(f"{len(saved)}장 업로드 완료!")
            except ValueError as e:
                st.error(str(e))
            except Exception as e:  # noqa: BLE001 - HEIC 미지원 등
                st.error(f"이미지 처리 실패: {e}")

st.subheader("최근 내가 올린 사진")
mine = photos.list_photos(uploader_id=user.id)[:12]
if mine:
    cols = st.columns(3)
    for i, p in enumerate(mine):
        cols[i % 3].image(p.thumb_path, caption=p.site_name, width="stretch")
else:
    st.caption("아직 업로드한 사진이 없습니다.")
