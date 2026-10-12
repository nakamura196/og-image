#!/usr/bin/env python3
"""サイトの共有用画像（OGP、1200×630 JPEG）を、どのサイトでも同じ型で作る。

材料はサイト自身の HTML の head から読む（公開中の URL か、ビルド済みの HTML ファイル）。
  - アイコン:  link rel=icon の SVG > apple-touch-icon > その他の icon > /favicon.ico
  - タイトル:  og:site_name > og:title > title
  - 説明:      og:description > meta description
  - 画像:      設定ファイルの image（自分の写真など）。無ければ文字だけの型にする
  - 強調色:    設定の accent > meta theme-color > アイコンのいちばん鮮やかな色
head に無いもの・変えたいものだけ、設定ファイル（JSON）で上書きする。

配置: 左上にアイコンとドメイン、その下にタイトル（2 行に収まるまで字を小さくする）と
説明（3 行まで、超えたら「…」）。右半分に画像。画像が無ければ文字を全幅にする。

使い方:
  python3 og_image.py og-image.json        # 設定ファイルに書いた全ページ分を作る
  python3 og_image.py --url https://browser.ldas.jp/ --out og-ja.jpg

設定ファイルの例（パスは設定ファイルからの相対）:
  {
    "accent": "#0b5cad",
    "pages": [
      {"url": "https://browser.ldas.jp/",    "out": "public/og-ja.jpg"},
      {"url": "https://browser.ldas.jp/en/", "out": "public/og-en.jpg",
       "image": "photos/hero.jpg", "credit": "Photo: ..."}
    ]
  }
ページごとの項目: url | html, out, title, description, icon, image, credit, accent, domain

字体は macOS のヒラギノ角ゴシック。SVG のアイコンは rsvg-convert（brew の librsvg）で描く。
"""
import argparse
import colorsys
import io
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
SPLIT = 600            # 画像の左端
PAD = 64
ICON = 64
BAR = 10
INK = (31, 34, 40)
GREY = (88, 92, 100)
FONT_BOLD = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
FONT_TEXT = "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"
UA = {"User-Agent": "og-image (nakamura196)"}

# 行頭に来てはいけない字と、行末に来てはいけない字（禁則）
NO_START = set("、。，．,.:;!?！？）)」』】〕〉》ー〜ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ・…")
NO_END = set("（(「『【〔〈《")


# ---------- head を読む ----------

class Head(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta, self.icons, self.title, self.lang, self._in_title = {}, [], None, None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title" and self.title is None:
            self._in_title, self.title = True, ""
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key and key not in self.meta and a.get("content"):
                self.meta[key] = a["content"].strip()
        elif tag == "link" and "icon" in (a.get("rel") or "").lower().split():
            self.icons.append(a)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.geturl(), r.read(), r.headers.get("content-type", "")


def read_source(page, base):
    """page の url か html から head を読み、(Head, 基準 URL か None, 基準フォルダ) を返す"""
    if page.get("html"):
        path = (base / page["html"]).resolve()
        h = Head()
        h.feed(path.read_text("utf-8", "replace"))
        return h, page.get("url"), path.parent
    final, body, _ = fetch(page["url"])
    h = Head()
    h.feed(body.decode("utf-8", "replace"))
    return h, final, None


def pick_icon(head):
    def score(a):
        rel, typ, href = (a.get("rel") or "").lower(), (a.get("type") or "").lower(), a.get("href") or ""
        if "svg" in typ or href.split("?")[0].endswith(".svg"):
            return 3
        if "apple-touch-icon" in rel:
            return 2
        sizes = [int(n) for n in re.findall(r"(\d+)x\d+", a.get("sizes") or "")]
        return 1 + (max(sizes) if sizes else 0) / 10000
    icons = [a for a in head.icons if a.get("href") and not a["href"].startswith("data:")]
    return max(icons, key=score)["href"] if icons else "/favicon.ico"


def load_bytes(ref, page_url, page_dir, base):
    """URL・サイト内のパス・設定ファイルからの相対パスのどれでも読む"""
    if re.match(r"https?://", ref):
        return fetch(ref)[1]
    if Path(ref).expanduser().is_absolute() and Path(ref).expanduser().exists():
        return Path(ref).expanduser().read_bytes()
    if page_url and (ref.startswith("/") or page_dir is None):
        return fetch(urllib.parse.urljoin(page_url, ref))[1]
    for d in [page_dir, base]:
        if d and (d / ref.lstrip("/")).exists():
            return (d / ref.lstrip("/")).read_bytes()
    raise FileNotFoundError(ref)


def load_icon(data, size):
    if data.lstrip()[:5] in (b"<?xml", b"<svg ") or b"<svg" in data[:300]:
        png = subprocess.run(["rsvg-convert", "-w", str(size * 4), "-h", str(size * 4), "-a"],
                             input=data, capture_output=True, check=True).stdout
        im = Image.open(io.BytesIO(png))
    else:
        im = Image.open(io.BytesIO(data))
        if getattr(im, "n_frames", 1) > 1 or im.format == "ICO":  # .ico は中のいちばん大きい絵
            im.size = max(im.info.get("sizes", [im.size]))
        if im.width < 96:
            print(f"  注意: アイコンが {im.width}px しかなく、ぼやけます。SVG か 180px 以上を用意してください")
    im = im.convert("RGBA")
    im.thumbnail((size, size), Image.LANCZOS)
    return im


def vivid_colour(icon):
    """アイコンの中でいちばん鮮やかで、多く使われている色"""
    best, best_score = None, 0
    for count, (r, g, b, a) in icon.getcolors(icon.width * icon.height) or []:
        if a < 200:
            continue
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if 0.2 < l < 0.6 and s > 0.35 and count * s > best_score:
            best, best_score = (r, g, b), count * s
    return best


def hex_colour(s):
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


# ---------- 文字の折り返し ----------

def tokens(text):
    """英数字のかたまりは 1 語、それ以外（日本語）は 1 字ずつ"""
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-_./:@]*\s*|\s+|.", text)


