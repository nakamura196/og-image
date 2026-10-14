#!/usr/bin/env python3
"""サイトのアイコンを「色の地に白い字を 1〜2 字」の型で作る。

作るもの（out_dir の下）:
  icon.svg              文字は線の形にして埋め込む（見る人の書体に左右されない）
  apple-touch-icon.png  180px、角を丸めない正方形（iPhone 側で丸める）
  favicon.ico           16 / 32 / 48px

head に書くタグ:
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" href="/icon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">

使い方:
  python3 site_icon.py --text R --bg "#c8102e" --out public
  og_image.py の設定ファイルに "site_icon": {"text": "R", "bg": "#c8102e", "out": "public"}
  と書けば、共有画像を作る前にアイコンも作り、共有画像の左上にも使う。

字体は Noto Sans JP（SIL OFL）の太字。fontTools と rsvg-convert（brew の librsvg）を使う。
1 字が基本。2 字は 32px 以上では読めるが、ブラウザのタブ（16px）では潰れる。
"""
import argparse
import io
import subprocess
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image

FONT = Path("~/Library/Fonts/NotoSansJP[wght].ttf").expanduser()
WEIGHT = 700
S = 512                 # SVG の一辺
RADIUS = 0.22           # 角の丸み（一辺に対する割合）
BOX_W, BOX_H = 0.70, 0.56   # 字の外形を収める枠（一辺に対する割合）


def text_path(text):
    """文字列を 1 本の SVG パスにし、枠の中央に置く"""
    if not FONT.exists():
        sys.exit(f"字体がありません: {FONT}（Noto Sans JP を入れてください）")
    font = TTFont(FONT)
    cmap = font.getBestCmap()
    gs = font.getGlyphSet(location={"wght": WEIGHT})
    # 字を横に並べ、全体の外形を測る
    placed, x = [], 0
    for ch in text:
        if ord(ch) not in cmap:
            sys.exit(f"字体に「{ch}」がありません")
        g = gs[cmap[ord(ch)]]
        placed.append((g, x))
        x += g.width
    bp = BoundsPen(gs)
    for g, dx in placed:
        g.draw(TransformPen(bp, (1, 0, 0, 1, dx, 0)))
    x0, y0, x1, y1 = bp.bounds
    k = min(S * BOX_W / (x1 - x0), S * BOX_H / (y1 - y0))
    # 外形の中心を正方形の中心へ（y は上下を反転）
    tx = S / 2 - k * (x0 + x1) / 2
    ty = S / 2 + k * (y0 + y1) / 2
    sp = SVGPathPen(gs)
    for g, dx in placed:
        g.draw(TransformPen(sp, (k, 0, 0, -k, tx + k * dx, ty)))
    return sp.getCommands()


def svg(text, bg, rounded=True):
    r = round(S * RADIUS) if rounded else 0
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}">'
            f'<rect width="{S}" height="{S}" rx="{r}" fill="{bg}"/>'
            f'<path fill="#fff" d="{text_path(text)}"/></svg>\n')


def png(svg_text, size):
    out = subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size)],
                         input=svg_text.encode(), capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(out)).convert("RGBA")


def make_icons(text, bg, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rounded = svg(text, bg)
    (out_dir / "icon.svg").write_text(rounded, "utf-8")
    png(svg(text, bg, rounded=False), 180).convert("RGB").save(out_dir / "apple-touch-icon.png", optimize=True)
    # .ico は大きさごとに描いて詰める（縮小で済ませると 16px がにじむ）
    ico = [png(rounded, n) for n in (48, 32, 16)]
    ico[0].save(out_dir / "favicon.ico", sizes=[(n, n) for n in (48, 32, 16)], append_images=ico[1:])
    for name in ("icon.svg", "apple-touch-icon.png", "favicon.ico"):
        print(f"{out_dir / name}  {(out_dir / name).stat().st_size // 1024 or 1} KB")
    return out_dir / "icon.svg"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--text", required=True, help="1〜2 字")
    ap.add_argument("--bg", required=True, help="地の色（#rrggbb）")
    ap.add_argument("--out", required=True, help="書き出し先のフォルダ")
    a = ap.parse_args()
    if len(a.text) > 2:
        print("注意: 3 字以上は小さい大きさで読めません")
    make_icons(a.text, a.bg, a.out)


if __name__ == "__main__":
    sys.exit(main())
