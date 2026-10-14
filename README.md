# og-image

サイトの共有用画像（OGP、1200×630 JPEG）を、どのサイトでも同じ型で作る道具。

材料（アイコン・タイトル・説明）はサイト自身の HTML の head から読みます。
公開中の URL か、ビルド済みの HTML ファイルを渡します。
変えたいものだけ、各サイトのリポジトリに置く設定ファイル `og-image.json` で上書きします。

## 必要なもの

- macOS（字体にヒラギノ角ゴシックを使う）
- Python 3.9 以上と Pillow（`pip3 install Pillow`）
- SVG のアイコンを使うなら librsvg（`brew install librsvg`）
- アイコンも作るなら fontTools（`pip3 install fonttools`）と Noto Sans JP（`~/Library/Fonts/NotoSansJP[wght].ttf`）

## 使い方

```
python3 og_image.py og-image.json
python3 og_image.py --url https://browser.ldas.jp/ --out og-ja.jpg
```

設定ファイルの例（パスは設定ファイルからの相対）:

```json
{
  "accent": "#0b5cad",
  "pages": [
    {"url": "https://browser.ldas.jp/",    "out": "public/og-ja.jpg"},
    {"url": "https://browser.ldas.jp/en/", "out": "public/og-en.jpg",
     "image": "photos/hero.jpg", "credit": "Photo: ..."}
  ]
}
```

ページごとの項目: `url` | `html`, `out`, `title`, `description`, `icon`, `image`, `credit`, `accent`, `domain`

## サイトのアイコン（site_icon.py）

アイコンの無いサイトには、色の地に白い字を置いたアイコンを作ります。

- 字は 1 字が基本。2 字までは作れるが、ブラウザのタブ（16px）では潰れる
- 地の色はそのサイトの強調色。角の丸みは一辺の 22%
- 字は線の形にして SVG に埋め込む（見る人の書体に左右されない）
- 作るもの: `icon.svg`、`apple-touch-icon.png`（180px、角を丸めない）、`favicon.ico`（16/32/48px）

```
python3 site_icon.py --text R --bg "#c8102e" --out public
```

`og-image.json` に書けば、共有画像を作るときに一緒に作り、共有画像の左上にも使います。

```json
{"site_icon": {"text": "R", "bg": "#c8102e", "out": "public"}, "pages": [...]}
```

head に書くタグ:

```html
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
```

## 運用

- 道具はこのリポジトリにだけ置く。各サイトには `og-image.json` とできた画像だけをコミットする
- 道具を直したら、各サイトで再実行して画像を作り直す

## ライセンス

MIT
