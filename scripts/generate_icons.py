#!/usr/bin/env python3
"""Generate deterministic PNG, ICNS source sizes, and Windows ICO assets."""

from pathlib import Path
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICONSET = ASSETS / "app-icon.iconset"


def render(size: int) -> Image.Image:
    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    factor = size * scale / 1024
    point = lambda pair: tuple(round(value * factor) for value in pair)
    draw.rounded_rectangle((0, 0, size * scale - 1, size * scale - 1), radius=round(150 * factor), fill="#080d18")
    route = [point(pair) for pair in ((214, 730), (382, 526), (526, 617), (782, 286))]
    draw.line(route, fill="#61a8ff", width=round(104 * factor), joint="curve")
    for x, y in route:
        radius = round(52 * factor)
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill="#61a8ff")
    draw.line(route, fill="#8bc5ff", width=round(34 * factor), joint="curve")
    for x, y in route:
        radius = round(17 * factor)
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill="#8bc5ff")
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    ICONSET.mkdir(exist_ok=True)
    render(1024).save(ASSETS / "app-icon.png")
    render(64).save(ASSETS / "tray-icon-64.png")
    render(32).save(ASSETS / "tray-icon-32.png")
    sizes = {"icon_16x16.png": 16, "icon_16x16@2x.png": 32, "icon_32x32.png": 32, "icon_32x32@2x.png": 64, "icon_128x128.png": 128, "icon_128x128@2x.png": 256, "icon_256x256.png": 256, "icon_256x256@2x.png": 512, "icon_512x512.png": 512, "icon_512x512@2x.png": 1024}
    for name, size in sizes.items():
        render(size).save(ICONSET / name)
    render(256).save(ASSETS / "app-icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    render(64).save(ASSETS / "tray-icon.ico", sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (48, 48), (64, 64)])


if __name__ == "__main__":
    main()
