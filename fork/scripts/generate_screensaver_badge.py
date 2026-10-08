#!/usr/bin/env python3
"""
Programmatic generator for the GaryPilot chromed screensaver badge.

Renders retro 1980s synthwave chrome typography using Audiowide font:
- Sky reflection: Deep metallic blue -> electric cyan -> pure white horizon flash line
- Ground reflection: Deep violet -> neon magenta / hot pink (matches perspective grid)
- Framing: 1px crisp black outline + 2px neon magenta rim glow

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
  from PIL import Image, ImageDraw, ImageFont
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
    if tag.startswith("r1-v"):
      return tag.replace("r1-", "")  # e.g. v0.1.0
    if tag.startswith("v"):
      return tag
  except Exception:
    pass

  # 2. Try FORK_CHANGELOG.md
  changelog_path = os.path.join(REPO_ROOT, "FORK_CHANGELOG.md")
  if os.path.exists(changelog_path):
    with open(changelog_path, "r", encoding="utf-8") as f:
      content = f.read()
    match = re.search(r"##\s*\[(\d+\.\d+\.\d+)\]", content)
    if match:
      return f"v{match.group(1)}"

  return "v0.1.0"


def render_chrome_badge(text: str, font_size: int = 22) -> Image.Image:
  """Programmatically render the chromed text with gradients, outline, and glow."""
  font = ImageFont.truetype(FONT_PATH, font_size)
  bbox = font.getbbox(text)
  w = bbox[2] - bbox[0] + 8
  h = bbox[3] - bbox[1] + 8

  mask = Image.new("L", (w, h), 0)
  d = ImageDraw.Draw(mask)
  d.text((4 - bbox[0], 4 - bbox[1]), text, font=font, fill=255)

  mask_pix = mask.point(lambda p: 255 if p > 90 else 0)
  real_bbox = mask_pix.getbbox()
  if not real_bbox:
    raise ValueError(f"Empty text render for '{text}'")

  top, bottom = real_bbox[1], real_bbox[3]
  mid = top + int((bottom - top) * 0.48)

  grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
  for y in range(h):
    if y < mid:
      t = min(1.0, max(0.0, (y - top) / float(max(1, mid - top))))
      if t < 0.65:
        st = t / 0.65
        r = int(15 + st * 25)
        g = int(35 + st * 155)
        b = int(140 + st * 115)
      else:
        st = (t - 0.65) / 0.35
        r = int(40 + st * 215)
        g = int(190 + st * 65)
        b = 255
    else:
      t = min(1.0, max(0.0, (y - mid) / float(max(1, bottom - mid))))
      # Neon Magenta bottom gradient (Outrun grid reflection)
      if t < 0.4:
        st = t / 0.4
        r = int(70 + st * 110)
        g = int(10 + st * 10)
        b = int(120 + st * 30)
      else:
        st = (t - 0.4) / 0.6
        r = int(180 + st * 75)
        g = int(20 + st * 100)
        b = int(150 + st * 50)

    for x in range(w):
      grad.putpixel((x, y), (r, g, b, 255))

  chrome_text = Image.new("RGBA", (w, h), (0, 0, 0, 0))
  chrome_text.paste(grad, (0, 0), mask_pix)

  final_img = Image.new("RGBA", (w + 6, h + 6), (0, 0, 0, 0))

  # 1. Outer Neon Magenta Rim Glow (matching Outrun grid)
  for dy in range(-2, 3):
    for dx in range(-2, 3):
      if abs(dx) == 2 or abs(dy) == 2:
        final_img.paste(Image.new("RGBA", (w, h), (255, 0, 128, 120)), (3 + dx, 3 + dy), mask_pix)

  # 2. Dark Outline
  for dy in [-1, 0, 1]:
    for dx in [-1, 0, 1]:
      if dx == 0 and dy == 0:
        continue
      final_img.paste(Image.new("RGBA", (w, h), (10, 2, 25, 255)), (3 + dx, 3 + dy), mask_pix)

  # 3. Chrome Body
  final_img.paste(chrome_text, (3, 3), chrome_text)

  # 4. White Horizon Flash Line
  for x in range(w):
    if mask_pix.getpixel((x, mid - 1)) > 0:
      final_img.putpixel((3 + x, 3 + mid - 1), (255, 255, 255, 255))
      if mask_pix.getpixel((x, mid - 2)) > 0:
        final_img.putpixel((3 + x, 3 + mid - 2), (235, 255, 255, 255))

  return final_img


def generate_badge_base64(version_str: str) -> str:
  text = f"GaryPilot {version_str}"
  img = render_chrome_badge(text, font_size=22)
  buf = io.BytesIO()
  img.save(buf, format="PNG", optimize=True)
  return base64.b64encode(buf.getvalue()).decode("utf-8")


def update_screen_saver(b64_string: str) -> bool:
  with open(SCREEN_SAVER_PY, "r", encoding="utf-8") as f:
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
    with open(SCREEN_SAVER_PY, "r", encoding="utf-8") as f:
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
