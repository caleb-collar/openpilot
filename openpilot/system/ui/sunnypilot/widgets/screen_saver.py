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

RIVIAN_LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAEBUlEQVR4nO3dUW+jQBADYOfU//+X04cTEqoSEmBmxx6PpXtqWLb4EyF0wz2ezycmvvlXPYFJbQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeX6qJ1CUd8ugHktnQRA3AJ/Wv20/t4HgAuDswkcbCA7XAHdWvbZfMdsdQESBrRF0BhBZXFsEXQFkFNYSQUcAmUW1Q9ANwIqCWiHoBGBlMW0QdAFQUUgLBB0AVBYhj0AdAEMBDHO4HGUATAeeaS6nogog6oA/EHe/XxKBIoCIA/23+CgIcgjUANw9wJ+KjoAghUAJQET5Ga99FRkEKgBWln9nm30kECgAqCg/YltAAAE7gJXlZ60TpEbADCCj/Ofu37t9vvpZWwSsALLKv7P/lggYAVSXf7RNOwRsAFjKP9q2FQImAGzlH43RBgELANbyj8ZqgYABAHv5R2PKI6gGoFL+0djSCCoBqJV/tA9ZBFUAVMs/2pckggoA6uUf7VMOwWoAXco/2rcUgpUAupW/RRrBKgBdy98ii2AFAMbyX42ZURg9gmwAKuV/87NvIocgE4Ba+WdecxQpBFkAVMu/8tpXkUGQAUC9/Dvb7COBIBpA5QLOjDHZ5gMEI4gEkFX+nXEjCrwzBv1C0+q/Bm5hLT9iLOqnkjIAYDzNKo95bgLE/3v41YllH1TWeV0KwxlgUpgBYB5mAFdPmfOcwBOJfFo4yxU78H8uGWNeDe2nHJYzQMZHpexl4d8mo/ywRAKgubkRPCbjvMLObtFngG73z7v8XeNtMt4CuiBoXz6Qdw2gjsCifCD3IlAVgU35QP6nADUEVuUDaz4GqiCwKx9Ydx+AEUFkJMsH1t4I6opAtnyA507gt2FDwP6FlY9ZDSDrgcwVCLLKX/q7VJwBOiBoUT5Q9xagjKBN+UDtNYAiglblA/UXgUoI2pUP1AMANBC0LB/gAABwI2hbPsADAOBE0Lp8gAsAwIWgffkAHwCAA4FF+QAnAKAWgU35APdXwwCOA88wh7SwngG2ZJ0JVmy7hbZ8gB8AUIegffmABgBgPQKL8gEdAEAcgk9rAm3KB7QAAHEH9lXRUVfDMuUDsV8OXZUH4sqK/ggkVT6gdwbYwnigGef0MaoAAK4DzjSXU1EGAHAceIY5XI46AIBvVbBUOgAAeFYFy6ULAKB+VbBkOgEA6lYFy6YbAGD9qmDpdAQANH2sa0YU7wR+m60wmS9qVqTrGWCf6EWhreIAADhf5OPCNpLp/BbwN/tCqZ/hvzJOAPaxK/pdXN4CJm8yAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMzzC6004gUSWLKnAAAAAElFTkSuQmCC"  # noqa: E501

