#!/bin/zsh

set -euo pipefail

CONTENT_ROOT="${1:-/Users/bigmac/.openclaw/workspace/content_factory}"
IMAGES_ROOT="$CONTENT_ROOT/images"

mkdir -p \
  "$IMAGES_ROOT/female_host" \
  "$IMAGES_ROOT/male_host" \
  "$IMAGES_ROOT/psych_host"

generate_gradient() {
  local output_path="$1"
  local color_a="$2"
  local color_b="$3"
  local color_c="$4"
  local x_expr="$5"
  local y_expr="$6"

  ffmpeg -y \
    -f lavfi -i "nullsrc=s=1080x1920,geq=r='lerp(lerp(${color_a%%,*},${color_b%%,*},${x_expr}),${color_c%%,*},${y_expr})':g='lerp(lerp(${color_a#*,},${color_b#*,},${x_expr}),${color_c#*,},${y_expr})':b='lerp(lerp(${color_a##*,},${color_b##*,},${x_expr}),${color_c##*,},${y_expr})'" \
    -frames:v 1 \
    "$output_path" \
    >/dev/null 2>&1
}

generate_gradient "$IMAGES_ROOT/female_host/warm_sunrise_01.png" "246,183,197" "255,165,117" "255,237,204" "X/W" "Y/H"
generate_gradient "$IMAGES_ROOT/female_host/warm_sunrise_02.png" "255,205,214" "255,145,108" "255,226,179" "(X+0.45*Y)/W" "Y/H"
generate_gradient "$IMAGES_ROOT/female_host/warm_sunrise_03.png" "255,191,210" "255,132,92" "255,243,214" "sqrt(((X-W*0.2)*(X-W*0.2))+((Y-H*0.1)*(Y-H*0.1)))/(sqrt((W*W)+(H*H)))" "Y/H"

generate_gradient "$IMAGES_ROOT/male_host/cool_modern_01.png" "17,42,78" "40,104,178" "6,15,28" "X/W" "Y/H"
generate_gradient "$IMAGES_ROOT/male_host/cool_modern_02.png" "28,58,102" "91,157,255" "9,20,38" "(X*0.65+Y*0.35)/W" "(Y*0.8)/H"
generate_gradient "$IMAGES_ROOT/male_host/cool_modern_03.png" "11,28,52" "64,125,214" "3,8,18" "sqrt(((X-W*0.8)*(X-W*0.8))+((Y-H*0.15)*(Y-H*0.15)))/(sqrt((W*W)+(H*H)))" "Y/H"

generate_gradient "$IMAGES_ROOT/psych_host/mystery_depth_01.png" "14,7,28" "87,39,140" "0,0,0" "X/W" "Y/H"
generate_gradient "$IMAGES_ROOT/psych_host/mystery_depth_02.png" "22,9,36" "118,56,169" "2,2,6" "(X+Y)/W" "sqrt(((X-W*0.5)*(X-W*0.5))+((Y-H*0.2)*(Y-H*0.2)))/(sqrt((W*W)+(H*H)))"
generate_gradient "$IMAGES_ROOT/psych_host/mystery_depth_03.png" "10,4,20" "73,26,120" "0,0,0" "sqrt(((X-W*0.5)*(X-W*0.5))+((Y-H*0.55)*(Y-H*0.55)))/(sqrt((W*W)+(H*H)))" "(Y*0.9)/H"
