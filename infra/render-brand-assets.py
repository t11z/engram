#!/usr/bin/env python3
"""Render the Engram brand mark into the raster icons and favicons.

The single source of truth for the brand mark is
``apps/web-ui/static/engram-logomark.svg`` (the amber seal, no background). This
script stamps it onto the design-system ink background (warm near-black, rounded
"stamp" corners) and rasterises it at every size the browser extension, web UI,
and docs site need, so the toolbar icon and favicons match the rest of the
product.

Run from the repo root:

    pip install cairosvg pillow   # one-off; not repo dependencies
    python3 infra/render-brand-assets.py

cairosvg needs the system cairo library; pillow does the rounded-corner
compositing and downscaling.
"""

from __future__ import annotations

import io
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
LOGOMARK = ROOT / "apps/web-ui/static/engram-logomark.svg"

# Design-system token (see apps/web-ui/src/app.css).
INK_900 = (11, 9, 7, 255)  # #0B0907 — warm near-black substrate

SS = 4  # supersample factor for crisp downscaling
MARK_SCALE = 0.86  # fraction of the canvas the mark spans
CORNER_RADIUS = 0.22  # corner radius as a fraction of icon size

# size -> output paths (relative to repo root)
TARGETS: dict[int, list[str]] = {
    16: ["apps/extension/public/icon/16.png"],
    32: ["apps/extension/public/icon/32.png"],
    48: ["apps/extension/public/icon/48.png"],
    128: ["apps/extension/public/icon/128.png"],
    256: [
        "apps/web-ui/static/favicon.png",
        "docs-site/docs/assets/favicon.png",
    ],
}


def _mark_png(px: int) -> Image.Image:
    """Rasterise the amber logomark to a transparent RGBA image, px*px."""
    png = cairosvg.svg2png(url=str(LOGOMARK), output_width=px, output_height=px)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def _render_icon(size: int) -> Image.Image:
    """Compose one icon: amber mark on a rounded ink square."""
    big = size * SS
    radius = round(big * CORNER_RADIUS)

    base = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    bg = Image.new("RGBA", (big, big), INK_900)
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=radius, fill=255)
    base.paste(bg, (0, 0), mask)

    mark_px = round(big * MARK_SCALE)
    mark = _mark_png(mark_px)
    offset = (big - mark_px) // 2
    base.alpha_composite(mark, (offset, offset))

    return base.resize((size, size), Image.LANCZOS)


def main() -> None:
    # Sanity-check the source actually contains the amber mark we expect.
    svg = LOGOMARK.read_text()
    if "<path" not in svg or "#D9983F" not in svg:
        raise SystemExit(f"unexpected source SVG (no amber <path>) in {LOGOMARK}")

    for size, rels in TARGETS.items():
        icon = _render_icon(size)
        for rel in rels:
            out = ROOT / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            icon.save(out, "PNG")
            print(f"wrote {rel} ({size}x{size})")


if __name__ == "__main__":
    main()
