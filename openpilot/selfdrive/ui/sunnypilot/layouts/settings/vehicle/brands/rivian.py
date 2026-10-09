"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import pyray as rl
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.vehicle.brands.base import BrandSettings
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.sunnypilot.widgets.list_view import multiple_button_item_sp
from openpilot.system.ui.widgets.list_view import text_item
from opendbc.car.rivian.values import RivianFlags


class RivianSettings(BrandSettings):
  def __init__(self):
    super().__init__()

    self._angle_status = tr("Standby")
    self._long_status = tr("Standby")
    self._gen_status = tr("Detecting...")
    self._radar_status = tr("Standby")
    self._bsm_status = tr("Standby")
    self._prev_summary = ""

    # Hardware Diagnostics (Option 1)
    self.angle_harness_item = text_item(
      tr("Lateral Angle Harness (0x1310)"),
      lambda: self._angle_status,
      description=tr("Angle sensor passthrough harness on CAN bus 1 at address 0x1310. Enables openpilot steering control.")
    )
    self.long_harness_item = text_item(
      tr("Longitudinal Harness / XNOR (0x131a)"),
      lambda: self._long_status,
      description=tr("Longitudinal upgrade / XNOR XTREME harness on CAN bus 1 at address 0x131a. Enables radar forwarding, BSM, and openpilot longitudinal control.")  # noqa: E501
    )
    self.platform_gen_item = text_item(
      tr("Vehicle Generation"),
      lambda: self._gen_status,
      description=tr("Rivian vehicle electrical architecture generation. Gen 1 includes capacitive steering wheel touch; Gen 2 uses vision/torque driver monitoring.")  # noqa: E501
    )
    self.radar_item = text_item(
      tr("Front Radar (Continental ARS430)"),
      lambda: self._radar_status,
      description=tr("Factory front millimeter-wave radar forwarding 32 object tracks through the longitudinal harness.")
    )
    self.bsm_item = text_item(
      tr("Corner Radar Blind-Spot Monitoring"),
      lambda: self._bsm_status,
      description=tr("Factory corner radar modules forwarding blind-spot monitoring alerts to openpilot.")
    )

    # Control Customizations (Options 2 & 3)
    stalk_texts = [tr("MADS Toggle"), tr("Cancel ACC"), tr("Disengage All")]
    self.stalk_up1_item = multiple_button_item_sp(
      tr("Stalk UP_1 Tap Action"),
      tr("Configure the action when flicking the gear stalk up to UP_1: toggle MADS lateral steering, cancel factory ACC/longitudinal, or disengage both."),
      stalk_texts,
      button_width=250,
      callback=self._on_stalk_up1_selected,
      param="RivianStalkUp1Action",
      inline=False,
    )

    speed_step_texts = [tr("1 mph / km/h"), tr("5 mph / km/h")]
    self.speed_step_item = multiple_button_item_sp(
      tr("Thumbpad Speed Click Step"),
      tr("Configure the set speed increment when clicking the right steering wheel thumbpad left/right."),
      speed_step_texts,
      button_width=250,
      callback=self._on_speed_step_selected,
      param="RivianSpeedClickStep",
      inline=False,
    )

    sensitivity_texts = [tr("Light"), tr("Standard"), tr("Firm")]
    self.steer_sensitivity_item = multiple_button_item_sp(
      tr("Driver Override Sensitivity"),
      tr("Adjust steering resistance threshold before openpilot yields to driver intervention. Light allows effortless steering override; Firm holds the lane more rigidly against minor steering touches."),  # noqa: E501
      sensitivity_texts,
      button_width=250,
      callback=self._on_steer_sensitivity_selected,
      param="RivianSteerOverrideSensitivity",
      inline=False,
    )

    self.items = [
      self.angle_harness_item,
      self.long_harness_item,
      self.platform_gen_item,
      self.radar_item,
      self.bsm_item,
      self.stalk_up1_item,
      self.speed_step_item,
      self.steer_sensitivity_item,
    ]

  @staticmethod
  def _on_stalk_up1_selected(index: int):
    ui_state.params.put("RivianStalkUp1Action", index)

  @staticmethod
  def _on_speed_step_selected(index: int):
    ui_state.params.put("RivianSpeedClickStep", index)

  @staticmethod
  def _on_steer_sensitivity_selected(index: int):
    ui_state.params.put("RivianSteerOverrideSensitivity", index)

  def update_settings(self):
    cp = ui_state.CP
    if cp is not None and cp.carFingerprint != "MOCK":
      # 1. Lateral Angle Harness (0x1310)
      if not cp.dashcamOnly:
        self._angle_status = tr("Connected")
        self.angle_harness_item.action_item.color = rl.Color(120, 220, 120, 255)
      else:
        self._angle_status = tr("Not Detected")
        self.angle_harness_item.action_item.color = rl.Color(220, 120, 120, 255)

      # 2. Longitudinal Harness Upgrade / XNOR XTREME (0x131a)
      if cp.alphaLongitudinalAvailable:
        self._long_status = tr("Connected")
        self.long_harness_item.action_item.color = rl.Color(120, 220, 120, 255)
      else:
        self._long_status = tr("Not Detected")
        self.long_harness_item.action_item.color = rl.Color(200, 200, 200, 255)

      # 3. Vehicle Generation
      is_gen2 = bool(cp.flags & RivianFlags.GEN2)
      self._gen_status = tr("Gen 2 (2025+)") if is_gen2 else tr("Gen 1 (2022–2024)")
      self.platform_gen_item.action_item.color = rl.Color(220, 220, 220, 255)

      # 4. Front Radar
      if not cp.radarUnavailable:
        self._radar_status = tr("32 Tracks Active")
        self.radar_item.action_item.color = rl.Color(120, 220, 120, 255)
      else:
        self._radar_status = tr("Unavailable")
        self.radar_item.action_item.color = rl.Color(200, 200, 200, 255)

      # 5. Corner Radar BSM
      if cp.enableBsm:
        self._bsm_status = tr("Active")
        self.bsm_item.action_item.color = rl.Color(120, 220, 120, 255)
      else:
        self._bsm_status = tr("Not Detected")
        self.bsm_item.action_item.color = rl.Color(200, 200, 200, 255)

      # Telemetry / Status summary for Sunnylink
      angle_ok = not cp.dashcamOnly
      long_ok = cp.alphaLongitudinalAvailable
      radar_ok = not cp.radarUnavailable
      gen_str = "Gen 2" if is_gen2 else "Gen 1"
      summary = f"Angle: {'OK' if angle_ok else 'None'} | Long: {'OK' if long_ok else 'None'} | {gen_str} | Radar: {'32 Tracks' if radar_ok else 'None'}"
      if summary != self._prev_summary:
        self._prev_summary = summary
        ui_state.params.put("RivianHarnessStatus", summary)
    else:
      self._angle_status = tr("Standby")
      self._long_status = tr("Standby")
      self._gen_status = tr("Detecting...")
      self._radar_status = tr("Standby")
      self._bsm_status = tr("Standby")

    # Disable controls while engaged
    engaged = ui_state.engaged
    self.stalk_up1_item.action_item.set_enabled(not engaged)
    self.speed_step_item.action_item.set_enabled(not engaged)
    self.steer_sensitivity_item.action_item.set_enabled(not engaged)
