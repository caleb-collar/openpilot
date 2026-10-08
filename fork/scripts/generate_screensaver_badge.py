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


def generate_badge_png_bytes(version_str: str | None = None) -> bytes:
  """Generate PNG bytes directly for programmatic runtime use."""
  text = f"GaryPilot {version_str}".strip() if version_str else "GaryPilot"
  img = render_chrome_badge(text, font_size=46)
  buf = io.BytesIO()
  img.save(buf, format="PNG", optimize=True)
  return buf.getvalue()


def generate_badge_base64(version_str: str | None = None) -> str:
  """Generate base64 encoded PNG of the badge."""
  return base64.b64encode(generate_badge_png_bytes(version_str)).decode("utf-8")


def create_pixel_vehicle() -> Image.Image:
  """Create authentic 76x42 pixel art vehicle rear view."""
  W, H = 76, 42
  img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
  d = ImageDraw.Draw(img)

  BODY = (220, 226, 236, 255)
  BODY_LIGHT = (250, 253, 255, 255)
  BODY_SHADOW = (145, 155, 172, 255)
  BODY_DARK = (85, 95, 112, 255)
  ROOF = (18, 22, 30, 255)
  PILLAR = (30, 36, 46, 255)
  GLASS = (12, 16, 26, 255)
  SUNSET_1 = (255, 100, 40, 200)
  SUNSET_2 = (255, 160, 60, 170)
  SUNSET_3 = (255, 210, 90, 140)
  BUMPER = (24, 26, 34, 255)
  BUMPER_ACCENT = (48, 54, 66, 255)
  TIRE = (10, 12, 16, 255)
  TIRE_TREAD = (30, 34, 44, 255)
  RED_HOT = (255, 0, 35, 255)
  RED_CORE = (255, 220, 230, 255)
  RED_GLOW = (255, 0, 50, 120)
  HOOK = (245, 180, 35, 255)
  PLATE = (0, 240, 255, 255)
  PLATE_TEXT = (10, 20, 40, 255)
  MIRROR = (190, 200, 215, 255)

  # 1. Tires
  d.rectangle([4, 26, 14, 40], fill=TIRE)
  d.rectangle([5, 27, 8, 39], fill=TIRE_TREAD)
  d.rectangle([61, 26, 71, 40], fill=TIRE)
  d.rectangle([67, 27, 70, 39], fill=TIRE_TREAD)

  # 2. Lower Body
  d.rectangle([8, 21, 67, 33], fill=BODY)
  d.rectangle([6, 23, 8, 32], fill=BODY_SHADOW)
  d.rectangle([67, 23, 69, 32], fill=BODY_SHADOW)
  d.line([(9, 31), (66, 31)], fill=BODY_SHADOW)
  d.line([(9, 32), (66, 32)], fill=BODY_DARK)

  # 3. Bumper & Skidplate
  d.rectangle([12, 33, 63, 38], fill=BUMPER)
  d.rectangle([20, 36, 55, 39], fill=BUMPER_ACCENT)
  d.rectangle([23, 35, 26, 37], fill=HOOK)
  d.rectangle([49, 35, 52, 37], fill=HOOK)
  d.rectangle([32, 33, 43, 37], fill=PLATE)
  d.point([(34, 35), (36, 35), (38, 35), (40, 35)], fill=PLATE_TEXT)

  # 4. Tailgate top lip
  d.rectangle([10, 17, 65, 19], fill=BODY)
  d.line([(10, 17), (65, 17)], fill=BODY_LIGHT)

  # 5. Greenhouse (Cab & Windows)
  for y in range(4, 17):
    f = (y - 4) / 13.0
    x1 = int(22 - f * 4)
    x2 = int(53 + f * 4)
    d.line([(x1, y), (x2, y)], fill=PILLAR)

  d.rectangle([23, 3, 52, 5], fill=ROOF)
  d.line([(24, 3), (51, 3)], fill=BODY_DARK)
  d.line([(35, 4), (40, 4)], fill=RED_HOT)
  d.line([(36, 4), (39, 4)], fill=RED_CORE)

  for y in range(6, 16):
    f = (y - 6) / 10.0
    x1 = int(25 - f * 4)
    x2 = int(50 + f * 4)
    d.line([(x1, y), (x2, y)], fill=GLASS)

  d.line([(27, 13), (48, 13)], fill=SUNSET_1)
  d.line([(28, 11), (47, 11)], fill=SUNSET_2)
  d.line([(29, 9), (46, 9)], fill=SUNSET_3)

  d.rectangle([29, 10, 33, 13], fill=(16, 20, 30, 255))
  d.rectangle([42, 10, 46, 13], fill=(16, 20, 30, 255))

  d.rectangle([12, 12, 15, 14], fill=MIRROR)
  d.rectangle([60, 12, 63, 14], fill=MIRROR)
  d.point([(12, 13), (63, 13)], fill=ROOF)

  # 6. Coast-to-Coast Red Lightbar
  d.line([(10, 18), (65, 18)], fill=RED_GLOW)
  d.line([(10, 22), (65, 22)], fill=RED_GLOW)
  d.line([(10, 19), (65, 19)], fill=RED_HOT)
  d.line([(10, 20), (65, 20)], fill=RED_HOT)
  d.line([(13, 19), (62, 19)], fill=RED_CORE)
  d.rectangle([9, 18, 12, 21], fill=RED_HOT)
  d.point([(10, 19), (11, 19)], fill=RED_CORE)
  d.rectangle([63, 18, 66, 21], fill=RED_HOT)
  d.point([(64, 19), (65, 19)], fill=RED_CORE)

  for x in [27, 31, 35, 40, 44, 48]:
    d.point([(x, 26)], fill=BODY_SHADOW)

  return img


