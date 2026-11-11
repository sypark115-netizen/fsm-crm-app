# Tech-to-Value ★

모든 주요 기술 메시지에 다음 사슬을 적용한다.

```
Technology → Capability → Process Change → Business Impact → Executive Value
```
예:
```
AI Agent
→ 자료 탐색·분석·작성·실행
→ 사람이 하던 반복 업무를 AI가 선처리
→ 처리시간·오류·대응속도 개선   (원문 수치가 있을 때만 숫자)
→ 사람은 고객·판단·의사결정에 집중
```

## 엔진이 주는 것
- `tech_terms`: 메시지 속 기술어와 **일반 Capability 힌트** (km_common.TECH_TERMS). 힌트는 사실이 아니다. 고객 자료에서 확인된 업무로 바꿔 쓴다.
- `tech_to_value_chain`: 위 5단 사슬 틀. Process Change 이후는 원문/근거에서 채운다.
- `Tech → Value` 플래그: 기술어는 있는데 가치어·업무어가 없을 때.

## 쓰는 법
1. 기술명을 주어에서 내린다. "생성형 AI 기반 ○○를 구축합니다" → 업무가 주어.
2. Capability를 **동사**로 쓴다: 찾는다, 정리한다, 초안을 쓴다, 연결한다, 대신 응대한다.
3. Process Change는 **누가 무엇을 덜/더 하는지**로 쓴다.
4. Business Impact 숫자는 원문·RFP·Reference에 있을 때만. 없으면 방향(줄인다, 바로 확인한다)만 쓴다.
5. Executive Value는 Audience에 맞춘다 → `audience-rules.md`.

| BAD | BETTER |
|---|---|
| 생성형 AI 기반 지능형 업무환경을 구축합니다. | 자료 탐색과 초안 작성은 AI가 맡고, 담당자는 검토와 의사결정에 집중합니다. |
| Data Platform을 구축하여 데이터 기반 의사결정을 지원합니다. | 흩어진 판매·재고 데이터를 한 화면에서 보고, 발주 판단을 하루 앞당깁니다. (하루: 원문 근거 있을 때) |
| AICC 도입으로 고객 경험을 혁신합니다. | 단순 문의는 AI가 바로 답하고, 상담원은 해지·불만 상담에 집중합니다. |
| MSP 서비스를 통해 안정적인 운영을 지원합니다. | 장애 감지부터 1차 조치까지 24시간 대신 맡고, 고객 IT팀은 개선 과제에 집중합니다. |
