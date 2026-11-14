"""출퇴근 기록. 반경 검증은 반드시 서버(파이썬)에서 다시 수행한다."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select

from core.database import get_session
from core.models import Attendance
from services.geofence import nearest_site


class AttendanceError(Exception):
    pass


def today_record(user_id: int, day: date | None = None) -> Attendance | None:
    day = day or date.today()
    with get_session() as s:
        return s.scalar(select(Attendance).where(Attendance.user_id == user_id, Attendance.work_date == day))


def check_in(user_id: int, lat: float, lng: float, now: datetime | None = None) -> Attendance:
    now = now or datetime.now()
    geo = nearest_site(lat, lng)
    if not geo.ok:
        raise AttendanceError(f"{geo.site.name} 반경 {geo.site.radius_m:.0f}m 밖입니다 (현재 {geo.distance_m:.0f}m).")
    with get_session() as s:
        rec = s.scalar(select(Attendance).where(Attendance.user_id == user_id, Attendance.work_date == now.date()))
        if rec and rec.check_in:
            raise AttendanceError("이미 출근 처리되었습니다.")
        rec = rec or Attendance(user_id=user_id, work_date=now.date())
        rec.check_in, rec.in_lat, rec.in_lng = now, lat, lng
        rec.site_name, rec.in_distance_m = geo.site.name, geo.distance_m
        s.add(rec)
        s.flush()
        return rec


def check_out(user_id: int, lat: float, lng: float, now: datetime | None = None) -> Attendance:
    now = now or datetime.now()
    geo = nearest_site(lat, lng)
    if not geo.ok:
        raise AttendanceError(f"{geo.site.name} 반경 {geo.site.radius_m:.0f}m 밖입니다 (현재 {geo.distance_m:.0f}m).")
    with get_session() as s:
        rec = s.scalar(select(Attendance).where(Attendance.user_id == user_id, Attendance.work_date == now.date()))
        if rec is None or rec.check_in is None:
            raise AttendanceError("출근 기록이 없습니다.")
        if rec.check_out:
            raise AttendanceError("이미 퇴근 처리되었습니다.")
        rec.check_out, rec.out_lat, rec.out_lng, rec.out_distance_m = now, lat, lng, geo.distance_m
        s.flush()
        return rec
