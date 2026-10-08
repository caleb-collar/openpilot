#!/usr/bin/env python3
"""
Screensaver Preview Tool for Comma 3X and Comma 4.

Supports:
- Comma 3 / 3X: 2160 x 1080 (6.0-inch OLED, 18:9 aspect ratio)
- Comma 4: 536 x 240 (1.9-inch OLED, 20:9 aspect ratio, 300 PPI)

Usage:
  ./preview_screensaver.py                     # interactive window (Comma 4 default)
  ./preview_screensaver.py --device comma3x    # interactive window (Comma 3X)
  ./preview_screensaver.py --device comma4     # interactive window (Comma 4)
  ./preview_screensaver.py --screenshot comma4.png  # headless screenshot export
  ./preview_screensaver.py --all --screenshot  # headless screenshot for both devices

Interactive controls:
  [3]: Switch to Comma 3X resolution (2160x1080)
  [4]: Switch to Comma 4 resolution (536x240)
  [S]: Save screenshot to disk
  [Q] or [ESC]: Quit
"""
from __future__ import annotations

import argparse
import os
import sys
import time

try:
  import pyray as rl
except ImportError:
  print("Error: pyray (raylib) is not installed. Run with .venv/bin/python3 preview_screensaver.py", file=sys.stderr)
  sys.exit(1)

from openpilot.system.ui.sunnypilot.widgets.screen_saver import (
  draw_screensaver,
  ensure_screensaver_assets,
)

RESOLUTIONS = {
  "comma3x": (2160, 1080, "Comma 3 / 3X (2160x1080)"),
  "comma4": (536, 240, "Comma 4 (536x240)"),
}


class ScreensaverRenderer:
  def __init__(self, width: int, height: int, is_comma4: bool):
    self.width = width
    self.height = height
    self.is_comma4 = is_comma4
    self.grid_offset = 0.0
    self.grid_speed = 40.0 if is_comma4 else 80.0
    self.spacing = 30.0 if is_comma4 else 50.0

  def update(self, dt: float):
    self.grid_offset += self.grid_speed * dt
    if self.grid_offset > self.spacing:
      self.grid_offset -= self.spacing

  def draw(
    self,
    texture,
    tex_gp=None,
    tex_vehicle=None,
    anim_time: float | None = None,
    grid_offset: float | None = None,
  ):
    t = anim_time if anim_time is not None else time.monotonic()
    offset = grid_offset if grid_offset is not None else self.grid_offset
    draw_screensaver(
      self.width,
      self.height,
      self.is_comma4,
      offset,
      texture,
      tex_gp,
      tex_vehicle,
      t,
    )


def capture_screenshot(device_key: str, out_path: str, anim_time: float = 0.0):
  """Headless render and export to PNG with 100% determinism."""
  w, h, title = RESOLUTIONS[device_key]
  logo_file, gp_file, vehicle_file = ensure_screensaver_assets()

  rl.set_config_flags(rl.ConfigFlags.FLAG_WINDOW_HIDDEN)
  rl.init_window(w, h, title.encode("utf-8"))
  texture = rl.load_texture(logo_file.encode("utf-8"))
  tex_gp = rl.load_texture(gp_file.encode("utf-8"))
  tex_vehicle = rl.load_texture(vehicle_file.encode("utf-8"))

  renderer = ScreensaverRenderer(w, h, is_comma4=(device_key == "comma4"))

  rl.begin_drawing()
  renderer.draw(texture, tex_gp, tex_vehicle, anim_time=anim_time, grid_offset=0.0)
  rl.end_drawing()

  img = rl.load_image_from_screen()
  rl.export_image(img, out_path.encode("utf-8"))
  rl.unload_image(img)
  rl.unload_texture(texture)
  rl.unload_texture(tex_gp)
  rl.unload_texture(tex_vehicle)
  rl.close_window()
  print(f"[✓] Screenshot saved to: {out_path} ({w}x{h})")


def capture_gif(device_key: str, out_path: str, duration: float = 4.0, fps: int = 20):
  """Render a full seamless animation cycle and export as an animated GIF."""
  try:
    from PIL import Image
  except ImportError:
    print("Error: Pillow is required to export animated GIFs.", file=sys.stderr)
    return

  w, h, title = RESOLUTIONS[device_key]
  logo_file, gp_file, vehicle_file = ensure_screensaver_assets()

  rl.set_config_flags(rl.ConfigFlags.FLAG_WINDOW_HIDDEN)
  rl.init_window(w, h, title.encode("utf-8"))
  texture = rl.load_texture(logo_file.encode("utf-8"))
  tex_gp = rl.load_texture(gp_file.encode("utf-8"))
  tex_vehicle = rl.load_texture(vehicle_file.encode("utf-8"))

  renderer = ScreensaverRenderer(w, h, is_comma4=(device_key == "comma4"))

  frames = []
  total_frames = int(duration * fps)
  temp_frame_path = ".preview_frame_tmp.png"

  for i in range(total_frames):
    t = i / fps
    grid_offset = (renderer.grid_speed * t) % renderer.spacing
    rl.begin_drawing()
    renderer.draw(texture, tex_gp, tex_vehicle, anim_time=t, grid_offset=grid_offset)
    rl.end_drawing()

    img = rl.load_image_from_screen()
    rl.export_image(img, temp_frame_path.encode("utf-8"))
    rl.unload_image(img)
    frames.append(Image.open(temp_frame_path).copy())

  rl.unload_texture(texture)
  rl.unload_texture(tex_gp)
  rl.unload_texture(tex_vehicle)
  rl.close_window()

  if os.path.exists(temp_frame_path):
    os.remove(temp_frame_path)

  frames_p = [f.convert("P", palette=Image.ADAPTIVE) for f in frames]
  frames_p[0].save(
    out_path,
    save_all=True,
    append_images=frames_p[1:],
    duration=int(1000 / fps),
    loop=0,
    optimize=True,
  )
  print(f"[✓] Animated GIF saved to: {out_path} ({len(frames)} frames, {w}x{h})")


