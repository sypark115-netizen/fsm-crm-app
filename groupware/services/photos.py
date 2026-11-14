"""현장 사진 저장(리사이즈·EXIF 회전 보정·썸네일)."""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from core.config import UPLOAD_DIR
from core.database import get_session
from core.models import Photo

MAX_EDGE = 1920
THUMB_EDGE = 480


def _process(fp: BinaryIO, dest: Path) -> tuple[Path, Path, int, int]:
    img = ImageOps.exif_transpose(Image.open(fp))  # 스마트폰 세로사진 회전 보정
    img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    img.save(dest, "JPEG", quality=85, optimize=True)  # 원본 EXIF(GPS 등) 제거 효과
    thumb = img.copy()
    thumb.thumbnail((THUMB_EDGE, THUMB_EDGE))
    tpath = dest.with_name(dest.stem + "_t.jpg")
    thumb.save(tpath, "JPEG", quality=80)
    return dest, tpath, img.width, img.height


def save_uploads(uploader_id: int, site_name: str, tags: list[str], files: list) -> list[Photo]:
    """files: st.file_uploader 가 반환한 UploadedFile 목록."""
    if not site_name.strip():
        raise ValueError("현장명을 입력해 주세요.")
    day_dir = UPLOAD_DIR / datetime.now().strftime("%Y%m")
    day_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Photo] = []
    with get_session() as s:
        for f in files:
            path, tpath, w, h = _process(f, day_dir / f"{uuid.uuid4().hex}.jpg")
            p = Photo(uploader_id=uploader_id, site_name=site_name.strip(), tags=",".join(tags),
                      file_path=str(path), thumb_path=str(tpath), original_name=f.name, width=w, height=h)
            s.add(p)
            saved.append(p)
    return saved


def list_photos(site: str | None = None, only_unpublished: bool = False, uploader_id: int | None = None) -> list[Photo]:
    with get_session() as s:
        q = select(Photo).options(joinedload(Photo.uploader)).order_by(Photo.uploaded_at.desc())
        if site:
            q = q.where(Photo.site_name == site)
        if only_unpublished:
            q = q.where(Photo.is_published.is_(False))
        if uploader_id is not None:
            q = q.where(Photo.uploader_id == uploader_id)
        return list(s.scalars(q))


def site_names() -> list[str]:
    with get_session() as s:
        return list(s.scalars(select(Photo.site_name).distinct().order_by(Photo.site_name)))


def set_public(photo_id: int, value: bool) -> None:
    with get_session() as s:
        photo = s.get(Photo, photo_id)
        if photo:
            photo.is_public = value
