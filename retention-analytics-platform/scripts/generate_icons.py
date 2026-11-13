"""Generate the PWA icons referenced by /api/seo/manifest.

Run: python scripts/generate_icons.py
Writes apps/web-customer/public/brand/icon-{192,512}.png
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "web-customer" / "public" / "brand"
ACCENT = (79, 70, 229)      # indigo-600
ACCENT_DARK = (67, 56, 202)  # indigo-700


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(size * 0.22)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=ACCENT)
    # "RA" mark
    pad = int(size * 0.26)
    bar_w = int(size * 0.085)
    top = int(size * 0.32)
    bottom = int(size * 0.70)
    # R
    d.rounded_rectangle((pad, top, pad + bar_w, bottom), radius=bar_w // 2, fill=(255, 255, 255, 255))
    d.arc((pad, top, pad + int(size * 0.30), top + int(size * 0.40)), start=0, end=180,
           fill=(255, 255, 255, 255), width=bar_w)
    d.line((pad + int(size * 0.15), top + int(size * 0.20), pad + int(size * 0.29), bottom),
           fill=(255, 255, 255, 255), width=bar_w)
    # A
    ax = int(size * 0.55)
    aw = int(size * 0.30)
    d.polygon([(ax, bottom), (ax + aw // 2, top), (ax + aw, bottom)], outline=(255, 255, 255, 255))
    d.line((ax + aw // 5, bottom - int(size * 0.20), ax + aw - aw // 5, bottom - int(size * 0.20)),
           fill=(255, 255, 255, 255), width=max(2, bar_w // 2))
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        path = OUT / f"icon-{size}.png"
        draw(size).save(path)
        print(f"wrote {path}")
    # apple-touch-icon
    draw(180).save(OUT / "apple-touch-icon.png")
    print(f"wrote {OUT / 'apple-touch-icon.png'}")


if __name__ == "__main__":
    main()
