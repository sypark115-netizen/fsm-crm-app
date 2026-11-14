from datetime import date, datetime
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import select

from core.auth import authenticate
from core.config import SITES
from core.database import get_session
from core.models import DocType, Photo, PortfolioItem, RequestType, Role, User
from services import approvals, attendance, hometax_rpa, image_studio, photos, publishing
from services.geofence import haversine_m, nearest_site
from services.payroll import monthly_payroll, to_excel

HQ = SITES[0]


def _uid(emp_no: str) -> int:
    with get_session() as s:
        return s.scalar(select(User.id).where(User.emp_no == emp_no))


def _jpeg(color="red", size=(800, 600)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    buf.seek(0)
    buf.name = f"{color}.jpg"
    return buf


def test_auth_roles():
    assert authenticate("w001", "1234").role == Role.WORKER  # 대소문자 무시
    assert authenticate("A001", "wrong") is None


def test_geofence():
    assert haversine_m(37.0, 127.0, 37.0, 127.0) == 0
    assert nearest_site(HQ.lat, HQ.lng).ok
    assert not nearest_site(HQ.lat + 0.01, HQ.lng).ok  # 약 1.1km


def test_checkin_rejects_outside_radius():
    with pytest.raises(attendance.AttendanceError):
        attendance.check_in(_uid("W001"), HQ.lat + 0.01, HQ.lng)


def test_payroll_matches_only_approved_overtime():
    w1, w2, admin = _uid("W001"), _uid("W002"), _uid("A001")
    d = date(2026, 11, 2)
    # W001: 08:00~20:00 → 12h - 1h 휴게 = 11h, 실연장 3h, 승인 2h → 인정 2h
    attendance.check_in(w1, HQ.lat, HQ.lng, datetime(2026, 11, 2, 8))
    attendance.check_out(w1, HQ.lat, HQ.lng, datetime(2026, 11, 2, 20))
    r = approvals.submit(w1, RequestType.OVERTIME, d, 2, "야간 마감")
    approvals.decide(r.id, admin, True)
    # W002: 실연장 2h 있으나 미승인 → 인정 0, 플래그
    attendance.check_in(w2, HQ.lat, HQ.lng, datetime(2026, 11, 2, 8))
    attendance.check_out(w2, HQ.lat, HQ.lng, datetime(2026, 11, 2, 19))

    ledger, detail = monthly_payroll(2026, 11)
    row1 = ledger.set_index("emp_no").loc["W001"]
    assert row1.regular_hours == 8 and row1.paid_ot == 2
    assert row1.ot_pay == round(2 * 12_000 * 1.5, -1)
    row2 = ledger.set_index("emp_no").loc["W002"]
    assert row2.paid_ot == 0 and row2.review_flags == 1
    assert to_excel(ledger, detail, 2026, 11)[:2] == b"PK"


def test_photo_publish_pipeline():
    w1, mkt = _uid("W001"), _uid("M001")
    saved = photos.save_uploads(w1, "강남 A아파트", ["타일", "완공"], [_jpeg("red", (4000, 3000)), _jpeg("blue")])
    assert saved[0].width == 1920
    photos.set_public(saved[0].id, True)
    result = publishing.publish_selected(mkt)
    assert result.item_count == 1 and len(result.posts) == 1
    assert "강남 A아파트" in result.posts[0].markdown
    with get_session() as s:
        assert s.scalar(select(PortfolioItem.photo_id)) == saved[0].id
        assert s.get(Photo, saved[1].id).is_published is False
    assert publishing.publish_selected(mkt).item_count == 0  # 중복 발행 방지


def test_image_studio():
    files = [_jpeg("red"), _jpeg("green"), _jpeg("blue")]
    assert image_studio.before_after(files[0], files[2]).size == (1080, 1080)
    assert image_studio.triptych(files, size=(1080, 1350)).size == (1080, 1350)


def test_rpa_mock_creates_pdf():
    path = hometax_rpa.issue(DocType.BIZ_REGISTRATION, _uid("A001"))
    assert path.read_bytes()[:4] == b"%PDF"
    assert hometax_rpa.history()[0].status.value == "done"
