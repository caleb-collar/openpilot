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
    bg_color = rl.Color(13, 2, 33, 255)       
    grid_color = rl.Color(255, 0, 128, 255)   
    horizon_color = rl.Color(0, 255, 255, 255) 
    
    rl.clear_background(bg_color)
    
    w = int(self.rect.width)
    h = int(self.rect.height)
    horizon_y = h // 2
    center_x = w // 2
    
    # Draw Stars
    rl.set_random_seed(1234)
    num_stars = 80 if not self._is_mici else 40
    for _ in range(num_stars):
        sx = rl.get_random_value(0, w)
        sy = rl.get_random_value(0, horizon_y - 50)
        size = rl.get_random_value(1, 2)
        alpha = rl.get_random_value(100, 255)
        
        # We can't easily use time in C++ raylib random seed loops predictably unless we pass time, 
        # so we'll just draw them static or use simple flickering based on x pos and monotonic time
        if rl.get_random_value(0, 5) == 0:
            import math
            import time
            alpha = int(127 + 127 * math.sin(time.monotonic() * 5.0 + sx))
            
        rl.draw_circle(sx, sy, float(size), rl.Color(255, 255, 255, alpha))
        
        if rl.get_random_value(0, 15) == 0:
            rl.draw_line(sx - 6, sy, sx + 6, sy, rl.Color(255, 255, 255, alpha))
            rl.draw_line(sx, sy - 6, sx, sy + 6, rl.Color(255, 255, 255, alpha))

    if self.texture is not None:
      # Logo as the Sun
      tex_w = self.texture.width
      tex_h = self.texture.height
      scale = 6.5 if not self._is_mici else 3.5
      
      dest = rl.Rectangle(float(center_x - (tex_w * scale) / 2), float(horizon_y - (tex_h * scale) / 2), float(tex_w * scale), float(tex_h * scale))
      source = rl.Rectangle(0.0, 0.0, float(tex_w), float(tex_h))
      
      # Add a glow behind the sun using transparent circles
      glow_radius = int((tex_w * scale) * 0.6)
      for r_idx in range(25):
          r = glow_radius * (1.0 - (r_idx / 25.0))
          g_alpha = int(100 * (r_idx / 25.0))
          rl.draw_circle(center_x, horizon_y, r, rl.Color(255, 100, 0, g_alpha))
      
      # Tint it sunset orange/yellow
      rl.draw_texture_pro(self.texture, source, dest, rl.Vector2(0.0, 0.0), 0.0, rl.Color(255, 204, 0, 255))
      
      # Draw black horizontal slices through the bottom half of the logo
      sun_radius = (tex_h * scale) / 2
      sun_y = horizon_y
      num_slices = 100 if not self._is_mici else 50
      for i in range(num_slices):
        slice_y = sun_y - sun_radius + int((i / num_slices) * (sun_radius * 2))
        if slice_y > horizon_y:
          if (i // 2) % 2 != 0:  
            rl.draw_rectangle(int(center_x - (tex_w * scale) / 2), int(slice_y), int(tex_w * scale), 4 if not self._is_mici else 2, bg_color)
    
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
                height_scale = 0.4 + 0.6 * (dist_from_center / (w/2))
                height = rl.get_random_value(min_h, max_h) * height_scale
                pts.append((curr_x, horizon_y + y_offset - int(height)))
            else:
                dx = rl.get_random_value(int(min_dx*0.8), int(max_dx*0.8))
                curr_x += dx
                pts.append((curr_x, horizon_y + y_offset - rl.get_random_value(0, 20)))
            is_peak = not is_peak
            
        px = -100
        py = horizon_y + y_offset
        for cx, cy in pts:
            # Black fill
            rl.draw_triangle(
                rl.Vector2(float(px), float(horizon_y + y_offset)),
                rl.Vector2(float(px), float(py)),
                rl.Vector2(float(cx), float(horizon_y + y_offset)),
                bg_color
            )
            rl.draw_triangle(
                rl.Vector2(float(px), float(py)),
                rl.Vector2(float(cx), float(cy)),
                rl.Vector2(float(cx), float(horizon_y + y_offset)),
                bg_color
            )
            # Outline
            rl.draw_line_ex(rl.Vector2(float(px), float(py)), rl.Vector2(float(cx), float(cy)), float(line_thick), color)
            px = cx
            py = cy

    # Back layer (taller, wider)
    draw_mountain_layer(42, rl.Color(180, 0, 100, 255), 80 if not self._is_mici else 40, 150 if not self._is_mici else 80, 100, 300 if not self._is_mici else 150, 0, 2.0 if not self._is_mici else 1.0)
    # Front layer (shorter, sharper, overlapping)
    draw_mountain_layer(99, grid_color, 50 if not self._is_mici else 30, 100 if not self._is_mici else 50, 50, 150 if not self._is_mici else 80, 0, 3.0 if not self._is_mici else 1.5)

    # Draw grid (bottom half)
    num_h_lines = 30 if not self._is_mici else 20
    spacing = 50.0 if not self._is_mici else 30.0
    for i in range(num_h_lines):
      f = (i + (self.grid_offset / spacing)) / num_h_lines
      if f > 1.0: f = 1.0
      y = horizon_y + (f ** 2) * (h - horizon_y)
      
      alpha = int(min(255, 255 * (f * 2.0)))
      line_color = rl.Color(grid_color.r, grid_color.g, grid_color.b, alpha)
      
      rl.draw_line(0, int(y), w, int(y), line_color)
        
    num_v_lines = 60 if not self._is_mici else 30
    for i in range(-num_v_lines, num_v_lines):
      x_bottom = center_x + i * (80 if not self._is_mici else 50)
      rl.draw_line(center_x, horizon_y, int(x_bottom), h, grid_color)

    # Draw a gradient rectangle over the horizon to fade out the vertical lines smoothly
    fog_height = 200 if not self._is_mici else 100
    for i in range(fog_height):
      alpha = int(255 * (1.0 - (i / fog_height)))
      fog_color = rl.Color(bg_color.r, bg_color.g, bg_color.b, alpha)
      rl.draw_line(0, horizon_y + i, w, horizon_y + i, fog_color)
        
    # Draw cyan horizon line with thickness
    rl.draw_line_ex(rl.Vector2(float(0), float(horizon_y)), rl.Vector2(float(w), float(horizon_y)), 4.0 if not self._is_mici else 2.0, horizon_color)

    return -1
