#!/usr/bin/env bash
# Render share-card-post.svg (1600 x 900) to share-card.png with macOS tools only:
#   render_share_png.sh <charts dir>
# Quick Look renders square thumbnails, so the card is centred in a 1600 x 1600 canvas and cropped with sips.
set -euo pipefail
dir="${1:?usage: render_share_png.sh <charts dir>}"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python3 - "$dir/share-card-post.svg" "$tmp/card.svg" <<'EOF'
import sys
inner = open(sys.argv[1], encoding="utf-8").read().split("\n", 1)[1].rsplit("</svg>", 1)[0]
open(sys.argv[2], "w", encoding="utf-8").write(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1600" width="1600" height="1600" '
    'font-family="-apple-system, Helvetica, Arial, sans-serif"><rect width="1600" height="1600" fill="#0d1117"/>'
    '<g transform="translate(0,350)">%s</g></svg>' % inner)
EOF
qlmanage -t -s 1600 -o "$tmp" "$tmp/card.svg" >/dev/null 2>&1
sips -c 900 1600 "$tmp/card.svg.png" --out "$dir/share-card.png" >/dev/null
sips -g pixelWidth -g pixelHeight "$dir/share-card.png" | tail -2
