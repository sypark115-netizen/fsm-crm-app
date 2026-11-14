"""[화면 B-1] GPS 모바일 출퇴근 체크인."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.auth import require_role
from core.config import ALLOW_MANUAL_GPS, SITES
from core.models import Role
from services.attendance import AttendanceError, check_in, check_out, today_record
from services.geofence import nearest_site

user = require_role(Role.WORKER, Role.ADMIN, Role.MARKETER)

st.title("📍 출퇴근 체크")
st.caption(f"{datetime.now():%Y년 %m월 %d일 (%a)} · {user.name}님")


def _browser_location() -> tuple[float, float, float] | None:
    """HTML5 Geolocation. HTTPS(또는 localhost)에서만 동작한다."""
    try:
        from streamlit_js_eval import get_geolocation
    except ImportError:
        st.info("`streamlit-js-eval` 미설치 — 수동 좌표 입력을 사용합니다.")
        return None
    loc = get_geolocation(component_key="gw_geo")
    if loc is None:
        st.caption("위치 권한을 허용해 주세요… (브라우저 팝업 확인)")
        return None
    if "coords" not in loc:
        st.error(f"위치를 가져오지 못했습니다: {loc.get('error', loc)}")
        return None
    c = loc["coords"]
    return c["latitude"], c["longitude"], c.get("accuracy") or 0.0


coords = _browser_location()
if coords is None and ALLOW_MANUAL_GPS:
    with st.expander("🛠 개발용: 좌표 수동 입력", expanded=False):
        lat = st.number_input("위도", value=SITES[0].lat, format="%.6f")
        lng = st.number_input("경도", value=SITES[0].lng, format="%.6f")
        if st.checkbox("이 좌표 사용"):
            coords = (lat, lng, 0.0)

rec = today_record(user.id)
c1, c2 = st.columns(2)
c1.metric("출근", rec.check_in.strftime("%H:%M") if rec and rec.check_in else "—")
c2.metric("퇴근", rec.check_out.strftime("%H:%M") if rec and rec.check_out else "—")

if coords is None:
    st.warning("현재 위치를 확인하는 중입니다. 위치 확인 후 버튼이 활성화됩니다.")
    can_check = False
else:
    lat, lng, acc = coords
    geo = nearest_site(lat, lng)
    can_check = geo.ok
    if geo.ok:
        st.success(f"✅ {geo.site.name} 반경 내 ({geo.distance_m:.0f}m / 허용 {geo.site.radius_m:.0f}m)")
    else:
        st.error(f"🚫 {geo.site.name}에서 {geo.distance_m:.0f}m 떨어져 있습니다 (허용 {geo.site.radius_m:.0f}m).")
    if acc and acc > 100:
        st.caption(f"⚠ GPS 정확도 ±{acc:.0f}m — 실외로 이동하면 정확해집니다.")

already_in = bool(rec and rec.check_in)
already_out = bool(rec and rec.check_out)

if st.button("🟢 출근하기", type="secondary" if already_in else "primary", width="stretch", disabled=not can_check or already_in):
    try:
        check_in(user.id, coords[0], coords[1])
        st.toast("출근 처리되었습니다.", icon="✅")
        st.rerun()
    except AttendanceError as e:
        st.error(str(e))

if st.button("🔴 퇴근하기", type="primary" if already_in and not already_out else "secondary", width="stretch", disabled=not can_check or not already_in or already_out):
    try:
        check_out(user.id, coords[0], coords[1])
        st.toast("퇴근 처리되었습니다. 수고하셨습니다!", icon="👋")
        st.rerun()
    except AttendanceError as e:
        st.error(str(e))
