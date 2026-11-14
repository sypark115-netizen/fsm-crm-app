"""[화면 C-2] 행정 증명서 자동 발급 (RPA)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.auth import require_role
from core.config import HOMETAX_MODE
from core.models import DocType, Role
from services import hometax_rpa
from services.hometax_rpa import DOC_SPECS, RpaError

admin = require_role(Role.ADMIN)
st.title("📄 행정 증명서 자동 발급")
if HOMETAX_MODE != "live":
    st.info("현재 **MOCK 모드**입니다. 실제 발급은 `GW_HOMETAX_MODE=live` + 인증서 설치 PC에서 실행하세요.")

cols = st.columns(2)
for i, doc_type in enumerate(DocType):
    spec = DOC_SPECS[doc_type]
    if cols[i % 2].button(f"{spec.label} 발급", key=f"doc_{doc_type.value}", width="stretch",
                          type="primary" if spec.portal == "hometax" else "secondary"):
        with st.status(f"{spec.label} 발급 중…", expanded=True) as status:
            try:
                path = hometax_rpa.issue(doc_type, admin.id, progress=st.write)
                status.update(label=f"{spec.label} 발급 완료", state="complete")
                st.session_state["last_doc"] = str(path)
            except (RpaError, Exception) as e:  # noqa: BLE001
                status.update(label=f"발급 실패: {e}", state="error")

if last := st.session_state.get("last_doc"):
    p = Path(last)
    if p.exists():
        st.download_button(f"⬇ {p.name}", p.read_bytes(), file_name=p.name, mime="application/pdf")

st.subheader("발급 이력")
hist = hometax_rpa.history()
for d in hist:
    c1, c2, c3 = st.columns([3, 2, 2])
    c1.write(f"{DOC_SPECS[d.doc_type].label} · {d.requested_at:%m/%d %H:%M}")
    c2.write({"done": "✅ 완료", "failed": "❌ 실패", "running": "⏳ 진행", "queued": "대기"}[d.status.value])
    if d.file_path and Path(d.file_path).exists():
        c3.download_button("다운로드", Path(d.file_path).read_bytes(), file_name=Path(d.file_path).name,
                           key=f"dl_{d.id}", mime="application/pdf")
    elif d.error:
        c3.caption(d.error[:80])
