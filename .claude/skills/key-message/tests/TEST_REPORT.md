# 키 메시지 Skill — 테스트 결과

- 작업 폴더: `<작업폴더>`
- 결과: 15 PASS / 0 FAIL

| Test | Result | Detail |
|---|---|---|
| TEST 1 — AI 상투어 → RED | PASS | status=RED, swap=YES, patterns=['기반으로', '디지털 혁신', '차별화된', '가속화', '당사의'] |
| TEST 2 — 좋은 메시지 → GREEN 유지 | PASS | status=GREEN (수정 강요 없음) |
| TEST 3 — Tech → Value | PASS | '생성형 AI 기반 Intelligent Workplace를 구축합니다.' → '흩어진 상담·설계 자료는 AI가 찾아 정리하고, 담당자는 견적 판단에 집중합니다.' (재진단 GREEN, 업무어=['견적', '담당자', '상담', '설계', '자료']) |
| TEST 4 — Human vs AI 역할 구분 | PASS | → '문의 분석부터 견적 초안까지는 AI Agent가, 가격과 최종 승인은 담당자가 맡습니다.' (AI 역할 + 담당자 역할 모두 포함, 재진단 GREEN) |
| TEST 5 — Fact Guard (숫자 보존) | PASS | OK/ERROR/WARN 판정 정확, 위조 숫자(150대) Review QA=ERROR, APPLY 차단 확인 |
| TEST 6 — Evidence 부족 → ESCALATE | PASS | ESCALATE, 추가 Evidence 요청 7개: 실제 구축 Reference(고객·업종·규모), 적용 업무 수 / 처리 건수, 정확도·처리시간·비용 변화… |
| TEST 7 — PPT REVIEW (PPTX → Review XLSX) | PASS | 한빛제조_AX_KeyMessage_Review.xlsx: 메시지 27개 (Governing 8), {'GREEN': 13, 'YELLOW': 5, 'RED': 6, 'ESCALATE': 3}, validate=PASS |
| TEST 8 — PDF REVIEW (Page·Source 추적) + PDF Review → 원본 PPTX APPLY | PASS | PDF 메시지 27개, Governing 8/8 인식·Page 일치, PDF Review→PPTX 반영 11건, 구조검증 PASS |
| TEST 9 — XLSX REVIEW (Workbook/Sheet 구조) + XLSX APPLY | PASS | 시트 2개·Header·수식 4개 인식, Governing 4개, 셀 반영 4건, 수식·차트·서식 보존 PASS |
| TEST 10 — APPLY Decision 처리 (ACCEPT/EDIT/KEEP/ESCALATE/빈칸) | PASS | ACCEPT=AI안, EDIT=Human Final, EDIT(빈칸)=Warning+원문, KEEP/ESCALATE/빈칸=원문 — 반영 2건, 구조검증 PASS |
| TEST 11 — Round Trip ★ (PPT → REVIEW → Excel → Human → APPLY → PPT) | PASS | 반영 12건 / 유지 15건, 원본 해시 동일, 구조검증 PASS, Score 76.2→81.6, RED 6→2, 긴 EDIT 처리: ['박스 자동 확장(spAutoFit) — 겹침 여부 육안 확인'], LibreOffice 열기 OK, Learning Log 기록 |
| TEST 12 — Multi Source ★ (RFP.pdf + Requirements.xlsx + Proposal.pptx + Reference.xlsx) | PASS | 역할 자동판별 4/4, 요구사항 12건(RFP p1~2 + xlsx), COVERED/WEAK 9·GAP 3, 요구사항 연결 메시지 14개, Reference 연결 메시지 4개, Source Trace 시트, 통합 Review→PPTX 반영 PASS |
| AUTO — 분석→재작성→수정본 자동 생성 | PASS | AUTO 반영 11건 (RED/YELLOW만), GREEN·ESCALATE 원문 유지, 구조검증 PASS |
| SAFETY — 원본 보호 (덮어쓰기 금지·v3 자동 증가·Stale 차단) | PASS | 같은 경로 출력 거부, v2 존재 시 v3 생성, 원문 불일치(Stale) 반영 0건 |
| OVERFLOW — 고정 박스 Overflow: 최소 폰트 조정 / 한계 초과 Warning | PASS | Box A 18→17pt(≤2pt 조정), Box B 폰트 유지 + Overflow Warning(축약 필요) |
