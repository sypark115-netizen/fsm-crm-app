---
name: kinetic-typography
description: 인터뷰·대담 영상에 키네틱 타이포그래피 자막을 입힐 때 사용. 하단 화자 자막(키워드 강조·펄스), 중앙 키워드 카드(예 SSOT, PRD, 기능 명세서, 유저 플로우 + 한 줄 풀이), 강조 문구(punch/typewriter/slide)를 ASS로 만들어 ffmpeg로 번인하고 프레임으로 검증한다. 「자막 모션그래픽」「키워드 자막」「타이포 애니메이션」「인터뷰 자막 입혀줘」 요청에 쓴다.
---

# 키네틱 타이포그래피 자막 (인터뷰용)

인터뷰이·진행자의 대화에서 **핵심 키워드·개념·강조 문구**를 뽑아
화면 하단과 중앙에 폰트 애니메이션으로 노출한다.

| 레이어 | 위치 | 동작 |
|---|---|---|
| 하단 자막 | 하단 중앙 | 화자 이름(색 구분) + 대사, 페이드·슬라이드업. 키워드는 강조색으로, **말하는 시점에** 펄스(116%→100%) |
| 키워드 카드 | 중앙 상단(38%) | 용어가 처음 나올 때 팝인(40→112→100%) + 아래에 한 줄 풀이 페이드인. 카드끼리·강조 문구와 안 겹치게 자동 대기열 |
| 강조 문구 | 중앙(42%) | `punch` 단어별 팝 / `typewriter` 글자별 / `slide` 좌→우 |

엔진은 `scripts/kinetic_subs.py` (표준 라이브러리만 사용, 렌더는 ffmpeg+libass).

## 절차

### 1. 큐시트를 만든다
`examples/interview_cues.json` 형식. 대사 타임코드는 **녹취(STT)·SRT의 실제 시간**을 쓴다. 추정해서 만들지 않는다.
SRT를 받으면 블록마다 `{start, end, speaker, text}`로 옮긴다.

```json
{
  "video": {"width": 1920, "height": 1080},
  "speakers": {"host": {"name": "진행자", "color": "#7FDBFF"},
               "guest": {"name": "허재혁 대표", "color": "#FFC93C"}},
  "keywords": [{"term": "SSOT", "aliases": ["단일 진실 공급원"],
                "gloss": "Single Source of Truth · 단일 진실 공급원"}],
  "lines":    [{"start": 3.4, "end": 7.0, "speaker": "guest", "text": "..."}],
  "emphasis": [{"start": 27.4, "end": 31.0, "text": "원본은 하나, 나머지는 링크", "style": "punch"}],
  "cards":    [{"start": 40.0, "term": "MVP", "gloss": "..."}]
}
```

- 시간은 초(`3.4`) 또는 `mm:ss.s` / `hh:mm:ss,ms`.
- `keywords`: 대사에서 자동으로 찾아 강조하고, 첫 등장 때 카드를 띄운다. 띄어쓰기 변형(`기능명세서`)·영문 표기(`user flow`)는 `aliases`에 넣는다. 카드 없이 강조만 하려면 `"card": false`.
- `emphasis`: 영상의 결론·명언급 한 문장. **한 편에 2~4개**만. 많으면 아무것도 강조되지 않는다.
- `cards`: 대사에 단어가 안 나오지만 띄울 카드(수동).
- `style`로 기본값 덮어쓰기: `accent`, `font`, `card_y`, `emph_y`, `caption_scale`, `keyword_once`, `max_cps` 등 (스크립트 상단 `DEFAULT_STYLE`).
- 세로 숏폼은 `"video": {"width": 1080, "height": 1920}`. 글자 크기는 짧은 변 기준이라 자동으로 맞는다.

### 키워드 고르는 기준
1. 시청자가 **처음 듣거나 약어인** 용어 (SSOT, PRD) → 카드 + 풀이
2. 영상 주제를 구성하는 개념 (기능 명세서, 유저 플로우) → 카드
3. 자주 나오지만 설명이 필요 없는 단어 → `"card": false`로 강조만
4. 풀이(gloss)는 **25자 안팎 한 줄**. 정의를 지어내지 말고, 인터뷰이가 설명한 뜻이 있으면 그 표현을 쓴다.

### 2. 검증 → 렌더
```bash
S=.claude/skills/kinetic-typography/scripts
python3 $S/kinetic_subs.py cues.json --check            # 검증만
python3 $S/kinetic_subs.py cues.json -o out.ass \
  --render input.mp4 output.mp4 --frames frames/        # ASS + 번인 + 미리보기 프레임
```
`errors`가 있으면 종료 코드 1이고 파일을 쓰지 않는다. `--strict`는 경고도 실패로 처리.

| 검사 | 수준 |
|---|---|
| 시작 ≥ 끝, 자막 시간 겹침, 정의 안 된 화자 | error |
| 읽기 속도 > 16자/초, 0.8초 미만 노출, 2줄 초과 | warning → 대사를 나누거나 시간을 늘린다 |
| 키워드가 대사에 한 번도 안 나옴 (오타·alias 누락) | warning |
| 카드가 몰려 1.2초 넘게 밀림 → 생략됨 | warning → `cards`로 시점을 직접 지정 |

한글 폰트가 없으면 `apt-get install -y fonts-noto-cjk`. 기본 폰트는 `Noto Sans CJK KR` (Bold).

### 3. 프레임을 눈으로 본다 (생략 금지)
`--frames`가 카드마다 1장, 강조 문구 끝(모든 단어가 나온 뒤) 1장, 가장 긴 자막 1장을 뽑는다. **Read로 전부 열어 본다.**
- [ ] 자막이 화면 밖으로 잘리지 않는가 (특히 세로 영상)
- [ ] 카드·강조 문구가 인물 얼굴을 가리지 않는가 → 가리면 `style.card_y`/`emph_y` 조정 (예: 0.22)
- [ ] 강조색 키워드가 배경에서 읽히는가
- [ ] 화자 이름이 맞는가

모션 자체를 확인할 때는 카드 시작 직후 0.4초를 한 장으로 본다:
```bash
ffmpeg -ss <카드시작-0.1> -i output.mp4 -t 0.4 -vf "fps=20,scale=480:-1,tile=2x4" -frames:v 1 strip.jpg
```

### 4. 납품
- `output.mp4`(번인본)와 `out.ass`(편집툴에서 다시 쓸 수 있는 자막 원본)를 함께 준다.
- Premiere/DaVinci 편집자에게는 ASS를 넘기거나, 번인본을 별도 트랙으로 쓴다.
- 영상만 바꿀 때는 ASS를 다시 쓸 필요가 없다. 대사만 고칠 때는 큐시트를 고치고 다시 렌더한다.

## 하지 않는 것
- 인터뷰이가 하지 않은 말을 강조 문구·풀이로 만들지 않는다. 강조 문구는 대사에서 그대로 따오거나 줄이기만 한다.
- 한 화면에 카드와 강조 문구를 동시에 띄우지 않는다 (엔진이 막는다).
- 같은 키워드 카드를 반복하지 않는다 (`keyword_once: true` 기본). 두 번째 등장부터는 하단 강조만 한다.

## 테스트
```bash
python3 -m unittest discover -s .claude/skills/kinetic-typography/scripts -v
```
색상 변환·시간 표기·이스케이프·줄바꿈·키워드 매칭(줄바꿈을 걸친 경우 포함)·카드 겹침 방지·검증 규칙·세로 영상 스케일, 그리고 ffmpeg가 있으면 실제 번인 후 픽셀이 바뀌었는지까지 확인한다 (14개).
