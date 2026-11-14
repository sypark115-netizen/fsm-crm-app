"""[화면 C-4] 연출샷 생성 보조: 원본 3장 → 전후 비교 / 공정 스토리 / 자동 보정."""
from __future__ import annotations

import streamlit as st

from core.auth import require_role
from core.models import Role
from services import image_studio as fx

require_role(Role.ADMIN, Role.MARKETER)
st.title("✨ 연출샷 스튜디오")
st.caption("현장 원본 3장(시공 전 → 시공 중 → 완공 순)을 올리면 마케팅용 컷을 자동 가공합니다.")

files = st.file_uploader("원본 사진 3장", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
c1, c2, c3 = st.columns(3)
fmt = c1.selectbox("출력 비율", ["1:1 (1080×1080)", "4:5 (1080×1350)", "9:16 (1080×1920)"])
strength = c2.slider("보정 강도", 0.0, 2.0, 1.0, 0.1)
mark = c3.text_input("워터마크", placeholder="예: ○○인테리어")

SIZES = {"1:1": (1080, 1080), "4:5": (1080, 1350), "9:16": (1080, 1920)}
size = SIZES[fmt.split()[0]]

if files and len(files) != 3:
    st.warning(f"사진 3장이 필요합니다 (현재 {len(files)}장).")
elif files and st.button("연출샷 생성", type="primary"):
    with st.spinner("이미지 가공 중…"):
        outputs = {
            "전후 비교": fx.before_after(files[0], files[2], size=size, vertical=size[1] > size[0]),
            "공정 스토리": fx.triptych(files, size=size),
            "완공 보정컷": fx.enhance(files[2], strength),
        }
        if mark:
            outputs = {k: fx.watermark(v, mark) for k, v in outputs.items()}
    tabs = st.tabs(list(outputs))
    for tab, (name, img) in zip(tabs, outputs.items()):
        with tab:
            st.image(img, width="stretch")
            st.download_button(f"{name} 다운로드", fx.to_jpeg_bytes(img), file_name=f"{name}.jpg",
                               mime="image/jpeg", key=f"dl_{name}")
