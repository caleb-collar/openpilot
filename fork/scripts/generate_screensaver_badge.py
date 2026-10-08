#!/usr/bin/env python3
"""
Programmatic generator for the GaryPilot chromed screensaver badge.

Renders large, high-legibility retro 1980s chrome/white/silver typography using Audiowide font:
- Pure Anti-Aliasing: Clean, undistorted vector letterforms with open counters and natural geometry
- Ethereal Soft Glow: Multi-tier luminous white & cool silver halo replacing harsh borders
- Polished Chrome Luster: Pure white specular highlights flowing into liquid platinum and metallic silver
- Ambient Grid Occlusion: Soft dark ambient shadow behind the glow to smoothly dim the perspective grid

Usage:
  ./fork/scripts/generate_screensaver_badge.py                  # auto-detects version from git/changelog
  ./fork/scripts/generate_screensaver_badge.py --version v0.1.0 # specifies version explicitly
  ./fork/scripts/generate_screensaver_badge.py --check          # verify embedded badge is up to date (for CI)
"""
from __future__ import annotations

import argparse
import base64
import io
import os
import re
import subprocess
import sys

try:
  from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
  print("Error: Pillow is required to run the badge generator. Install with: pip install Pillow", file=sys.stderr)
  sys.exit(1)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONT_PATH = os.path.join(REPO_ROOT, "openpilot", "selfdrive", "assets", "fonts", "Audiowide-Regular.ttf")
SCREEN_SAVER_PY = os.path.join(REPO_ROOT, "openpilot", "system/ui/sunnypilot/widgets/screen_saver.py")


def detect_version() -> str:
  """Detect the fork version from git tag or FORK_CHANGELOG.md."""
  # 1. Try git describe --tags
  try:
    tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL).decode().strip()
    tag = re.sub(r"^r1[a-z]*-", "", tag)  # e.g. r1-v0.1.0 -> v0.1.0, r1t-v0.1.0 -> v0.1.0
    if tag.startswith("v"):
      return tag
    return f"v{tag}"
  except Exception:
    pass

  # 2. Try FORK_CHANGELOG.md
  changelog_path = os.path.join(REPO_ROOT, "FORK_CHANGELOG.md")
  if os.path.exists(changelog_path):
    with open(changelog_path, encoding="utf-8") as f:
      content = f.read()
    match = re.search(r"##\s*\[(\d+\.\d+\.\d+)\]", content)
    if match:
      return f"v{match.group(1)}"

  return "v0.1.0"


