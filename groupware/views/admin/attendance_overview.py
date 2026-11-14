"""전사 근태 조회."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import select

from core.auth import require_role
from core.database import engine
from core.models import Attendance, Role, User

require_role(Role.ADMIN)
st.title("🗓️ 전사 근태 조회")

c1, c2 = st.columns(2)
start = c1.date_input("시작일", value=date.today() - timedelta(days=7))
end = c2.date_input("종료일", value=date.today())

q = (select(User.emp_no.label("사번"), User.name.label("성명"), User.department.label("부서"),
            Attendance.work_date.label("일자"), Attendance.check_in.label("출근"), Attendance.check_out.label("퇴근"),
            Attendance.site_name.label("지점"), Attendance.in_distance_m.label("출근거리(m)"))
     .join(User, User.id == Attendance.user_id)
     .where(Attendance.work_date.between(start, end))
     .order_by(Attendance.work_date.desc(), User.emp_no))
df = pd.read_sql(q, engine)
if df.empty:
    st.info("해당 기간 근태 기록이 없습니다.")
else:
    df["근무(h)"] = ((pd.to_datetime(df["퇴근"]) - pd.to_datetime(df["출근"])).dt.total_seconds() / 3600).round(2)
    df["상태"] = df["퇴근"].isna().map({True: "퇴근 미체크", False: ""})
    st.dataframe(df, hide_index=True, width="stretch")
    st.download_button("CSV 다운로드", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"attendance_{start}_{end}.csv", mime="text/csv")
