"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.vehicle.brands.base import BrandSettings
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.sunnypilot.widgets.list_view import multiple_button_item_sp, toggle_item_sp


class RivianSettings(BrandSettings):
  def __init__(self):
    super().__init__()

    self.aeb_guard_toggle = toggle_item_sp(
      tr("Direct ESP AEB Safety Guard"),
      "",
      param="RivianAebGuard",
      callback=self._on_settings_changed,
    )

    regen_texts = [tr("Smooth (EV Regen)"), tr("Standard"), tr("Dynamic")]
    self.regen_decel_item = multiple_button_item_sp(
      tr("Regenerative Braking Deceleration Blend"),
      "",
      regen_texts,
      button_width=250,
      callback=self._on_regen_selected,
      param="RivianRegenDecel",
      inline=False,
    )

    self.auto_resume_toggle = toggle_item_sp(
      tr("Stop and Go Auto-Resume"),
      "",
      param="RivianStopAndGoAutoResume",
      callback=self._on_settings_changed,
    )

    self.items = [self.aeb_guard_toggle, self.regen_decel_item, self.auto_resume_toggle]

  def _on_settings_changed(self, _):
    self.update_settings()

  @staticmethod
  def _on_regen_selected(index):
    ui_state.params.put("RivianRegenDecel", index)

  def update_settings(self):
    is_offroad = ui_state.is_offroad()
    long_enabled = ui_state.has_longitudinal_control

    offroad_msg = tr("Enable \"Always Offroad\" in Device panel, or turn vehicle off to toggle.") if not is_offroad else ""

    # AEB Guard description
    aeb_desc = tr("Ensures openpilot instantly relinquishes longitudinal control whenever factory Automatic Emergency Braking (AEB) intervenes, allowing the vehicle Bosch ESP unit full braking authority without delay.")
    self.aeb_guard_toggle.action_item.set_enabled(is_offroad)
    self.aeb_guard_toggle.set_description(f"<b>{offroad_msg}</b><br><br>{aeb_desc}" if offroad_msg else aeb_desc)

    # Regen deceleration blend description
    regen_descs = [
      tr("Smooth deceleration prioritizing native motor regen coast-down, comfortable for EV driving."),
      tr("Standard balanced deceleration curve."),
      tr("Dynamic deceleration curve with stronger initial response."),
    ]
    regen_param = int(ui_state.params.get("RivianRegenDecel") or "0")
    cur_regen_desc = regen_descs[regen_param] if regen_param < len(regen_descs) else regen_descs[0]

    if not is_offroad:
      cur_regen_desc = f"<b>{offroad_msg}</b><br><br>{cur_regen_desc}"
    elif not long_enabled:
      disabled_long_msg = tr("This feature is unavailable because sunnypilot Longitudinal Control (Alpha) is not enabled.")
      cur_regen_desc = f"<b>{disabled_long_msg}</b><br><br>{cur_regen_desc}"

    self.regen_decel_item.action_item.set_enabled(is_offroad and long_enabled)
    self.regen_decel_item.set_description(cur_regen_desc)
    self.regen_decel_item.show_description(True)
    self.regen_decel_item.action_item.set_selected_button(regen_param)

    # Auto-resume description
    resume_desc = tr("Automatically resumes acceleration when lead vehicle departs from a complete standstill without requiring an accelerator pedal press.")
    if not is_offroad:
      resume_desc = f"<b>{offroad_msg}</b><br><br>{resume_desc}"
    elif not long_enabled:
      disabled_long_msg = tr("This feature is unavailable because sunnypilot Longitudinal Control (Alpha) is not enabled.")
      resume_desc = f"<b>{disabled_long_msg}</b><br><br>{resume_desc}"

    self.auto_resume_toggle.action_item.set_enabled(is_offroad and long_enabled)
    self.auto_resume_toggle.set_description(resume_desc)
