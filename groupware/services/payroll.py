"""근태 × 승인된 연장근로 자동 대조 → 월 급여대장.

규칙(기본값, 회사 취업규칙에 맞춰 조정):
- 휴게시간: 근로 4h 이상 30분, 8h 이상 1시간 공제 (근로기준법 제54조)
- 기본근로: 일 8시간 한도
- 연장수당: '승인된 연장근로 시간'과 '실제 8h 초과 근로' 중 작은 값만 인정 × 1.5배
  → 승인 없이 남은 시간, 승인됐지만 실제로 일하지 않은 시간 모두 자동 배제
"""
from __future__ import annotations

from datetime import date
from io import BytesIO

import pandas as pd
from sqlalchemy import select

from core.config import FLAG_MIN_OT_HOURS, OVERTIME_MULTIPLIER, REGULAR_HOURS_PER_DAY
from core.database import engine
from core.models import Attendance, RequestStatus, RequestType, User, WorkRequest


def month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    return start, end


def break_hours(gross: float) -> float:
    if gross >= 8:
        return 1.0
    if gross >= 4:
        return 0.5
    return 0.0


def load_frames(year: int, month: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    start, end = month_range(year, month)
    users = pd.read_sql(select(User.id.label("user_id"), User.emp_no, User.name, User.department,
                               User.hourly_wage).where(User.is_active.is_(True)), engine)
    att = pd.read_sql(select(Attendance.user_id, Attendance.work_date, Attendance.check_in, Attendance.check_out)
                      .where(Attendance.work_date >= start, Attendance.work_date < end), engine)
    ot = pd.read_sql(select(WorkRequest.user_id, WorkRequest.target_date.label("work_date"),
                            WorkRequest.hours.label("approved_ot"))
                     .where(WorkRequest.type == RequestType.OVERTIME,
                            WorkRequest.status == RequestStatus.APPROVED,
                            WorkRequest.target_date >= start, WorkRequest.target_date < end), engine)
    return users, att, ot


def daily_detail(att: pd.DataFrame, ot: pd.DataFrame) -> pd.DataFrame:
    """일자별 대조표 (관리자 검증용)."""
    if att.empty:
        return pd.DataFrame(columns=["user_id", "work_date", "net_hours", "regular_hours",
                                     "actual_ot", "approved_ot", "paid_ot", "flag"])
    df = att.dropna(subset=["check_in", "check_out"]).copy()
    df["work_date"] = pd.to_datetime(df["work_date"]).dt.date
    gross = (pd.to_datetime(df["check_out"]) - pd.to_datetime(df["check_in"])).dt.total_seconds() / 3600
    df["net_hours"] = (gross - gross.map(break_hours)).clip(lower=0).round(2)
    df["regular_hours"] = df["net_hours"].clip(upper=REGULAR_HOURS_PER_DAY)
    df["actual_ot"] = (df["net_hours"] - REGULAR_HOURS_PER_DAY).clip(lower=0).round(2)

    if not ot.empty:
        ot = ot.copy()
        ot["work_date"] = pd.to_datetime(ot["work_date"]).dt.date
        ot = ot.groupby(["user_id", "work_date"], as_index=False)["approved_ot"].sum()
        df = df.merge(ot, on=["user_id", "work_date"], how="left")
    else:
        df["approved_ot"] = 0.0
    df["approved_ot"] = df["approved_ot"].fillna(0.0)
    df["paid_ot"] = df[["actual_ot", "approved_ot"]].min(axis=1)

    def _flag(r) -> str:
        if r.actual_ot >= FLAG_MIN_OT_HOURS and r.approved_ot == 0:
            return "미승인 초과근로"
        if r.approved_ot > r.actual_ot:
            return "승인>실근로"
        return ""

    df["flag"] = df.apply(_flag, axis=1)
    return df[["user_id", "work_date", "net_hours", "regular_hours", "actual_ot", "approved_ot", "paid_ot", "flag"]]


def monthly_payroll(year: int, month: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(급여대장, 일자별 대조표) 반환."""
    users, att, ot = load_frames(year, month)
    detail = daily_detail(att, ot)
    agg = (detail.groupby("user_id")
           .agg(work_days=("work_date", "nunique"), regular_hours=("regular_hours", "sum"),
                paid_ot=("paid_ot", "sum"), review_flags=("flag", lambda f: int((f != "").sum())))
           .reset_index())
    ledger = users.merge(agg, on="user_id", how="left").fillna(
        {"work_days": 0, "regular_hours": 0.0, "paid_ot": 0.0, "review_flags": 0})
    ledger["base_pay"] = (ledger["regular_hours"] * ledger["hourly_wage"]).round(-1)
    ledger["ot_pay"] = (ledger["paid_ot"] * ledger["hourly_wage"] * OVERTIME_MULTIPLIER).round(-1)
    ledger["gross_pay"] = ledger["base_pay"] + ledger["ot_pay"]
    # TODO: 주휴수당, 4대보험/소득세 공제는 회사 정책 확정 후 추가
    ledger = ledger.astype({"work_days": int, "review_flags": int, "base_pay": int, "ot_pay": int, "gross_pay": int})

    detail = detail.merge(users[["user_id", "emp_no", "name"]], on="user_id", how="left")
    return ledger.drop(columns=["user_id"]), detail.drop(columns=["user_id"])


LEDGER_COLUMNS_KO = {
    "emp_no": "사번", "name": "성명", "department": "부서", "hourly_wage": "시급", "work_days": "근무일수",
    "regular_hours": "기본근로(h)", "paid_ot": "인정연장(h)", "review_flags": "검토필요", "base_pay": "기본급",
    "ot_pay": "연장수당", "gross_pay": "지급총액",
}


DETAIL_COLUMNS_KO = {
    "work_date": "일자", "emp_no": "사번", "name": "성명", "net_hours": "실근로(h)", "regular_hours": "기본(h)",
    "actual_ot": "실연장(h)", "approved_ot": "승인연장(h)", "paid_ot": "인정연장(h)", "flag": "검토사유",
}


def to_excel(ledger: pd.DataFrame, detail: pd.DataFrame, year: int, month: int) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        ledger.rename(columns=LEDGER_COLUMNS_KO).to_excel(xw, sheet_name=f"{year}-{month:02d} 급여대장", index=False)
        detail.rename(columns=DETAIL_COLUMNS_KO)[list(DETAIL_COLUMNS_KO.values())].to_excel(
            xw, sheet_name="일자별 대조", index=False)
    return buf.getvalue()
