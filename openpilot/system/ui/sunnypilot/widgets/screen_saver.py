"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from __future__ import annotations

import base64
import math
import os
import time
from typing import TYPE_CHECKING

import pyray as rl

from openpilot.common.hardware import HARDWARE
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import Widget

if TYPE_CHECKING:
  from openpilot.common.params import Params
else:
  try:
    from openpilot.common.params import Params
  except (ImportError, OSError):
    Params = None

R_LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAD/ElEQVR4nO2d226rMBBFm6P+/y/naB6QUJWQADOefZkl9Smxcb2XDLgDfTyfz5/Bl3/dAxh6GQHMGQHMGQHMGQHMGQHMGQHMGQHMGQHMGQHMGQHMGQHMGQHMGQHMGQHMGQHMGQHM+e0eQBPvyqAeS0cBgJsAn+rfts9tRHAR4Gzho40IDtcAd6pe5Stm1QXICFBaAmUBMoOTlUBVgIrAJCVQFKAyKDkJ1ARYEZCUBEoCrAxGRgIVAToCkZBAQYDOIOglYBcAIQCEMVyGWQCkiUcayylYBcia8MdP3n4/pQSMAmRM9N/gs0Sgk4BNgLsT/CnoDBGoJGASICP8iu++gkYCFgFWhn+nzR4KCRgE6Ag/o20ALwG6ACvDr6oThJYAWYCK8J+7n3fHfPWZrASoAlSFf+f4khIgCtAd/lEbOQnQBEAJ/6itlARIAqCFf9SHjAQoAqCGf9SXhAQIAqCHf9QnvQTdArCEf9Q3tQSdArCFf3QMWgm6BGAN/+hYlBJ0CMAe/tEx6SRYLYBK+EfHppJgpQBq4W9QS7BKANXwN2glWCEAYviv+qwIDF6CagFYwv/ms2+gk6BSALbwz3znCCoJqgRgDf/Kd19BI0GFAOzh32mzh0KCbAE6Czgr+kQbT5AqQaYAVeHf6TcjwDt9wBeadv81cAM1/Iy+oN9KiiAA4jLL3Oe5AQD/9/CrA6ueVNRxXQJhBRgaGQHMQRbg6pI57wk8QebbwlGu2INnUZ9Xgb3LQVkBKm6VqsvCv6Ui/DQyBYDZ3EjuE3Fcaatb9gqgtn+u8neNt1ScAlQkkA8/qLoGYJfAIvyg8iKQVQKb8IPquwA2CazCD1bcBrJIYBd+sGofAFGCTCjDD1ZuBKlKQBt+gLIT+C1oEqA/sPKR1QJUvZC5Q4Kq8Jf+Lh0rgIIEEuEHXacAZglkwg86rwEYJZAKP+i+CGSSQC78oFuAgEECyfADBAECZAlkww9QBAgQJZAOP0ASIECSQD78AE2AAEECi/ADRAGCTglswg+QHw0LECYeYQxloK4AG1UrwYq2G7DhB+gCBF0SyIcfMAgQrJbAIvyARYAgS4JPNYE24QdMAgRZE/sq6KyrYZrwg8yHQ1cRE5wVVvYtEFX4AdsKsIE40Yhj+girAAHShCON5RTMAgQIE48whsuwCxCgVQVToSBAgFIVTIeKAEF3VTAlSgIEXVXBtKgJEKyuCqZGUYBA8rWuFTDuBH7LFhjNg5odqK4Ae7KLQqVwECA4G+TjQhtKlE8Bf9kHCv0O/5U4CbDHLuh3uJwChjeMAOaMAOaMAOaMAOaMAOaMAOaMAOaMAOaMAOaMAOaMAOaMAOaMAOaMAOaMAMMwDLb8B6Eu4gGh6E+YAAAAAElFTkSuQmCC"  # noqa: E501

GARYPILOT_LOGO_B64 = "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"  # noqa: E501

