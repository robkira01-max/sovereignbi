"""Generate MizanBI brand raster assets (favicons, app icons, Open Graph image).

Social networks (LinkedIn, Facebook, X) and iOS/Android do not render SVG for
og:image / touch icons, so PNG/ICO files are produced here from the brand colours
(oklch(65% .22 265) blue -> oklch(68% .18 155) green, as in the login logo).

Usage: .venv/bin/python tools/make_brand_assets.py   (needs Pillow)
Output: mizanbi-client/public/{favicon.ico,apple-touch-icon.png,icon-192.png,
        icon-512.png,icon-maskable-512.png,og-image.png}
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent.parent / "mizanbi-client" / "public"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BG = (7, 7, 17)  # #070711


def oklch(l: float, c: float, h_deg: float) -> tuple[int, int, int]:
    h = math.radians(h_deg)
    a, b = c * math.cos(h), c * math.sin(h)
    l_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (l - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )

    def enc(x: float) -> int:
        x = max(0.0, min(1.0, x))
        x = 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
        return round(x * 255)

    return tuple(enc(v) for v in rgb)  # type: ignore[return-value]


BLUE = oklch(0.65, 0.22, 265)
GREEN = oklch(0.68, 0.18, 155)


def gradient(size: int) -> Image.Image:
    """Diagonal blue -> green gradient (135deg), size x size."""
    g = Image.new("RGB", (size, size))
    px = g.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            px[x, y] = tuple(round(BLUE[i] + (GREEN[i] - BLUE[i]) * t) for i in range(3))
    return g


def logo(size: int, *, rounded: bool, letter_scale: float = 0.62) -> Image.Image:
    """Gradient tile with a dark 'M'. Drawn at 4x then downsampled for clean edges."""
    big = size * 4
    tile = gradient(big).convert("RGBA")
    d = ImageDraw.Draw(tile)
    font = ImageFont.truetype(FONT_BOLD, round(big * letter_scale))
    d.text((big / 2, big / 2), "M", font=font, fill=BG + (255,), anchor="mm")
    if rounded:
        mask = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=round(big * 0.22), fill=255)
        tile.putalpha(mask)
    return tile.resize((size, size), Image.LANCZOS)


def og_image() -> Image.Image:
    w, h, s = 1200, 630, 2
    img = Image.new("RGB", (w * s, h * s), BG)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 10 * s, h * s), fill=BLUE)
    # soft accent glow bottom-right
    glow = Image.new("RGB", (w * s, h * s), BG)
    gd = ImageDraw.Draw(glow)
    for r in range(420 * s, 0, -6 * s):
        k = 1 - r / (420 * s)
        col = tuple(round(BG[i] + (GREEN[i] * 0.22 - BG[i]) * k) for i in range(3))
        gd.ellipse((w * s - r, h * s - r, w * s + r, h * s + r), fill=col)
    img = Image.blend(img, glow, 0.9)
    d = ImageDraw.Draw(img)

    img.paste(logo(150 * s, rounded=True), (80 * s, 120 * s), logo(150 * s, rounded=True))
    f_title = ImageFont.truetype(FONT_BOLD, 104 * s)
    f_tag = ImageFont.truetype(FONT_BOLD, 42 * s)
    f_sub = ImageFont.truetype(FONT_REG, 30 * s)
    d.text((262 * s, 195 * s), "MizanBI", font=f_title, fill=(255, 255, 255), anchor="lm")
    d.text((80 * s, 360 * s), "L'IA vient à vos données,", font=f_tag, fill=BLUE, anchor="ls")
    d.text((80 * s, 418 * s), "pas l'inverse.", font=f_tag, fill=BLUE, anchor="ls")
    d.text((80 * s, 520 * s), "BI conversationnelle · Auto-hébergée · Souveraine", font=f_sub, fill=(190, 195, 215), anchor="ls")
    return img.resize((w, h), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    logo(256, rounded=True).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    # Apple touch icon: opaque full-bleed square (iOS applies its own rounding)
    logo(180, rounded=False, letter_scale=0.6).convert("RGB").save(OUT / "apple-touch-icon.png")
    logo(192, rounded=True).save(OUT / "icon-192.png")
    logo(512, rounded=True).save(OUT / "icon-512.png")
    # Maskable: full bleed, letter inside the 80% safe zone
    logo(512, rounded=False, letter_scale=0.5).convert("RGB").save(OUT / "icon-maskable-512.png")
    og_image().save(OUT / "og-image.png", optimize=True)
    for f in sorted(OUT.glob("*.png")) + [OUT / "favicon.ico"]:
        print(f"{f.name:26s} {f.stat().st_size:>8,d} B")


if __name__ == "__main__":
    main()
