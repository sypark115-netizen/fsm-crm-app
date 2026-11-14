"""[화면 C-1] 근태 × 승인 연장근로 자동 대조 → 월 급여대장."""
from __future__ import annotations

from datetime import date

import streamlit as st

from core.auth import require_role
from core.models import Role
from services.payroll import LEDGER_COLUMNS_KO, monthly_payroll, to_excel

require_role(Role.ADMIN)
st.title("💰 급여 자동 산출")
st.caption("출퇴근 기록과 '승인된' 연장근로를 일자별로 대조해 인정 연장시간을 자동 산출합니다.")

today = date.today()
c1, c2 = st.columns(2)
year = c1.number_input("연도", 2020, 2100, today.year)
month = c2.selectbox("월", range(1, 13), index=today.month - 1)

ledger, detail = monthly_payroll(int(year), int(month))

m1, m2, m3 = st.columns(3)
m1.metric("지급 총액", f"{ledger['gross_pay'].sum():,}원")
m2.metric("연장수당 합계", f"{ledger['ot_pay'].sum():,}원")
m3.metric("검토 필요 일자", int(ledger["review_flags"].sum()))

st.subheader(f"{year}년 {month}월 급여대장")
st.dataframe(ledger.rename(columns=LEDGER_COLUMNS_KO), hide_index=True, width="stretch",
             column_config={k: st.column_config.NumberColumn(format="%d원") for k in ("시급", "기본급", "연장수당", "지급총액")})

with st.expander("일자별 대조표 (미승인 초과근로 / 승인>실근로 플래그)"):
    flagged_only = st.toggle("플래그 있는 행만")
    view = detail[detail["flag"] != ""] if flagged_only else detail
    st.dataframe(view, hide_index=True, width="stretch")

st.download_button("📥 엑셀 급여대장 다운로드", to_excel(ledger, detail, int(year), int(month)),
                   file_name=f"payroll_{year}{month:02d}.xlsx", type="primary",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
