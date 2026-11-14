"""마케팅 연출샷 자동 가공 (Pillow 기반, 생성형 AI 연동 지점은 TODO).

- before_after(): 전/후 비교 컷 (좌우 분할 + 라벨)
- triptych(): 3장 공정 스토리 컷 (철거→시공→완공)
- enhance(): 자동 보정 (노출/대비/채도/샤프닝)
- watermark(): 로고/상호 워터마크
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

BRAND_BLUE = (30, 111, 255)
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]


def _font(size: int) -> ImageFont.ImageFont:
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def _open(src) -> Image.Image:
    if isinstance(src, Image.Image):
        return src.convert("RGB")
    if hasattr(src, "seek"):
        src.seek(0)  # 같은 UploadedFile 을 여러 번 읽기 때문
    return ImageOps.exif_transpose(Image.open(src)).convert("RGB")


def _fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(img, size, Image.Resampling.LANCZOS)


def _label(img: Image.Image, text: str, pos: str = "tl") -> None:
    d = ImageDraw.Draw(img)
    f = _font(max(18, img.width // 22))
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    w, h, pad = r - l, b - t, max(8, img.width // 60)
    x = pad if pos.endswith("l") else img.width - w - pad * 3
    y = pad
    d.rounded_rectangle((x, y, x + w + pad * 2, y + h + pad * 2), radius=pad, fill=BRAND_BLUE)
    d.text((x + pad - l, y + pad - t), text, font=f, fill="white")


def enhance(src, strength: float = 1.0) -> Image.Image:
    img = ImageOps.autocontrast(_open(src), cutoff=1)
    img = ImageEnhance.Brightness(img).enhance(1 + 0.05 * strength)
    img = ImageEnhance.Color(img).enhance(1 + 0.15 * strength)
    img = ImageEnhance.Contrast(img).enhance(1 + 0.08 * strength)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=int(80 * strength), threshold=3))


def before_after(before, after, size: tuple[int, int] = (1080, 1080), vertical: bool = False) -> Image.Image:
    w, h = size
    cell = (w, h // 2) if vertical else (w // 2, h)
    b, a = _fit(_open(before), cell), _fit(enhance(after), cell)
    _label(b, "BEFORE")
    _label(a, "AFTER")
    canvas = Image.new("RGB", size, "white")
    canvas.paste(b, (0, 0))
    canvas.paste(a, (0, h // 2) if vertical else (w // 2, 0))
    d = ImageDraw.Draw(canvas)
    if vertical:
        d.line((0, h // 2, w, h // 2), fill="white", width=6)
    else:
        d.line((w // 2, 0, w // 2, h), fill="white", width=6)
    return canvas


def triptych(images: list, labels: tuple[str, ...] = ("STEP 1", "STEP 2", "완공"),
             size: tuple[int, int] = (1080, 1350)) -> Image.Image:
    if len(images) != 3:
        raise ValueError("사진 3장이 필요합니다.")
    w, h = size
    hero_h = int(h * 0.6)
    small = ((w - 6) // 2, h - hero_h - 6)
    first, second, hero = (_open(i) for i in images)
    canvas = Image.new("RGB", size, "white")
    hero_img = _fit(enhance(hero), (w, hero_h))
    _label(hero_img, labels[2])
    canvas.paste(hero_img, (0, 0))
    for idx, (img, lab) in enumerate(((first, labels[0]), (second, labels[1]))):
        tile = _fit(img, small)
        _label(tile, lab)
        canvas.paste(tile, (idx * (small[0] + 6), hero_h + 6))
    return canvas


def watermark(img: Image.Image, text: str) -> Image.Image:
    img = img.copy()
    d = ImageDraw.Draw(img, "RGBA")
    f = _font(max(16, img.width // 40))
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    d.text((img.width - (r - l) - 20, img.height - (b - t) - 20), text, font=f, fill=(255, 255, 255, 200))
    return img


def to_jpeg_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


# TODO(AI): 배경 정리/하늘 교체/가구 배치 등 생성형 연출은 외부 이미지 API로 위임하는 훅을 여기에 추가
