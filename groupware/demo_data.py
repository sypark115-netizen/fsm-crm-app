"""테스트용 데모 데이터 생성: 이번 달 출퇴근·결재·현장사진.

사용: python demo_data.py   (DB가 비어 있을 때 1회)
"""
import sys
sys.path.insert(0, ".")
from datetime import date, datetime, timedelta
from io import BytesIO
from PIL import Image, ImageDraw
from sqlalchemy import select
from core.database import init_db, get_session
from core.config import SITES
from core.models import User, RequestType

from services import attendance, approvals, photos

init_db()
with get_session() as _s:
    from core.models import Photo
    if _s.scalar(select(Photo.id).limit(1)) is not None:
        print("이미 데이터가 있어 건너뜁니다."); sys.exit(0)
HQ = SITES[0]
with get_session() as s:
    ids = {u.emp_no: u.id for u in s.scalars(select(User))}
today = date.today()
d = today.replace(day=1)
plan = {"W001": (8, 20), "W002": (8, 18)}
while d < today:
    if d.weekday() < 5:
        for emp, (h_in, h_out) in plan.items():
            out = h_out if d.day % 3 else 17
            attendance.check_in(ids[emp], HQ.lat, HQ.lng, datetime(d.year, d.month, d.day, h_in, 5))
            attendance.check_out(ids[emp], HQ.lat, HQ.lng, datetime(d.year, d.month, d.day, out, 10))
        if d.day % 3:
            r = approvals.submit(ids["W001"], RequestType.OVERTIME, d, 2, "타일 마감 야간작업")
            approvals.decide(r.id, ids["A001"], True)
    d += timedelta(days=1)
approvals.submit(ids["W002"], RequestType.OVERTIME, today, 2, "강남 A아파트 욕실 방수 마감")
approvals.submit(ids["W001"], RequestType.ANNUAL, today + timedelta(days=5), 0, "가족 행사")

def img(top, bottom, label):
    im = Image.new("RGB", (1600, 1200))
    dr = ImageDraw.Draw(im)
    for y in range(1200):
        t = y / 1200
        dr.line((0, y, 1600, y), fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    for x in range(0, 1600, 160):
        dr.rectangle((x + 20, 700, x + 140, 1100), outline=(255, 255, 255), width=4)
    dr.text((60, 60), label, fill="white", font_size=80)
    b = BytesIO(); im.save(b, "JPEG"); b.seek(0); b.name = label + ".jpg"; return b

photos.save_uploads(ids["W001"], "강남 래미안 101동", ["철거"], [img((90, 80, 70), (150, 130, 110), "BEFORE")])
photos.save_uploads(ids["W001"], "강남 래미안 101동", ["타일"], [img((120, 140, 160), (200, 200, 210), "TILE WORK")])
photos.save_uploads(ids["W002"], "강남 래미안 101동", ["완공"], [img((230, 225, 215), (250, 250, 245), "AFTER")])
photos.save_uploads(ids["W002"], "성수 카페 인테리어", ["목공", "도장"], [img((160, 110, 70), (220, 180, 140), "WOOD"), img((60, 90, 80), (140, 170, 150), "PAINT")])
print("데모 데이터 생성 완료")