def wrap(text, font, width):
    lines, cur = [], ""
    for t in tokens(text):
        if cur and font.getlength((cur + t).rstrip()) > width:
            # 禁則: 行頭禁止の字は前の行に入れる（ぶら下げ）。行末禁止の字は次の行へ送る
            if t[0] in NO_START:
                cur += t
                continue
            carry = ""
            while cur and cur[-1] in NO_END:
                carry, cur = cur[-1] + carry, cur[:-1]
            lines.append(cur.rstrip())
            cur = carry + t.lstrip()
        else:
            cur += t
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


def clamp(lines, font, width, n):
    """n 行に切り詰め、切ったら最後の行の末尾を「…」にする"""
    if len(lines) <= n:
        return lines
    last = lines[n - 1]
    while last and font.getlength(last + "…") > width:
        last = last[:-1]
    return lines[:n - 1] + [last.rstrip("、。,. ") + "…"]


def kind(c):
    if "぀" <= c <= "ゟ":
        return "hira"
    if "゠" <= c <= "ヿ":
        return "kata"
    if "一" <= c <= "鿿" or c in "々〆":
        return "kanji"
    return "latin" if c.isalnum() else "other"


def break_points(text):
    """タイトルを 2 行に分けてよい位置と、その良さ（大きいほど良い）"""
    points = []
    for i in range(1, len(text)):
        a, b = text[i - 1], text[i]
        if b in NO_START or a in NO_END:
            continue
        if a.isspace() or a in "・／/|｜—–:：" or b in "（(「『":
            points.append((i, 3))
        elif kind(a) == "hira" and kind(b) in ("kanji", "kata", "latin"):
            points.append((i, 2))  # 助詞の後ろ（「バンクーバーの／遊び場」）
    return points


def fit_title(text, width, sizes):
    """1 行に収まればそのまま。2 行にするときは、語の切れ目で分けられる最大の字の大きさを探す。
    どの大きさでも切れ目で分けられないときだけ、1 字単位で折り返す"""
    points = break_points(text)
    for size in sizes:
        font = ImageFont.truetype(FONT_BOLD, size)
        if font.getlength(text) <= width:
            return font, [text]
        ok = []
        for i, good in points:
            a, b = text[:i].rstrip(), text[i:].lstrip()
            la, lb = font.getlength(a), font.getlength(b)
            if la <= width and lb <= width:
                ok.append((good, -abs(la - lb), a, b))
        if ok:
            _, _, a, b = max(ok)
            return font, [a, b]
    for size in sizes:
        font = ImageFont.truetype(FONT_BOLD, size)
        lines = wrap(text, font, width)
        if len(lines) <= 2:
            return font, lines
    return font, clamp(lines, font, width, 2)


# ---------- 描く ----------

