# Output — findings.json 스키마와 예시

리포트는 모델이 `<작업폴더>/findings.json`을 쓰고 `scripts/report.py`가 렌더한다. 직접 Markdown 리포트를 쓰지 않는다 — report.py가 Guard 검사(원문에 없는 숫자·금융사명, 출처 없는 Evidence)를 하기 때문이다.

## 1. 스키마

```json
{
  "meta": {
    "customer": "한빛은행", "title": "차세대 DC 이전 사업", "date": "2026-11-11",
    "mode": "Presentation" ,
    "domains": "Primary: DC Migration / Secondary: Network / Cross: Security, PM, Financial Regulation",
    "files": ["F1 한빛은행_제안발표.pptx"],
    "assumptions": ["경쟁사 미지정 → '국내 대형 SI/MSP'로 Replaceability Test", "Win Theme 미제공 → 마무리 장표에서 추정"]
  },
  "executive": {
    "overall_assessment": "3~6문장. 현재 상태로 제출/발표하면 평가위원이 어떻게 받아들일지, 가장 큰 승부처와 가장 큰 Risk.",
    "evaluator_journey": {"SEE": "…", "UNDERSTAND": "…", "BELIEVE": "…", "TRUST": "…", "REMEMBER": "…"},
    "top5": [{"title": "…", "where": ["F1#S002", "F1#S006"], "why": "수주 영향", "fix": "구체적 수정"}],
    "what_works_well": ["F1#S004 — Evidence·How·Impact가 한 장표에 연결 (그대로 유지)"],
    "memory_test": {"remembered": ["…", "…", "…"], "intended": ["…", "…", "…"], "match": "1/3 일치", "gap_cause": "Governing Message — …"},
    "storyline": [{"id": "F1#S002", "gm": "…", "flag": "GENERIC"}],
    "success_questions": {"1. 고객의 진짜 니즈": "…", "2. RFP 누락": "…", "3. 제안전략": "…", "4. 경쟁사와 차이": "…",
                          "5. 왜 KT": "…", "6. Evidence": "…", "7. How": "…", "8. 평가위원 눈에 보이나": "…",
                          "9. PM·수행팀 신뢰": "…", "10. 발표 후 남는 것": "…"}
  },
  "findings": [{
    "id": "RT-01", "location": "F1#S002", "severity": "MUST FIX",
    "category": "Differentiation", "flags": ["DIFFERENTIATION FAILURE", "UNSUBSTANTIATED CLAIM"],
    "current": "원문 그대로",
    "issue": "무엇이 문제인가 (구체적으로)",
    "why_it_matters": "평가·수주에 왜 영향을 주나",
    "recommendation": "무엇을 어디에 어떻게",
    "revised": "바로 쓸 수 있는 수정 문장 (사실 필요 부분은 [VERIFY: …] / [EVIDENCE REQUIRED: …])",
    "triangle": {"why_kt": "…", "evidence": "… (위치)", "how": "…"},
    "visual": "5문항 형식의 Visual 추천 또는 빈칸",
    "evaluator": "평가위원의 속마음 한두 문장"
  }],
  "evidence_ledger": [{"claim": "…", "claim_loc": "F1#S002", "type": "Reference", "evidence": "…", "evidence_loc": "F1#S004", "status": "SUPPORTED"}],
  "compliance": [{"req_id": "PER-001", "requirement": "RTO 4시간 이내, RPO 0", "req_loc": "F3#P001", "criteria": "DR/보안 (20점)",
                  "response": "RTO 6시간 목표", "response_loc": "F2#P001", "evidence": "", "status": "CONFLICT",
                  "findability": "MEDIUM", "risk": "MUST FIX — 필수 요구 미충족으로 감점·부적합", "recommendation": "…"}]
}
```

- `severity`: `MUST FIX` | `SHOULD FIX` | `ENHANCEMENT` | `PASS`
- `category`: Strategy / Storyline / Differentiation / Evidence / How / Key Message / Visual / PM-Team Trust / Compliance / Consistency / Technical / Financial Regulation / Security / Copy-Paste / **hygiene**
- `location`: unit id. 여러 곳이면 `"F1#S005, F1#S009"`.
- `compliance`는 Mode 1에서만. `memory_test`는 Mode 2에서만.
- PASS Finding도 쓴다 (잘된 장표를 보호하기 위해). 단 What Works Well과 중복되면 PASS는 생략 가능.

## 2. 좋은 Finding vs 나쁜 Finding

**나쁜 예** (일반론 — 어느 제안서에나 해당, 위치·인용 없음)
```json
{"id":"X","location":"전체","severity":"SHOULD FIX","category":"Evidence",
 "issue":"차별화 포인트가 부족합니다","recommendation":"Evidence를 보강하고 차별화를 강화하세요",
 "revised":"KT는 국내 최고 수준의 금융 DC 이전 역량을 보유하고 있습니다"}
```
문제: 위치 없음, 인용 없음, Revised가 원래 문장보다 나아진 게 없고 "국내 최고"라는 새 주장을 만들었다.

**좋은 예**
```json
{"id":"RT-01","location":"F1#S002","severity":"MUST FIX","category":"Differentiation",
 "flags":["DIFFERENTIATION FAILURE","UNSUBSTANTIATED CLAIM"],
 "current":"KT는 차별화된 금융 Cloud 역량을 보유하고 있습니다",
 "issue":"발표 두 번째 장(집중도 최고 구간)의 GM이 Capability 선언이다. 'KT'를 '<경쟁사>'로 바꿔도 그대로 성립하고, 본문 3줄(역량 보유·다양한 경험·최고 인력)에 숫자·사례가 없다.",
 "why_it_matters":"평가위원은 앞 사업자에게서 같은 문장을 이미 들었다. 이 장에서 'KT만의 이유'를 얻지 못하면 이후 장표를 KT 관점으로 읽지 않는다.",
 "recommendation":"S04의 검증된 차별화(서버 이전-회선 Cutover 단일 Runbook, A금융사 1,180대)를 S02 GM으로 끌어올리고 S02 본문은 그 근거 3개로 재구성.",
 "revised":"서버와 회선을 함께 옮겨 본 사업자만 할 수 있는 약속: 한빛은행 계정계를 계획정지 8시간 안에 전환합니다 (A금융사 서버 1,180대 이전으로 검증)",
 "triangle":{"why_kt":"Network 운영조직 + DC 이전 PM 통합 (S04)","evidence":"A금융사 1,180대, 8시간 내 Cutover (F1#S004)","how":"단일 War-room·Runbook (F1#S004)"},
 "visual":"①'8시간'·'1,180대' ②현재 S04 본문 문장 속에 묻힘 ③Big Number 2개 + 한 줄 근거 ④GM 바로 아래 좌우 배치 ⑤SEE 3초 안에 KT의 약속이 각인",
 "evaluator":"'또 역량 자랑이네.' → '이 회사는 회선까지 같이 옮겨봤구나.'"}
```
Revised의 숫자(8시간, 1,180대)는 모두 원문(F1#S004)에 있는 숫자다. 원문에 없는 숫자를 쓰면 report.py가 `[VERIFY: 원문에 없는 수치]`를 붙인다.

## 3. 채팅 요약 형식 (리포트 생성 후)

```
**Overall**: 2~3줄
**Top 5 Winning Issues**: 1줄씩
**MUST FIX n건 · SHOULD FIX n건** · Compliance: MISSING x / CONFLICT y / HARD TO FIND z (Mode 1)
**파일**: <작업폴더>/01_executive.md …
```
