# og-image

サイトの共有用画像（OGP、1200×630 JPEG）を、どのサイトでも同じ型で作る道具。

材料（アイコン・タイトル・説明）はサイト自身の HTML の head から読みます。
公開中の URL か、ビルド済みの HTML ファイルを渡します。
変えたいものだけ、各サイトのリポジトリに置く設定ファイル `og-image.json` で上書きします。

## 必要なもの

- macOS（字体にヒラギノ角ゴシックを使う）
- Python 3.9 以上と Pillow（`pip3 install Pillow`）
- SVG のアイコンを使うなら librsvg（`brew install librsvg`）

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

## 運用

- 道具はこのリポジトリにだけ置く。各サイトには `og-image.json` とできた画像だけをコミットする
- 道具を直したら、各サイトで再実行して画像を作り直す

## ライセンス

MIT