R_LOGO_PATH = "/tmp/r_logo_screensaver.png"
GARYPILOT_LOGO_PATH = "/tmp/garypilot_screensaver_logo.png"


def ensure_screensaver_assets() -> tuple[str, str]:
  for path, b64_data in [(R_LOGO_PATH, R_LOGO_B64), (GARYPILOT_LOGO_PATH, GARYPILOT_LOGO_B64)]:
    data = base64.b64decode(b64_data)
    if not os.path.exists(path) or os.path.getsize(path) != len(data):
      with open(path, "wb") as f:
        f.write(data)
  return R_LOGO_PATH, GARYPILOT_LOGO_PATH


def draw_screensaver(
  w: int,
  h: int,
  is_mici: bool,
  grid_offset: float = 0.0,
  texture: rl.Texture | None = None,
  gp_texture: rl.Texture | None = None,
  anim_time: float = 0.0,
) -> None:
  # Outrun Colors
  bg_color = rl.Color(13, 2, 33, 255)
  grid_color = rl.Color(255, 0, 128, 255)
  horizon_color = rl.Color(0, 255, 255, 255)

  rl.clear_background(bg_color)

  horizon_y = h // 2
  center_x = w // 2

  # Draw Stars
  rl.set_random_seed(1234)
  num_stars = 80 if not is_mici else 40
  for _ in range(num_stars):
    sx = rl.get_random_value(0, w)
    sy = rl.get_random_value(0, horizon_y - 50)
    size = rl.get_random_value(1, 2)
    alpha = rl.get_random_value(100, 255)

    if rl.get_random_value(0, 5) == 0:
      alpha = int(127 + 127 * math.sin(anim_time * 5.0 + sx))

    rl.draw_circle(sx, sy, float(size), rl.Color(255, 255, 255, alpha))

    if rl.get_random_value(0, 15) == 0:
      rl.draw_line(sx - 6, sy, sx + 6, sy, rl.Color(255, 255, 255, alpha))
      rl.draw_line(sx, sy - 6, sx, sy + 6, rl.Color(255, 255, 255, alpha))

  if texture is not None:
    # Logo as the Sun
    tex_w = texture.width
    tex_h = texture.height
    scale = 8.5 if not is_mici else 4.5

    # Offset the sun up so it is not centered on the horizon
    sun_offset_y = int((tex_h * scale) * 0.25)
    sun_y = horizon_y - sun_offset_y

    dest = rl.Rectangle(
      float(center_x - (tex_w * scale) / 2),
      float(sun_y - (tex_h * scale) / 2),
      float(tex_w * scale),
      float(tex_h * scale),
    )
    source = rl.Rectangle(0.0, 0.0, float(tex_w), float(tex_h))

    # Add a glow behind the sun using transparent circles
    glow_radius = int((tex_w * scale) * 0.6)
    for r_idx in range(25):
      r = glow_radius * (1.0 - (r_idx / 25.0))
      g_alpha = int(100 * (r_idx / 25.0))
      rl.draw_circle(center_x, sun_y, r, rl.Color(255, 100, 0, g_alpha))

    # Tint it sunset orange/yellow
    rl.draw_texture_pro(texture, source, dest, rl.Vector2(0.0, 0.0), 0.0, rl.Color(255, 204, 0, 255))

    # Draw background-color horizontal slices through the bottom half of the logo
    sun_radius = (tex_h * scale) / 2
    current_y = 0.0
    solid_thickness = 25.0 if not is_mici else 12.0
    cut_thickness = 2.0 if not is_mici else 1.0

    while current_y < sun_radius:
      current_y += solid_thickness
      slice_y = sun_y + int(current_y)

      if slice_y > horizon_y:
        break

      cut_h = int(cut_thickness)
      if cut_h < 1:
        cut_h = 1

      if slice_y + cut_h > horizon_y:
        cut_h = int(horizon_y - slice_y)

      if cut_h > 0 and slice_y > sun_y:
        rl.draw_rectangle(int(center_x - (tex_w * scale) / 2), int(slice_y), int(tex_w * scale), cut_h, bg_color)

      current_y += cut_thickness

      # Modify thicknesses for the next iteration: solid bands get thinner, cutouts get thicker
      solid_thickness *= 0.85
      cut_thickness *= 1.4

    # Strictly occlude the sun and glow if they fall below the horizon line
    rl.draw_rectangle(0, int(horizon_y), w, h - int(horizon_y), bg_color)

  # Draw Mountains
  def draw_mountain_layer(seed, color, min_dx, max_dx, min_h, max_h, y_offset, line_thick):
    rl.set_random_seed(seed)
    curr_x = -100
    pts = []
    is_peak = True
    while curr_x < w + 200:
      if is_peak:
        dx = rl.get_random_value(min_dx, max_dx)
        curr_x += dx
        dist_from_center = abs(curr_x - center_x)
        # Scale height so they are taller at edges, shorter in middle
        height_scale = 0.4 + 0.6 * (dist_from_center / (w / 2))
        height = rl.get_random_value(min_h, max_h) * height_scale
        pts.append((curr_x, horizon_y + y_offset - int(height)))
      else:
        dx = rl.get_random_value(int(min_dx * 0.8), int(max_dx * 0.8))
        curr_x += dx
        pts.append((curr_x, horizon_y + y_offset - rl.get_random_value(0, 20)))
      is_peak = not is_peak

    px = -100
    py = horizon_y + y_offset
    for cx, cy in pts:
      # Black fill
      rl.draw_triangle(
        rl.Vector2(float(px), float(horizon_y + y_offset)),
        rl.Vector2(float(cx), float(horizon_y + y_offset)),
        rl.Vector2(float(px), float(py)),
        bg_color,
      )
      rl.draw_triangle(
        rl.Vector2(float(px), float(py)),
        rl.Vector2(float(cx), float(horizon_y + y_offset)),
        rl.Vector2(float(cx), float(cy)),
        bg_color,
      )
      # Outline
      rl.draw_line_ex(rl.Vector2(float(px), float(py)), rl.Vector2(float(cx), float(cy)), float(line_thick), color)
      px = cx
      py = cy

  # Back layer (taller, wider)
  draw_mountain_layer(
    42,
    rl.Color(180, 0, 100, 255),
    80 if not is_mici else 40,
    150 if not is_mici else 80,
    100,
    300 if not is_mici else 150,
    0,
    2.0 if not is_mici else 1.0,
  )
  # Front layer (shorter, sharper, overlapping)
  draw_mountain_layer(
    99,
    grid_color,
    50 if not is_mici else 30,
    100 if not is_mici else 50,
    50,
    150 if not is_mici else 80,
    0,
    3.0 if not is_mici else 1.5,
  )

  # Draw grid (bottom half)
  num_h_lines = 30 if not is_mici else 20
  spacing = 50.0 if not is_mici else 30.0
  for i in range(num_h_lines + 1):
    f = (i + (grid_offset / spacing)) / num_h_lines
    y = horizon_y + (f ** 2) * (h - horizon_y)

    alpha = int(min(255, 255 * (f * 2.0)))
    line_color = rl.Color(grid_color.r, grid_color.g, grid_color.b, alpha)

    rl.draw_line(0, int(y), w, int(y), line_color)

  num_v_lines = 60 if not is_mici else 30
  for i in range(-num_v_lines, num_v_lines):
    x_bottom = center_x + i * (80 if not is_mici else 50)
    rl.draw_line(center_x, horizon_y, int(x_bottom), h, grid_color)

  # Draw a gradient rectangle over the horizon to fade out the vertical lines smoothly
  fog_height = 200 if not is_mici else 100
  for i in range(fog_height):
    alpha = int(255 * (1.0 - (i / fog_height)))
    fog_color = rl.Color(bg_color.r, bg_color.g, bg_color.b, alpha)
    rl.draw_line(0, horizon_y + i, w, horizon_y + i, fog_color)

  # Add a soft glow to the horizon line
  glow_size = 20 if not is_mici else 10
  for i in range(1, glow_size):
    alpha = int(100 * (1.0 - (i / glow_size)))
    glow_col = rl.Color(horizon_color.r, horizon_color.g, horizon_color.b, alpha)
    rl.draw_line(0, horizon_y - i, w, horizon_y - i, glow_col)
    rl.draw_line(0, horizon_y + i, w, horizon_y + i, glow_col)

  # Draw cyan horizon line with thickness
  rl.draw_line_ex(
    rl.Vector2(float(0), float(horizon_y)),
    rl.Vector2(float(w), float(horizon_y)),
    4.0 if not is_mici else 2.0,
    horizon_color,
  )

  # Draw GaryPilot pixel art badge centered in the lower half of the screen
  if gp_texture is not None:
    gp_w = gp_texture.width
    gp_h = gp_texture.height
    gp_scale = 1.5 if is_mici else 6.0
    badge_w = float(int(gp_w * gp_scale))
    badge_h = float(int(gp_h * gp_scale))
    gp_x = float(center_x - int(badge_w / 2))
    lower_half_center_y = horizon_y + (h - horizon_y) // 2
    gp_y = float(lower_half_center_y - int(badge_h / 2))
    dest = rl.Rectangle(gp_x, gp_y, badge_w, badge_h)
    source = rl.Rectangle(0.0, 0.0, float(gp_w), float(gp_h))
    rl.draw_texture_pro(gp_texture, source, dest, rl.Vector2(0.0, 0.0), 0.0, rl.WHITE)


