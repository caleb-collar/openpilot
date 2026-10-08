"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import os
import time
import base64
import math

import pyray as rl

from openpilot.common.hardware import HARDWARE
from openpilot.common.params import Params
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import Widget


class ScreenSaverSP(Widget):
  def __init__(self, params: Params | None = None):
    super().__init__()
    self.set_rect(rl.Rectangle(0, 0, gui_app.width, gui_app.height))
    self._params = params or Params()
    self._is_mici = HARDWARE.get_device_type() == 'mici' or (HARDWARE.get_device_type() == "pc" and os.getenv("BIG") != "1")

    # Save the base64 Rivian logo to tmp so we can load it as a texture
    self.logo_path = "/tmp/rivian_logo_screensaver.png"
    b64_logo = "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAEBUlEQVR4nO3dUW+jQBADYOfU//+X04cTEqoSEmBmxx6PpXtqWLb4EyF0wz2ezycmvvlXPYFJbQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeQaAeX6qJ1CUd8ugHktnQRA3AJ/Wv20/t4HgAuDswkcbCA7XAHdWvbZfMdsdQESBrRF0BhBZXFsEXQFkFNYSQUcAmUW1Q9ANwIqCWiHoBGBlMW0QdAFQUUgLBB0AVBYhj0AdAEMBDHO4HGUATAeeaS6nogog6oA/EHe/XxKBIoCIA/23+CgIcgjUANw9wJ+KjoAghUAJQET5Ga99FRkEKgBWln9nm30kECgAqCg/YltAAAE7gJXlZ60TpEbADCCj/Ofu37t9vvpZWwSsALLKv7P/lggYAVSXf7RNOwRsAFjKP9q2FQImAGzlH43RBgELANbyj8ZqgYABAHv5R2PKI6gGoFL+0djSCCoBqJV/tA9ZBFUAVMs/2pckggoA6uUf7VMOwWoAXco/2rcUgpUAupW/RRrBKgBdy98ii2AFAMbyX42ZURg9gmwAKuV/87NvIocgE4Ba+WdecxQpBFkAVMu/8tpXkUGQAUC9/Dvb7COBIBpA5QLOjDHZ5gMEI4gEkFX+nXEjCrwzBv1C0+q/Bm5hLT9iLOqnkjIAYDzNKo95bgLE/3v41YllH1TWeV0KwxlgUpgBYB5mAFdPmfOcwBOJfFo4yxU78H8uGWNeDe2nHJYzQMZHpexl4d8mo/ywRAKgubkRPCbjvMLObtFngG73z7v8XeNtMt4CuiBoXz6Qdw2gjsCifCD3IlAVgU35QP6nADUEVuUDaz4GqiCwKx9Ydx+AEUFkJMsH1t4I6opAtnyA507gt2FDwP6FlY9ZDSDrgcwVCLLKX/q7VJwBOiBoUT5Q9xagjKBN+UDtNYAiglblA/UXgUoI2pUP1AMANBC0LB/gAABwI2hbPsADAOBE0Lp8gAsAwIWgffkAHwCAA4FF+QAnAKAWgU35APdXwwCOA88wh7SwngG2ZJ0JVmy7hbZ8gB8AUIegffmABgBgPQKL8gEdAEAcgk9rAm3KB7QAAHEH9lXRUVfDMuUDsV8OXZUH4sqK/ggkVT6gdwbYwnigGef0MaoAAK4DzjSXU1EGAHAceIY5XI46AIBvVbBUOgAAeFYFy6ULAKB+VbBkOgEA6lYFy6YbAGD9qmDpdAQANH2sa0YU7wR+m60wmS9qVqTrGWCf6EWhreIAADhf5OPCNpLp/BbwN/tCqZ/hvzJOAPaxK/pdXN4CJm8yAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMwzAMzzC6004gUSWLKnAAAAAElFTkSuQmCC"
    if not os.path.exists(self.logo_path):
      with open(self.logo_path, "wb") as f:
        f.write(base64.b64decode(b64_logo))
    
    self.texture = None
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
    self._screensaver_timeout = self._params.get("ScreenSaverTimeout", return_default=True)
    if self._start_time is None:
      self._start_time = time.monotonic()
    self._dismiss = False
    if self.texture is None:
      self.texture = rl.load_texture(self.logo_path)

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
    # Wrap offset around spacing for infinite loop effect
    if self.grid_offset > 50.0:
      self.grid_offset -= 50.0

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    
    # Outrun Colors
    bg_color = rl.Color(13, 2, 33, 255)       # Deep synthwave purple/black
    grid_color = rl.Color(255, 0, 128, 255)   # Hot pink/magenta
    horizon_color = rl.Color(0, 255, 255, 255) # Cyan glow
    sun_color_top = rl.Color(255, 204, 0, 255)  # Yellow top
    sun_color_bot = rl.Color(255, 0, 128, 255)  # Pink bottom
    
    rl.clear_background(bg_color)
    
    w = int(self.rect.width)
    h = int(self.rect.height)
    horizon_y = h // 2
    center_x = w // 2
    
    # Draw outrun sun (with slices)
    sun_radius = 300 if not self._is_mici else 150
    sun_y = horizon_y
    num_slices = 80
    for i in range(num_slices):
      slice_y = sun_y - sun_radius + int((i / num_slices) * (sun_radius * 2))
      
      # Add gaps to the bottom half of the sun
      if slice_y > horizon_y:
        if (i // 2) % 2 == 0:  # Skip some slices to create gaps
          continue
      
      # Calculate width of circle at this y
      dy = slice_y - sun_y
      val = sun_radius**2 - dy**2
      if val < 0: val = 0
      slice_w = int(math.sqrt(val))
      if slice_w == 0:
        continue
      
      # Interpolate color from yellow to pink
      t = i / num_slices
      r = int(sun_color_top.r + t * (sun_color_bot.r - sun_color_top.r))
      g = int(sun_color_top.g + t * (sun_color_bot.g - sun_color_top.g))
      b = int(sun_color_top.b + t * (sun_color_bot.b - sun_color_top.b))
      slice_color = rl.Color(r, g, b, 255)
      
      # Draw the slice as a rectangle for thickness
      rl.draw_rectangle(center_x - slice_w, slice_y, slice_w * 2, 3, slice_color)
        
    # Draw grid (bottom half)
    cam_y = 5.0
    fov = w * 0.8
    z_far = 100.0
    z_near = 1.0
    
    # Horizontal lines
    grid_spacing = 5.0
    for z_i in range(int(z_near), int(z_far + grid_spacing), int(grid_spacing)):
      z = z_i - (self.grid_offset / 10.0)
      if z < z_near: continue
      
      py = horizon_y + (cam_y / z) * fov
      if py > h: continue
      
      f_val = 1.0 - (z / z_far)
      if f_val < 0: f_val = 0
      alpha = int(255 * (f_val ** 1.5))
      line_color = rl.Color(grid_color.r, grid_color.g, grid_color.b, alpha)
      
      rl.draw_line(0, int(py), w, int(py), line_color)
        
    # Vertical lines
    for x_i in range(-100, 100, int(grid_spacing)):
      px1 = center_x + (x_i / z_near) * fov
      py1 = horizon_y + (cam_y / z_near) * fov
      px2 = center_x + (x_i / z_far) * fov
      py2 = horizon_y + (cam_y / z_far) * fov
      rl.draw_line(int(px1), int(py1), int(px2), int(py2), grid_color)

    # Draw cyan horizon line with thickness

    # Draw cyan horizon line with thickness
    rl.draw_line_ex(rl.Vector2(float(0), float(horizon_y)), rl.Vector2(float(w), float(horizon_y)), 4.0, horizon_color)

    # Draw the Rivian logo in the middle, sitting on the horizon
    if self.texture is not None:
      tex_w = self.texture.width
      tex_h = self.texture.height
      scale = 2.0 if not self._is_mici else 1.0
      dest = rl.Rectangle(float(center_x - (tex_w * scale) / 2), float(horizon_y - (tex_h * scale) / 2), float(tex_w * scale), float(tex_h * scale))
      source = rl.Rectangle(0.0, 0.0, float(tex_w), float(tex_h))
      
      # We tint it BLACK to make a perfect silhouette against the bright sun
      rl.draw_texture_pro(self.texture, source, dest, rl.Vector2(0.0, 0.0), 0.0, rl.BLACK)

    return -1
