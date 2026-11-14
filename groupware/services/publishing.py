"""원클릭 발행: 노출 체크된 사진 → 포트폴리오 DB 적재 + 마크다운 블로그 초안 생성/퍼블리싱."""
from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy import select

from core.config import BLOG_DIR, PORTFOLIO_DIR
from core.database import get_session
from core.models import BlogPost, Photo, PortfolioItem


class Publisher(Protocol):
    channel: str

    def publish(self, title: str, markdown: str, images: list[Path]) -> str | None:
        """외부 URL 반환(없으면 None)."""


class LocalPublisher:
    """기본: 로컬 파일로만 저장. 랜딩페이지는 portfolio.json 을 읽는다."""
    channel = "local"

    def publish(self, title: str, markdown: str, images: list[Path]) -> str | None:
        return None


# TODO: class NaverBlogPublisher / WordPressPublisher — 각 채널 API 키 확보 후 구현


@dataclass
class PublishResult:
    posts: list[BlogPost]
    item_count: int


def _slug(text: str) -> str:
    return re.sub(r"[^\w가-힣-]+", "-", text).strip("-")[:60] or "site"


def build_markdown(site_name: str, photos: list[Photo], public_paths: list[str]) -> tuple[str, str]:
    tags = sorted({t for p in photos for t in p.tag_list})
    title = f"[시공사례] {site_name} {' · '.join(tags[:3])} 현장 기록".strip()
    lines = [
        f"# {title}", "",
        f"> 작업 기간: {min(p.uploaded_at for p in photos):%Y.%m.%d} ~ {max(p.uploaded_at for p in photos):%Y.%m.%d}",
        f"> 공정: {', '.join(tags) or '-'}", "",
        "## 현장 소개", "",
        f"{site_name} 현장의 시공 과정을 사진으로 정리했습니다. <!-- TODO: 현장 특징/고객 요청사항 보강 -->", "",
        "## 시공 과정", "",
    ]
    for i, (p, path) in enumerate(zip(photos, public_paths), 1):
        lines += [f"![{site_name} {i}]({path})", f"*{', '.join(p.tag_list) or '현장'} — {p.uploaded_at:%m월 %d일}*", ""]
    lines += ["## 문의", "", "비슷한 공사를 계획 중이시라면 언제든 문의 주세요. <!-- TODO: 연락처/CTA -->", "",
              " ".join(f"#{t}" for t in [site_name.replace(" ", ""), *tags])]
    return title, "\n".join(lines)


def publish_selected(author_id: int, publisher: Publisher | None = None) -> PublishResult:
    publisher = publisher or LocalPublisher()
    posts: list[BlogPost] = []
    count = 0
    with get_session() as s:
        photos = list(s.scalars(select(Photo).where(Photo.is_public.is_(True), Photo.is_published.is_(False))
                                .order_by(Photo.uploaded_at)))
        by_site: dict[str, list[Photo]] = defaultdict(list)
        for p in photos:
            by_site[p.site_name].append(p)

        for site, group in by_site.items():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            site_dir = PORTFOLIO_DIR / f"{stamp}-{_slug(site)}"
            site_dir.mkdir(parents=True, exist_ok=True)
            public_paths = []
            for p in group:
                dst = site_dir / Path(p.file_path).name
                shutil.copy2(p.file_path, dst)
                public_paths.append(f"portfolio/{site_dir.name}/{dst.name}")

            title, md = build_markdown(site, group, public_paths)
            md_path = BLOG_DIR / f"{stamp}-{_slug(site)}.md"
            md_path.write_text(md, encoding="utf-8")
            external_url = publisher.publish(title, md, [site_dir / Path(x).name for x in public_paths])

            post = BlogPost(title=title, site_name=site, markdown=md, file_path=str(md_path),
                            channel=publisher.channel, external_url=external_url, author_id=author_id)
            s.add(post)
            s.flush()
            for p, path in zip(group, public_paths):
                s.add(PortfolioItem(photo_id=p.id, post_id=post.id, site_name=site, tags=p.tags,
                                    public_path=path, caption=f"{site} · {', '.join(p.tag_list)}"))
                p.is_published = True
                count += 1
            posts.append(post)
    export_portfolio_json()
    return PublishResult(posts=posts, item_count=count)


def export_portfolio_json() -> Path:
    """외부 랜딩페이지(정적 사이트/Next.js 등)가 읽을 시공사례 피드."""
    with get_session() as s:
        items = s.scalars(select(PortfolioItem).order_by(PortfolioItem.published_at.desc())).all()
        data = [{"id": i.id, "site": i.site_name, "tags": [t for t in i.tags.split(",") if t],
                 "image": i.public_path, "caption": i.caption, "published_at": i.published_at.isoformat()}
                for i in items]
    out = PORTFOLIO_DIR / "portfolio.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def list_posts() -> list[BlogPost]:
    with get_session() as s:
        return list(s.scalars(select(BlogPost).order_by(BlogPost.created_at.desc())))