class ScreenSaverSP(Widget):
  def __init__(self, params: Params | None = None):
    super().__init__()
    self.set_rect(rl.Rectangle(0, 0, gui_app.width, gui_app.height))
    self._params = params or (Params() if Params is not None else None)
    self._is_mici = HARDWARE.get_device_type() == 'mici' or (HARDWARE.get_device_type() == "pc" and os.getenv("BIG") != "1")

    self.logo_path, self.gp_logo_path = ensure_screensaver_assets()

    self.texture = None
    self.gp_texture = None
    self._start_time = None
    self._dismiss = False
    self._screensaver_timeout = 300

    # Outrun variables
    self.grid_offset = 0.0
    self.grid_speed = 40.0 if self._is_mici else 80.0

  @property
  def is_active(self) -> bool:
    return self._start_time is not None and not self._dismiss

  @property
  def was_dismissed(self) -> bool:
    return self._dismiss

  def initialize(self):
    self._screensaver_timeout = self._params.get("ScreenSaverTimeout", return_default=True) if self._params is not None else 300
    if self._start_time is None:
      self._start_time = time.monotonic()
    self._dismiss = False
    if self.texture is None:
      self.texture = rl.load_texture(self.logo_path)
    if self.gp_texture is None:
      self.gp_texture = rl.load_texture(self.gp_logo_path)

  def hide_event(self):
    super().hide_event()
    self._dismiss = False
    self._start_time = None

  def _handle_mouse_release(self, mouse_pos):
    self._dismiss = True
    self._start_time = None
    gui_app.pop_widget()
    return super()._handle_mouse_release(mouse_pos)

  def _update_state(self):
    super()._update_state()

    if self._start_time and time.monotonic() - self._start_time > self._screensaver_timeout:
      self._dismiss = True
      self._start_time = None

    dt = rl.get_frame_time()
    self.grid_offset += self.grid_speed * dt
    spacing = 50.0 if not self._is_mici else 30.0
    # Wrap offset around spacing for infinite loop effect
    if self.grid_offset > spacing:
      self.grid_offset -= spacing

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    draw_screensaver(
      int(self.rect.width),
      int(self.rect.height),
      self._is_mici,
      self.grid_offset,
      self.texture,
      self.gp_texture,
      time.monotonic(),
    )
    return -1