def generate_vehicle_png_bytes() -> bytes:
  """Generate PNG bytes of the pixel art vehicle sprite."""
  img = create_pixel_vehicle()
  buf = io.BytesIO()
  img.save(buf, format="PNG", optimize=True)
  return buf.getvalue()


def generate_vehicle_base64() -> str:
  """Generate base64 encoded PNG of the pixel art vehicle sprite."""
  return base64.b64encode(generate_vehicle_png_bytes()).decode("utf-8")


def update_screen_saver(gp_b64: str, veh_b64: str) -> bool:
  with open(SCREEN_SAVER_PY, encoding="utf-8") as f:
    lines = f.readlines()

  changed = False
  new_lines = []
  for line in lines:
    if line.startswith("GARYPILOT_LOGO_B64 = "):
      new_line = f'GARYPILOT_LOGO_B64 = "{gp_b64}"  # noqa: E501\n'
      if line != new_line:
        changed = True
      new_lines.append(new_line)
    elif line.startswith("VEHICLE_SPRITE_B64 = "):
      new_line = f'VEHICLE_SPRITE_B64 = "{veh_b64}"  # noqa: E501\n'
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
  parser = argparse.ArgumentParser(description="Generate GaryPilot Chromed Badge and Pixel Art Vehicle")
  parser.add_argument("--version", type=str, default=None, help="Explicit version string or None for title only")
  parser.add_argument("--check", action="store_true", help="Check if current code matches generated assets without modifying")
  args = parser.parse_args()

  gp_b64 = generate_badge_base64(args.version)
  veh_b64 = generate_vehicle_base64()

  if args.check:
    with open(SCREEN_SAVER_PY, encoding="utf-8") as f:
      content = f.read()
    gp_ok = f'GARYPILOT_LOGO_B64 = "{gp_b64}"' in content
    veh_ok = f'VEHICLE_SPRITE_B64 = "{veh_b64}"' in content
    if gp_ok and veh_ok:
      print("[✓] Screensaver assets in screen_saver.py are up to date.")
      sys.exit(0)
    else:
      print("[✗] Screensaver assets in screen_saver.py are OUT OF DATE.")
      if not gp_ok:
        print("  - GARYPILOT_LOGO_B64 mismatch")
      if not veh_ok:
        print("  - VEHICLE_SPRITE_B64 mismatch")
      sys.exit(1)

  changed = update_screen_saver(gp_b64, veh_b64)
  if changed:
    print("[✓] Successfully generated and updated GaryPilot badge and vehicle sprite in screen_saver.py")
  else:
    print("[✓] Screensaver assets in screen_saver.py are already up to date")


if __name__ == "__main__":
  main()
