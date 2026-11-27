# 인사이트 서재 (Personal AI Digital Library)

업무와 의사결정에 바로 적용할 인사이트를 쌓는 개인 디지털 서재. Next.js 16 (App Router) + Tailwind CSS v4.
DB 없이 **로컬 파일**에만 저장하므로 서버를 다시 켜도 데이터가 그대로 남습니다.

## 실행
```bash
cd digital-library
npm install
npm run dev        # http://localhost:3000
```
샘플 데이터 초기화(복습 날짜를 오늘 기준으로 다시 계산): `npm run reset-data`
(현재 books.json은 `data/backup-*.json`으로 백업한 뒤 덮어씁니다)

## 폴더 구조
```
digital-library/
├─ app/
│  ├─ page.tsx                    # 대시보드(복습 리마인더·책장·위시리스트)
│  ├─ books/[id]/page.tsx         # 도서 상세(3단 탭 + 연관 도서)
│  └─ api/
│     ├─ library/route.ts         # GET  전체 데이터
│     ├─ books/route.ts           # POST 도서 등록
│     ├─ books/[id]/route.ts      # GET/PATCH/DELETE 도서
│     ├─ books/[id]/notes/[kind]/route.ts  # PUT 요약·메모 .md 저장
│     ├─ categories/route.ts      # POST/PATCH/DELETE 카테고리
│     └─ wishlist/route.ts        # POST/DELETE 읽을 책
├─ components/                    # Dashboard, BookDetailView, AddBookModal, Markdown 등
├─ lib/
│  ├─ store.ts                    # 파일 읽기/쓰기(쓰기 직렬화 + 원자적 저장)
│  ├─ review.ts                   # 에빙하우스 복습 스케줄 계산
│  └─ types.ts
├─ data/
│  ├─ books.json                  # 카테고리·도서·액션 체크·하이라이트·복습 기록·위시리스트
│  ├─ notes/{bookId}--short.md    # 2,000자 압축본
│  ├─ notes/{bookId}--long.md     # 10,000자 심화본
│  ├─ notes/{bookId}--memo.md     # 현장 적용 메모
│  └─ seed/                       # reset-data용 원본
└─ scripts/reset-data.mjs
```

## 기능
- **분야별 책장**: 기본 5개 분야 + 전체, 카테고리 추가/이름 변경/삭제(‘편집’), 카드·리스트 보기 전환(브라우저에 기억), 검색
- **도서 상세 3단 탭**: ① 핵심 요약(기본 정보·시대/산업 배경·3줄 메시지·압축본/심화본 전환, 마크다운 편집) ② 실전 실행 인사이트(체크박스, 추가/더블클릭 수정/삭제) ③ 북마크 & 메모(하이라이트 저장, 현장 적용 메모)
- **에빙하우스 복습**: 등록일 기준 1·3·7·30일차. 도래했지만 완료하지 않은 가장 이른 단계를 대시보드 상단에 표시, ‘복습 완료’ 체크. 상세 화면의 단계 배지로 완료/취소 가능
- **연관 도서**: 상세 하단 4~5권 + 추천 이유, 클릭 한 번으로 위시리스트 추가 → 위시리스트에서 ‘서재에 등록’

## 참고
- 데이터는 `data/` 폴더 파일이 전부입니다. 이 폴더를 백업/동기화(예: Git, 클라우드 드라이브)하면 됩니다.
- 로컬 1인 사용 전제로 인증이 없습니다. 외부에 공개된 서버로 띄우지 마세요.
