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

R_LOGO_B64 = "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"  # noqa: E501

GARYPILOT_LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAJkAAAAoCAYAAADtylhqAAAFYklEQVR4nO2bT2hURxjAJy8qkadJxVXKeijtQbwJxkARL4K00kuhETxUENNC0pMLlZCg4ArVJyEFe9HuIZWCezM9liCCl1IKBaG3kEOlh4awHppYHhQkSQ/db3fet9/MfN+8txvdzu+UN/PN92++NzNv34tSgUAgEAgEAoFAoO8Z2GkHAm22VXVGOmZAVe90w5ci2bXTDgT+AwosjmoJ7ku3JmdN7b3wLS+sIvO5w2y8CXcflyJyA/mAQtr97petvlfPvza2dxNbXNL5cxaZ7Q7z4U25+zgUkZt0a3JWn9Chkzcz/a+e29u7SVGrp7XIcBLjc3el+jOkS5Vc418nishNulRRcVRL9IkbLI2Qsqb2bqPH5Tt/zpUMkjh88YGXgX4mb26GLz5QLx9ezhRaulQh9e1UkRVhl3UmO1BZzG0IU8STVLfPihz9eXNzoLKo/ro73iq0OKolLx9e7pAbLA07dfnmY0BV75jGUnZNsqazGqvIdqFqfnH9LGeYE8lZBs4uEEivzoom/SDvk5tDXz3puHaNw3YwvvnQz4TUWGzXlQ8KVpHpS+ba1JhTqYS3v/3VKbM2Nda60/W7CALm6AA9lDy0c33U5aW5iaNa8uL6WdJnKh7Qadu2cJFI8qGvoK6xpj5X/sRFplS+AsNLKmfPP/JoRf15/mjm7AJJOfJoReyD9Jxhkzflhto6tlV1BiZ0bWqM9N0Uj8kHXGCSfOh5lY6VwCqy/Qf3dbT5bFN4yzPppjj2dFUtnylnCu3Y01WpCyKbHHmqz3Q2gbMPFBo11mTL5gPMhU8+IK8uG3lgFdmodhMta+2fPuMHVT9RJre8UcGiMvpstaVHOrZ+otzWg8YtKzs2eVNubFD+w1iTLZfPkrnAgK7lM2UvPa64WUV2+3j777qh3aljc1W9M9ieaEi0PvkUf2xmg64b2nXdJmAFwX7XafEWNnkqN5ynPFNcJlsun3G/Kx+6fX1u8HzocpwcU7CKrCRsdwEFlm7a75p4sCyyzT0rSv22yeM+7jFCmlOXz5J8xFEt4chTcoX/4g98GNN6Te02YBJOD11ijZfatr1XgxVG6rdNHvedHrok1vnTP987bbl85ubDlQP8ExElV/i7S6WUOjiwm2zXk0Px8d7PRe0S26b2PDp95HGfr1+wlfvGW2RMefRS8LbLqNOQa9mMo1pCjcP6FtL7Ytu2dg6msfjJl2ML90n9wvH7xsuJST8rcv3Mk2eAt5JFezLX+KUud5ytndIXR7VEooMLNZZ68uXYwn0L6X01vf+K1f7c399krvXYJfHq88CNCY4r3PzlyTMgXsnmRq6q6Y151gGXc1e69PViJfP1wdSHi4jCdJNy48U+S2KaG7mauZ7emDf62bOVrIT25e/eyvdGyVffxHo7X1iHhOmN+Q6bJh8m1hOrLdwnefrSt2ZYbUy2bD5PrCeimCiMRd+rM9nEeqIWD9/IbawIfXBAHtnjt4z7jLfJUn15vvyl9HF99snJeKP9MSTlt2+edZxFBgGON26qH9+7lc9aw1/fR79fy1zv3YeCb7h16J+0QHKdPjTstjJ9DB9c2GwZfW44+g1ATm2rbxHxWYsMv2vDE+2Lrz49GXl80V+yc/R0TLxGUTlx6XP5LI0JjzOtvkXEx/qXuKI/Duwm3K2KExMcmn85lT3Iv//zFevd77NduvyxfViYF9MXIxJ5u/7/OduqOmN7Uv7tg87f8Y4//kKlW5Oz/fRfV90k/N9lk5VPFlhyR3/4rMue9B+hyJrYzl2Yfvq3vl4QiqyJq8hK9y5krsNWyScUWRNcRBRhBfMjFJny/5U+EAgEAoFAIBAIBAJN/gXkYp/nMKQdPAAAAABJRU5ErkJggg=="  # noqa: E501

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