def run_interactive(initial_device: str):
  """Run interactive Raylib preview window."""
  device_key = initial_device
  logo_file, gp_file, vehicle_file = ensure_screensaver_assets()

  while True:
    w, h, title = RESOLUTIONS[device_key]
    is_comma4 = (device_key == "comma4")
    display_title = f"{title} - [3]: Comma 3X | [4]: Comma 4 | [S]: Screenshot | [Q]: Quit"

    rl.init_window(w, h, display_title.encode("utf-8"))
    rl.set_target_fps(60)
    texture = rl.load_texture(logo_file.encode("utf-8"))
    tex_gp = rl.load_texture(gp_file.encode("utf-8"))
    tex_vehicle = rl.load_texture(vehicle_file.encode("utf-8"))
    renderer = ScreensaverRenderer(w, h, is_comma4)

    switch_to = None

    while not rl.window_should_close():
      dt = rl.get_frame_time()
      renderer.update(dt)

      if rl.is_key_pressed(rl.KeyboardKey.KEY_THREE) and device_key != "comma3x":
        switch_to = "comma3x"
        break
      elif rl.is_key_pressed(rl.KeyboardKey.KEY_FOUR) and device_key != "comma4":
        switch_to = "comma4"
        break
      elif rl.is_key_pressed(rl.KeyboardKey.KEY_S):
        ts = int(time.monotonic())
        shot_name = f"screensaver_{device_key}_{ts}.png"
        rl.take_screenshot(shot_name.encode("utf-8"))
        print(f"[✓] Screenshot saved: {shot_name}")
      elif rl.is_key_pressed(rl.KeyboardKey.KEY_Q):
        rl.unload_texture(texture)
        rl.unload_texture(tex_gp)
        rl.unload_texture(tex_vehicle)
        rl.close_window()
        return

      rl.begin_drawing()
      renderer.draw(texture, tex_gp, tex_vehicle)
      rl.end_drawing()

    rl.unload_texture(texture)
    rl.unload_texture(tex_gp)
    rl.unload_texture(tex_vehicle)
    rl.close_window()

    if switch_to:
      device_key = switch_to
    else:
      break


def main():
  parser = argparse.ArgumentParser(description="Screensaver Preview Tool for Comma 3X and Comma 4")
  parser.add_argument(
    "--device",
    "-d",
    choices=["comma3x", "comma4"],
    default="comma4",
    help="Device target resolution to preview (default: comma4)",
  )
  parser.add_argument(
    "--all",
    action="store_true",
    help="Preview / capture screenshots for all supported devices",
  )
  parser.add_argument(
    "--screenshot",
    nargs="?",
    const="auto",
    default=None,
    help="Capture screenshot headlessly and exit. Optional output file path.",
  )
  parser.add_argument(
    "--time",
    "-t",
    type=float,
    default=0.0,
    help="Animation timestamp in seconds for static screenshot capture (default: 0.0)",
  )
  parser.add_argument(
    "--gif",
    "-g",
    nargs="?",
    const="auto",
    default=None,
    help="Capture seamless animated GIF cycle and exit. Optional output file path.",
  )

  args = parser.parse_args()

  if args.gif:
    if args.all:
      capture_gif("comma3x", "preview_comma3x.gif")
      capture_gif("comma4", "preview_comma4.gif")
    else:
      out_gif = args.gif if args.gif != "auto" else f"preview_{args.device}.gif"
      capture_gif(args.device, out_gif)
    return

  if args.screenshot:
    if args.all:
      capture_screenshot("comma3x", "preview_comma3x.png", anim_time=args.time)
      capture_screenshot("comma4", "preview_comma4.png", anim_time=args.time)
    else:
      out_file = args.screenshot if args.screenshot != "auto" else f"preview_{args.device}.png"
      capture_screenshot(args.device, out_file, anim_time=args.time)
    return

  if args.all:
    print("Interactive mode will start with Comma 4. Press [3] to view Comma 3X.")

  run_interactive(args.device)


if __name__ == "__main__":
  main()