def render_chrome_badge(text: str, font_size: int = 46) -> Image.Image:
  """Programmatically render clean anti-aliased chrome typography with an ethereal soft glow."""
  # Supersample 2x for pristine edge anti-aliasing and smooth glow falloff
  s = 2
  eff_font_size = font_size * s
  font = ImageFont.truetype(FONT_PATH, eff_font_size)
  bbox = font.getbbox(text)
  pad = 20 * s
  w = bbox[2] - bbox[0] + pad * 2
  h = bbox[3] - bbox[1] + pad * 2

  mask = Image.new("L", (w, h), 0)
  d = ImageDraw.Draw(mask)
  d.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=255)

  real_bbox = mask.getbbox()
  if not real_bbox:
    raise ValueError(f"Empty text render for '{text}'")

  top, bottom = real_bbox[1], real_bbox[3]
  glyph_h = max(1, bottom - top)
  mid = top + int(glyph_h * 0.46)

  # Chrome gradient: elegant silver/white
  grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
  for y in range(h):
    if y < mid:
      st = (y - top) / float(max(1, mid - top))
      if st < 0.3:
        r = g = b = 255
      elif st < 0.8:
        sst = (st - 0.3) / 0.5
        r = int(255 - sst * 50)
        g = int(255 - sst * 45)
        b = int(255 - sst * 35)
      else:
        sst = (st - 0.8) / 0.2
        r = int(205 + sst * 50)
        g = int(210 + sst * 45)
        b = int(220 + sst * 35)
    else:
      st = (y - mid) / float(max(1, bottom - mid))
      if st < 0.25:
        sst = st / 0.25
        r = int(120 + sst * 30)
        g = int(125 + sst * 30)
        b = int(140 + sst * 30)
      elif st < 0.75:
        sst = (st - 0.25) / 0.50
        r = int(150 + sst * 85)
        g = int(155 + sst * 85)
        b = int(170 + sst * 75)
      else:
        sst = (st - 0.75) / 0.25
        r = int(235 + sst * 20)
        g = int(240 + sst * 15)
        b = int(245 + sst * 10)

    for x in range(w):
      grad.putpixel((x, y), (r, g, b, 255))

  chrome_body = Image.new("RGBA", (w, h), (0, 0, 0, 0))
  chrome_body.paste(grad, (0, 0), mask)

  final_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

  # 1. Ambient dark drop shadow behind the glow to smoothly dim the perspective grid
  shadow_mask = mask.filter(ImageFilter.GaussianBlur(radius=8 * s))
  shadow_layer = Image.new("RGBA", (w, h), (10, 2, 25, 200))
  final_img.paste(shadow_layer, (0, 0), shadow_mask)

  # 2. Multi-tier Soft Luminous Glow (no harsh borders!)
  # Broad soft atmospheric halo
  halo_mask = mask.filter(ImageFilter.GaussianBlur(radius=6 * s))
  halo_layer = Image.new("RGBA", (w, h), (225, 240, 255, 120))
  final_img.paste(halo_layer, (0, 0), halo_mask)

  # Tight intense inner glow right at the edges of the glyphs
  tight_mask = mask.filter(ImageFilter.GaussianBlur(radius=2 * s))
  tight_layer = Image.new("RGBA", (w, h), (255, 255, 255, 180))
  final_img.paste(tight_layer, (0, 0), tight_mask)

  # 3. Clean Chrome Body (Pristine anti-aliased typography)
  final_img.paste(chrome_body, (0, 0), mask)

  # Downsample with Lanczos for razor-clean smooth typography
  target_w = w // s
  target_h = h // s
  return final_img.resize((target_w, target_h), Image.Resampling.LANCZOS)


def generate_badge_png_bytes(version_str: str) -> bytes:
  """Generate PNG bytes directly for programmatic runtime use."""
  text = f"GaryPilot {version_str}"
  img = render_chrome_badge(text, font_size=46)
  buf = io.BytesIO()
  img.save(buf, format="PNG", optimize=True)
  return buf.getvalue()


def generate_badge_base64(version_str: str) -> str:
  """Generate base64 encoded PNG of the badge."""
  return base64.b64encode(generate_badge_png_bytes(version_str)).decode("utf-8")


def update_screen_saver(b64_string: str) -> bool:
  with open(SCREEN_SAVER_PY, encoding="utf-8") as f:
    lines = f.readlines()

  changed = False
  new_lines = []
  for line in lines:
    if line.startswith("GARYPILOT_LOGO_B64 = "):
      new_line = f'GARYPILOT_LOGO_B64 = "{b64_string}"  # noqa: E501\n'
      if line != new_line:
        changed = True
      new_lines.append(new_line)
    else:
      new_lines.append(line)

  if changed:
    with open(SCREEN_SAVER_PY, "w", encoding="utf-8") as f:
      f.writelines(new_lines)

  return changed


def main():
  parser = argparse.ArgumentParser(description="Generate GaryPilot Chromed Badge with Version")
  parser.add_argument("--version", type=str, default=None, help="Explicit version string (e.g. v0.1.0)")
  parser.add_argument("--check", action="store_true", help="Check if current code matches generated badge without modifying")
  args = parser.parse_args()

  version = args.version or detect_version()
  b64_str = generate_badge_base64(version)

  if args.check:
    with open(SCREEN_SAVER_PY, encoding="utf-8") as f:
      content = f.read()
    if f'GARYPILOT_LOGO_B64 = "{b64_str}"' in content:
      print(f"[✓] Badge in screen_saver.py matches version: {version}")
      sys.exit(0)
    else:
      print(f"[✗] Badge in screen_saver.py is OUT OF DATE for version: {version}")
      sys.exit(1)

  changed = update_screen_saver(b64_str)
  if changed:
    print(f"[✓] Successfully generated and updated GaryPilot badge for '{version}' in screen_saver.py")
  else:
    print(f"[✓] GaryPilot badge in screen_saver.py is already up to date for '{version}'")


if __name__ == "__main__":
  main()
