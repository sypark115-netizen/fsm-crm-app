# Hygiene Pass — 문서 기본 품질

Hygiene Factor다. 리포트의 중심이 아니며 `02_slide_review.md` 맨 뒤에 모은다. `category: "hygiene"`로 쓰면 report.py가 자동으로 뒤로 보낸다.

## 1. 대상

| 항목 | 방법 | 기본 Severity |
|---|---|---|
| 오타·오탈자·맞춤법 | unit 텍스트를 읽고 판단 (외부 맞춤법 검사기 사용 금지 — 기밀 전송) | ENHANCEMENT |
| 띄어쓰기 | 의미가 바뀌거나 눈에 띄는 것만 (전수 교정은 소음) | ENHANCEMENT |
| **고객명 오류·다른 고객명** | `cross_check.json` `customer_variants`, `other_customers` | **MUST FIX** (다른 고객명), SHOULD FIX (표기 변형) |
| **제품명·회사명 표기** | 공식 표기 혼용 (`kt_naming`, `term_variants`) | SHOULD FIX (GM·표지), ENHANCEMENT (본문) |
| 숫자·단위 불일치 | `number_conflicts`, `date_conflicts` — 진짜 모순이면 Hygiene가 아니라 **CONSISTENCY Finding** (MUST FIX 가능) | — |
| 용어 통일 | 같은 대상을 다른 말로 (이전/이관/마이그레이션, DR센터/백업센터) | ENHANCEMENT |
| GM·표지 오타 | 가장 먼저 보이는 곳 | **SHOULD FIX** |
| 어색한 한국어·번역투 | 의미 전달을 해치는 경우만 | ENHANCEMENT |
| AI스러운 문장 | `key-message.md` 5절 목록 — 근거 없이 쓰인 경우 | ENHANCEMENT (GM이면 SHOULD FIX) |

## 2. 출력 규칙

- 행마다 `current`(원문 일부)와 `revised`(수정 문장)를 쓴다.
- 같은 오류가 여러 곳이면 한 행에 위치를 나열한다.
- 고유명사·제품명의 "공식" 표기를 AI가 확정하지 않는다 → 혼용 사실만 알리고 `[VERIFY: 공식 표기]`.
- 숫자는 고치지 않는다 (Protected Facts) — 불일치만 알린다.