GARYPILOT_LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAJkAAAAoCAYAAADtylhqAAAFkUlEQVR4nO2bQWicRRSAJ7trXPltlpCIYYsVD0p6EKFJvEqhoHg1J9tLD5JAEBa8JNDCSsTtRSiI4OKhl66n9FSoEYSSq8ZePLjUQ3HFEChBWlnItibxsDv7zz/73pv35v83set8l+Sfee/Ne2/ePzP/7r9KBQKBQCAQCAQCgZFn7KQdCMQcqeqqVGdMVa8Nw5csKZy0A4EuusCiXL1m97UPl9aw9uPwLS2sIvO5wyiehbuPSxa50fnQhfTca5/0+54++AJtHyZUXNL5cxYZdYf58KzcfRyyyE37cGnNnNDi/KeJ/qcP6PZhktXqSRaZncTovetS+wnam5VU+v8lsshNe7Oioly9Zk5cfroEymLtw8aMy3f+nCuZTuLEpRteA4wyaXMzcemGenzzcqLQ2psV0N5JFVkW47LOZJOVW6kHssniSWrYZ0WO/bS5mazcUn9d/6BfaFGuXnt88/KAXH56wmnLNx9jqnoN04XGxWSxsxqryApWNT+8coGj5kRyltFnFx3IcZ0VMfta3ic3L332w8C1S88ex8Y3H+aZENK1x3XlA4JVZOaSubu84DQqYebrn5wyu8sL/TvdvIt0wBwb2g4kr9u5Ppry0txEuXrt4ZULoM9QPNomtW3ZRSLJh7mCunSxPlf+xEWmVLoCs5dUzp5/euO++nPxjcTZRSfl9MZ9sQ/ScwYlj+UG2jqOVHVVT+ju8gLoOxYP5oNdYJJ8mHmV6kpgFdmpqRcH2ny2KXvLw2xDzN7dUc3z5UShzd7dkbogGpMjD/VhZxN99tGFBuliY1E+6LnwyYfOq2uMNLCKbM64iZpG+8V7/KAa58rgljcnWFTm7u307Uh1G+fKsR1Lr6loKHksNxSQ/1oXG8vls2QubLSt5vmylx1X3Kwi+/yt+P8G0u60cbCjXs3HE60TbU4+xO8HyaAbSLtpG0OvILbfDVi8DyUP5YbzlIfFhY3l8tnud+XDHN+cG3s+TDlOjiFYRTYtbHehC6x9QN81Ub4sGpt7VpT6TcnbfdxjhDSnLp8l+Yhy9RpHHpLL/BN/zdkoMq5KSDuHUn8SzhQfMfRLgEwJGbvbTn2vplcYTBeDkrdzc6b4iLQF6bX2qZzS8br0sM/+XPKwnDvHEKwieznK9f9v7Svjf3pyFqb+Tlxr3W57blDBorWfHNu0gbVzkOpS8nZubFkOrf14K/eNN8uYMDlJjk1YRTZjOrTX/eNaNqNcvTZjJ3xv0N7tFr2acWyY7RwwXfvJ1yU/0LcHyDqw4/eNlxOTeVbk5g+aeynMIssnru0vdbl6VDtkr1uofBtcIF3oyZczlt13uxWpj87St/w3vxYT12bsknjNeeDG1P/QlZm/NHnWiFeyq/NP1Pr2OOuAi93VEnscG1JsXV8fsD67iCCwm5Qbr+2zJKar80+UeVxZ3x5H/UyTZ418u1RKffXOP0zzvITR9mLZla3Y3TTBr2+PD4yJ+bCyVRAVmeTpy9ya9WqDjUX5vLJVEMUEzYu06CWwimxlq6A23j9KPVgW9uIDst8y7qNPyUJ9ad78hexxffbJyeKd+GcekN++eTZxFpkOcPHOmPr+4vMph+t423u30Ulcn5q0t6SOcmG+0qKT6/ahQ46V7HP74IIaC/e54+iH0TmlVt8s4iOLzP6uzZ5oX3ztmclI44v5JTvHzgtT9hNwrJNVTlz2XD5LY7L1sNU3i/hYP4nL+uXAYcLdqjgx6UPzj9VXEu1vV/8g736f7dLlD/ViYVqwN0Yk8rT9/zlHqrpKPSn/8uXsQNubHzdV+3BpbZR+dTVMwu8ue/z27RxL7vUPfx6yJ6NHKLIeg+cunFH6Wd9xEIqsR9FRZNPz3yWuw1bJJxRZD7uIIMIK5kcoMuX/KX0gEAgEAoFAIBAIBHr8C5kfwD+uIlpuAAAAAElFTkSuQmCC"  # noqa: E501

RIVIAN_LOGO_PATH = "/tmp/rivian_logo_screensaver.png"
GARYPILOT_LOGO_PATH = "/tmp/garypilot_screensaver_logo.png"


def ensure_screensaver_assets() -> tuple[str, str]:
  for path, b64_data in [(RIVIAN_LOGO_PATH, RIVIAN_LOGO_B64), (GARYPILOT_LOGO_PATH, GARYPILOT_LOGO_B64)]:
    data = base64.b64decode(b64_data)
    if not os.path.exists(path) or os.path.getsize(path) != len(data):
      with open(path, "wb") as f:
        f.write(data)
  return RIVIAN_LOGO_PATH, GARYPILOT_LOGO_PATH


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
