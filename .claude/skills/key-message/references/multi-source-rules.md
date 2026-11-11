# Multi-Source · Proposal Context · Source Traceability

## 파일 역할 (자동 판별, `--role`로 지정 가능)
| role | 파일명/내용 신호 | 쓰임 |
|---|---|---|
| proposal | 제안서, proposal, storyline, 메시지 / .pptx 기본 | **수정 대상** (Message Review 행) |
| rfp | RFP, 제안요청, 과업지시, 입찰 | 고객 요구사항·배경·성공 기준 |
| requirements | 요구사항, requirement | 요구사항 Row → Req ID |
| reference | reference, 레퍼런스, 실적, 사례 | Evidence 후보 |

## 연결 사슬
```
Customer Requirement → Business Problem → Proposed Solution → Evidence → Customer Value → Governing → Key
```
- 요구사항 추출: RFP 문장 중 "~하여야 한다 / ~할 것 / 요구 / 제시" 또는 `SFR-001` 형식, 요구사항 xlsx의 Row(ID·명칭·상세 열 자동 인식).
- 메시지 ↔ 요구사항: 한국어 bigram 유사도. 메시지별 상위 3건(0.22 이상) 연결, 요구사항별 Coverage COVERED(≥0.3) / WEAK / GAP.
- 메시지 ↔ Evidence: 같은 장표 본문·표 우선, 이후 다른 자료(≥0.35). 근거 없는 주장 메시지에는 Reference 상위 2건을 **"Evidence 후보(확인 필요)"** 로만 제시하고 Status는 바꾸지 않는다.
- GAP 요구사항은 "메시지로 응답하지 않은 고객 요구사항 N건"으로 핵심 진단에 올린다. 중요한 요구사항(예: 승인 절차, 무중단, 보안)이 GAP이면 해당 장표 Governing에 응답을 제안한다.

## Proposal Context (문장 수정 전 먼저)
Brief 상단과 메시지별 정보로 다음을 정리한다.
- Customer: 고객명(발주기관·고객사 필드 > 귀중 > 표지), 산업, 현재 상황
- Business: 추진 이유, 핵심 문제·Pain, 요구사항, 성공 기준
- Technology: 제안 기술, Capability, 기존 시스템 연결
- Competition: 경쟁 구도, 차별점, Why Us (자료에 있을 때만)
- Evidence: Reference·수행 경험·숫자·SLA·성능·Architecture·인력·일정·비용·PoC
- Story: Why → What → Why Us → How → Evidence → Value

## Source Traceability
Review의 `Source Type · Source File · Source Location · Page / Slide`, Evidence 칸의 `파일 / 위치`를 유지한다.
```
RFP.pdf / Page 2 / Block 3 → SFR-002 담당자 승인 후 확정
Requirements.xlsx / Sheet '요구사항' / Row 3 → 견적 승인
Proposal.pptx / Slide 7 / Table → 가격·할인 승인은 사람
```
출처를 확인할 수 없는 사실은 확정적으로 쓰지 않는다. 다른 고객 Reference 숫자를 쓸 때는 공개 가능 여부를 Reason에 적는다.

## PDF
- PDF는 기본적으로 REVIEW 전용. Page별 분석, Source Location = `Page n / Block m`.
- PPT에서 Export된 PDF + 원본 PPTX가 있으면: PDF로 REVIEW → 승인 → **원본 PPTX에 APPLY** (같은 장표 번호에서 원문 텍스트 매칭).
- PDF 자체 직접 수정은 지원하지 않는다(별도 옵션 영역).

## XLSX
- 시트별 Header 행 자동 인식(상위 10행), 수식 셀은 메시지 대상 제외(값만 Context), 표 Row Record 생성.
- Storyline/메시지 시트: `Governing`/`헤드 메시지` 열 → Governing, `Key Message` 열 → Key, `장표`/`Page` 열 → Page, `섹션` 열 → Section.
- APPLY는 sheet XML의 해당 셀만 바꾸고 sharedStrings에 새 문자열을 추가한다 → 수식·서식·차트·다른 시트 그대로.