def cover(im, w, h):
    im = im.convert("RGB")
    scale = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def render(title, desc, domain, icon, accent, photo=None, credit=None):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    right = (SPLIT if photo else W) - PAD
    width = right - PAD
    if photo:
        im.paste(cover(photo, W - SPLIT, H), (SPLIT, 0))
    d.rectangle((0, 0, right + PAD, BAR - 1), fill=accent)

    # 左上: アイコンとドメイン
    y = PAD + BAR
    small = ImageFont.truetype(FONT_TEXT, 26)
    x = PAD
    if icon:
        im.paste(icon, (PAD, y + (ICON - icon.height) // 2), icon)
        x = PAD + ICON + 20
    d.text((x, y + ICON // 2), domain, font=small, fill=accent, anchor="lm")

    # タイトル（2 行に収まるまで小さくする）と説明（3 行まで）を、アイコンの下の余白の上下中央に置く
    sizes = range(68, 39, -4) if photo else range(84, 47, -4)
    tfont, tlines = fit_title(title, width, sizes)
    t_step = round(tfont.size * 1.3)
    dfont = ImageFont.truetype(FONT_TEXT, 30 if photo else 34)
    dlines = clamp(wrap(desc, dfont, width), dfont, width, 3) if desc else []
    d_step = round(dfont.size * 1.55)
    gap = 28 if dlines else 0
    block = t_step * len(tlines) + gap + d_step * len(dlines)
    top, bottom = y + ICON + 32, H - PAD
    y = max(top, top + (bottom - top - block) // 2 - 16)
    for line in tlines:
        d.text((PAD, y), line, font=tfont, fill=INK)
        y += t_step
    y += gap
    for line in dlines:
        d.text((PAD, y), line, font=dfont, fill=GREY)
        y += d_step
    if y > H - PAD // 2:
        print("  注意: 文字が下にはみ出しています。title か description を短く上書きしてください")

    if photo and credit:
        cw = d.textlength(credit, font=ImageFont.truetype(FONT_TEXT, 22))
        d.rectangle((W - cw - 32, H - 46, W, H), fill="black")
        d.text((W - cw - 16, H - 23), credit, font=ImageFont.truetype(FONT_TEXT, 22), fill="white", anchor="lm")
    return im


def make(page, defaults, base):
    page = {**defaults, **page}
    head, page_url, page_dir = read_source(page, base)
    m = head.meta
    title = page.get("title") or m.get("og:site_name") or m.get("og:title") or (head.title or "").strip()
    desc = page.get("description") or m.get("og:description") or m.get("description")
    domain = page.get("domain") or (urllib.parse.urlparse(page_url).netloc if page_url else "")
    icon_ref = page.get("icon") or pick_icon(head)
    try:
        icon = load_icon(load_bytes(icon_ref, page_url, page_dir, base), ICON)
    except Exception as e:
        print(f"  注意: アイコンを読めません（{icon_ref}: {e}）。アイコン無しで作ります")
        icon = None
    accent = page.get("accent") or m.get("theme-color")
    accent = hex_colour(accent) if accent else (icon and vivid_colour(icon)) or (47, 84, 150)
    photo = Image.open(io.BytesIO(load_bytes(page["image"], page_url, page_dir, base))) if page.get("image") else None

    out = (base / page["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    render(title, desc, domain, icon, accent, photo, page.get("credit")).save(
        out, quality=85, optimize=True, progressive=True)
    kb = out.stat().st_size // 1024
    print(f"{out}  {W}x{H}  {kb} KB  (title: {title} / icon: {icon_ref} / lang: {head.lang})")
    if kb > 300:
        print("  注意: 300 KB を超えています。共有先によっては画像が出ません")
    return out, title, head.lang


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("config", nargs="?", help="設定ファイル（JSON）")
    ap.add_argument("--url")
    ap.add_argument("--html")
    ap.add_argument("--out")
    ap.add_argument("--image")
    a = ap.parse_args()
    if a.config:
        path = Path(a.config).resolve()
        cfg = json.loads(path.read_text("utf-8"))
        pages, base = cfg.pop("pages"), path.parent
        defaults = cfg
    elif (a.url or a.html) and a.out:
        pages = [{k: v for k, v in {"url": a.url, "html": a.html, "out": a.out, "image": a.image}.items() if v}]
        base, defaults = Path.cwd(), {}
    else:
        ap.error("設定ファイルか、--url / --html と --out を指定してください")
    for p in pages:
        make(p, defaults, base)


if __name__ == "__main__":
    sys.exit(main())
