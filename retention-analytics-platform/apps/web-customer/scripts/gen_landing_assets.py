"""Generate animation + brand-video assets for the web-customer landing.

Outputs:
    public/anim/anim.css, public/anim/anim.js   (style_engines package)
    public/brand/intro.mp4, intro-poster.jpg    (LandingVideoService 'retention' scene)

Usage (from apps/web-customer):
    python scripts/gen_landing_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
REPO = APP.parent.parent
SHARED = REPO.parent / "shared-canonical-services"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from shared.branding import generate_landing_video  # noqa: E402
from shared.style_engines import (  # noqa: E402
    AnimationOptions,
    generate_animation_css,
    generate_animation_js,
    generate_theme_css,
)

# Dark SaaS analytics theme: deep navy, indigo/violet accent, emerald data color.
THEME_TOKENS = {
    "background_color": "rgb(9, 11, 26)",
    "text_color": "rgb(232, 235, 255)",
    "link_color": "rgb(129, 140, 248)",
    "heading_color": "rgb(255, 255, 255)",
    "font_family": "Inter, system-ui, sans-serif",
    "color_palette": [
        "rgb(9, 11, 26)",
        "rgb(232, 235, 255)",
        "rgb(129, 140, 248)",
        "rgb(52, 211, 153)",
        "rgb(251, 113, 133)",
    ],
}

PRESET = {
    "level": "premium",
    "gsap_enabled": True,
    "split_scrub": True,
    "text_fade_blur": True,
    "scroll_read": True,
    "clip_reveal": True,
    "reveal_group": True,
    "marquee": True,
    "counting_number": True,
    "cursor_marquee": True,
    "btn_hover_fill": True,
    "glow": True,
    "tilt_3d": True,
    "wipe_mask": True,
    "svg_draw": True,
    "pinned_storytelling": True,
    "intro_video": True,
    "loading_sequence": True,
    "page_transitions": True,
    "scroll_progress_ring": True,
    "progress_bars": True,
    "progressive_blur": True,
    "chart_animations": True,
    "parallax_intensity": 0.3,
    "animated_grain": False,
    "noise_overlay": True,
    "reduced_motion": "respect",
}


def main() -> int:
    anim = APP / "public" / "anim"
    brand = APP / "public" / "brand"
    anim.mkdir(parents=True, exist_ok=True)
    brand.mkdir(parents=True, exist_ok=True)

    opts = AnimationOptions.from_dict(dict(PRESET))
    css = generate_theme_css(THEME_TOKENS) + "\n" + generate_animation_css(opts)
    js = generate_animation_js(opts)
    (anim / "anim.css").write_text(css, encoding="utf-8")
    (anim / "anim.js").write_text(js, encoding="utf-8")
    print(f"[+] {anim/'anim.css'} ({len(css)} B), {anim/'anim.js'} ({len(js)} B)")

    resp = generate_landing_video(
        "retention", brand / "intro.mp4", poster_path=brand / "intro-poster.jpg", seconds=5, fps=24
    )
    if not resp.success:
        print(f"[!] video failed: {resp.error}")
        return 1
    print(f"[+] {resp.data.get('path')} ({resp.data.get('format')}) + poster")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
