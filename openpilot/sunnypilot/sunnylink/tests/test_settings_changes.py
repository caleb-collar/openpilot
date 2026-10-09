"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Per-bug regression tests for the Raylib-vs-schema parity audit. Each test
isolates one of the gating bugs that the design-overhaul branch fixes so a
future regression is loud and obvious. These tests are intentionally narrow
and additive — they do not replace the broader test_settings_schema.py.
"""
from __future__ import annotations

import json
import os
from typing import Any

from openpilot.common.parameterized import parameterized

from openpilot.sunnypilot.sunnylink.tools.generate_settings_schema import (
  DEFINITION_PATH,
  TORQUE_VERSIONS_PATH,
  _build_torque_options,
  _load_torque_versions,
  generate_schema,
)
from openpilot.common.test import OpenpilotTestCase


SCHEMA_VALIDATOR_PATH = os.path.join(os.path.dirname(DEFINITION_PATH), "settings_ui.schema.json")


def _walk_items(schema: dict[str, Any]):
  """Yield every item dict from the schema."""
  def _yield(item: dict[str, Any]):
    yield item
    for sub in item.get("sub_items", []):
      yield from _yield(sub)

  for panel in schema.get("panels", []):
    for section in panel.get("sections", []):
      for item in section.get("items", []):
        yield from _yield(item)
      for sp in section.get("sub_panels", []):
        for item in sp.get("items", []):
          yield from _yield(item)
    for item in panel.get("items", []):
      yield from _yield(item)
    for sp in panel.get("sub_panels", []):
      for item in sp.get("items", []):
        yield from _yield(item)
  for brand in schema.get("vehicle_settings", {}).values():
    items = brand.get("items", []) if isinstance(brand, dict) else brand
    for item in items:
      yield from _yield(item)


def _find_item(schema: dict[str, Any], key: str) -> dict[str, Any] | None:
  for item in _walk_items(schema):
    if item.get("key") == key:
      return item
  return None


def _find_section(schema: dict[str, Any], panel_id: str, section_id: str) -> dict[str, Any] | None:
  for panel in schema.get("panels", []):
    if panel.get("id") != panel_id:
      continue
    for section in panel.get("sections", []):
      if section.get("id") == section_id:
        return section
  return None


def _flatten_rule_types(rules: list[dict[str, Any]] | None) -> set[str]:
  out: set[str] = set()

  def _walk(rule: dict[str, Any]) -> None:
    out.add(rule.get("type", ""))
    if rule.get("type") == "not" and "condition" in rule:
      _walk(rule["condition"])
    elif rule.get("type") in ("any", "all"):
      for c in rule.get("conditions", []):
        _walk(c)

  for rule in rules or []:
    _walk(rule)
  return out


def _references_capability_field(rules: list[dict[str, Any]] | None, field: str) -> bool:
  found = False

  def _walk(rule: dict[str, Any]) -> None:
    nonlocal found
    if rule.get("type") == "capability" and rule.get("field") == field:
      found = True
    elif rule.get("type") == "not" and "condition" in rule:
      _walk(rule["condition"])
    elif rule.get("type") in ("any", "all"):
      for c in rule.get("conditions", []):
        _walk(c)

  for rule in rules or []:
    _walk(rule)
  return found


def schema():
  return generate_schema()


class TestMadsBrandGates(OpenpilotTestCase):
  def test_mads_main_cruise_has_brand_gate(self, schema):
    """MadsMainCruiseAllowed must gate on brand and tesla_has_vehicle_bus."""
    item = _find_item(schema, "MadsMainCruiseAllowed")
    assert item is not None
    assert _references_capability_field(item.get("enablement"), "brand")
    assert _references_capability_field(item.get("enablement"), "tesla_has_vehicle_bus")

  def test_mads_unified_engagement_has_brand_gate(self, schema):
    """MadsUnifiedEngagementMode must mirror MadsMainCruiseAllowed brand-gate."""
    item = _find_item(schema, "MadsUnifiedEngagementMode")
    assert item is not None
    assert _references_capability_field(item.get("enablement"), "brand")
    assert _references_capability_field(item.get("enablement"), "tesla_has_vehicle_bus")

  def test_mads_steering_mode_options_allow_rivian(self, schema):
    """MadsSteeringMode Remain Active and Pause gate on tesla_has_vehicle_bus but allow Rivian."""
    item = _find_item(schema, "MadsSteeringMode")
    assert item is not None
    options = {opt["value"]: opt for opt in item.get("options", [])}
    for opt_val in (0, 1):
      enablement = options[opt_val].get("enablement", [])
      assert _references_capability_field(enablement, "brand")
      assert _references_capability_field(enablement, "tesla_has_vehicle_bus")
      assert "rivian" not in json.dumps(enablement), f"Option {opt_val} unexpectedly restricts Rivian"


class TestTestManeuversSection(OpenpilotTestCase):
  def test_lateral_maneuver_mode_in_test_maneuvers(self, schema):
    section = _find_section(schema, "developer", "test_maneuvers")
    assert section is not None, "developer.test_maneuvers section missing"
    keys = {item["key"] for item in section.get("items", [])}
    assert "LateralManeuverMode" in keys
    assert "LongitudinalManeuverMode" in keys

  def test_test_maneuvers_section_requires_attestation(self, schema):
    section = _find_section(schema, "developer", "test_maneuvers")
    assert section is not None
    assert section.get("attestation_required") is True

  def test_test_maneuvers_section_visibility_gate(self, schema):
    section = _find_section(schema, "developer", "test_maneuvers")
    assert section is not None
    visibility = section.get("visibility")
    assert visibility, "test_maneuvers must have visibility gate"
    vis_refs = json.dumps(visibility)
    assert "is_development" in vis_refs
    assert "is_sp_release" in vis_refs
    enablement = section.get("enablement") or []
    enable_refs = json.dumps(enablement)
    assert "ShowAdvancedControls" in enable_refs, \
      "test_maneuvers must gate ShowAdvancedControls via enablement"


class TestValidator(OpenpilotTestCase):
  def test_validator_accepts_real_json(self):
    """settings_ui.json validates against settings_ui.schema.json."""
    try:
      import jsonschema
    except ImportError:
      self.skipTest("jsonschema not installed")
    with open(DEFINITION_PATH) as f:
      data = json.load(f)
    with open(SCHEMA_VALIDATOR_PATH) as f:
      validator = json.load(f)
    jsonschema.validate(instance=data, schema=validator)


class TestTorqueOptionGeneration(OpenpilotTestCase):
  def test_torque_versions_match_generated_options(self, schema):
    versions = _load_torque_versions()
    assert versions, "latcontrol_torque_versions.json must have at least one version"
    expected = _build_torque_options(versions)
    item = _find_item(schema, "TorqueControlTune")
    assert item is not None, "TorqueControlTune item must be present"
    assert item.get("options") == expected

  def test_torque_versions_path_resolves(self):
    assert os.path.exists(TORQUE_VERSIONS_PATH), (
      f"latcontrol_torque_versions.json not found at {TORQUE_VERSIONS_PATH}"
    )


class TestReleaseBranchGates(OpenpilotTestCase):
  @parameterized.expand([
    "EnableGithubRunner",
    "QuickBootToggle",
  ], names=["key"])
  def test_sp_dev_items_gate_on_is_sp_release(self, schema, key):
    """sunnypilot dev items must hide on sunnypilot release branches (is_sp_release gate)."""
    item = _find_item(schema, key)
    assert item is not None, f"{key} not found in schema"
    rules = (item.get("visibility") or []) + (item.get("enablement") or [])
    assert _references_capability_field(rules, "is_sp_release"), f"{key} missing is_sp_release gate"


class TestSpuriousOffroadGatesDropped(OpenpilotTestCase):
  def test_disengage_on_accelerator_has_no_offroad_only(self, schema):
    item = _find_item(schema, "DisengageOnAccelerator")
    assert item is not None
    assert "offroad_only" not in _flatten_rule_types(item.get("enablement"))

  def test_dynamic_experimental_has_no_offroad_only(self, schema):
    item = _find_item(schema, "DynamicExperimentalControl")
    assert item is not None
    assert "offroad_only" not in _flatten_rule_types(item.get("enablement"))


class TestNotEngagedReplacement(OpenpilotTestCase):
  @parameterized.expand([
    "AlphaLongitudinalEnabled",
    "ToyotaEnforceStockLongitudinal",
    "ToyotaStopAndGoHack",
  ], names=["key"])
  def test_offroad_only_replaced_with_not_engaged(self, schema, key):
    """These items should use not_engaged, not offroad_only."""
    item = _find_item(schema, key)
    assert item is not None, f"{key} not found"
    rule_types = _flatten_rule_types(item.get("enablement"))
    assert "offroad_only" not in rule_types, f"{key} still uses offroad_only"
    assert "not_engaged" in rule_types, f"{key} missing not_engaged"


class TestGaryPilotRivianSettings(OpenpilotTestCase):
  def test_rivian_vehicle_settings_and_no_redundant_longitudinal(self, schema):
    """Rivian vehicle settings must contain diagnostics and controls customization, but NOT redundant longitudinal toggles."""
    assert "RivianEnforceStockLongitudinal" not in [item.get("key") for item in _walk_items(schema)]
    assert "rivian" in schema.get("vehicle_settings", {})
    rivian_items = schema["vehicle_settings"]["rivian"]["items"]
    rivian_keys = [item.get("key") for item in rivian_items]
    assert "RivianHarnessStatus" in rivian_keys
    assert "RivianStalkUp1Action" in rivian_keys
    assert "RivianSpeedClickStep" in rivian_keys
    assert "RivianSteerOverrideSensitivity" in rivian_keys
    # Option 4 exclusion: longitudinal control toggle must NOT be duplicated under vehicle settings
    assert "AlphaLongitudinalEnabled" not in rivian_keys

  def test_rivian_stalk_up1_action_decoding(self):
    """Verify CarStateExt decodes UP_1 according to RivianStalkUp1Action (0=lkas, 1=cancel, 2=disengage all)."""
    from types import SimpleNamespace
    from opendbc.car import Bus, structs
    from opendbc.sunnypilot.car.rivian.carstate_ext import CarStateExt
    ButtonType = structs.CarState.ButtonEvent.Type

    CP = structs.CarParams.new_message()
    CP.brand = 'rivian'
    CP_SP = structs.CarParamsSP()

    class FakeParams:
      def __init__(self, action):
        self.action = str(action)
      def get(self, key, block=False, return_default=False):
        if key == "RivianStalkUp1Action":
          return self.action
        return None
      def get_bool(self, key, block=False):
        return False

    # Action 0: MADS Toggle -> ButtonType.lkas
    ext0 = CarStateExt(CP, CP_SP)
    ext0.params = FakeParams(0)
    ext0._refresh_params()
    ret = structs.CarState()
    cp = SimpleNamespace(vl={"VDM_AdasSts": {"VDM_UserAdasRequest": 1}})
    ext0.update_stalk_controls(ret, {Bus.pt: cp})
    evs = ext0.update_stalk_controls(ret, {Bus.pt: cp})
    assert any(be.type == ButtonType.lkas and be.pressed for be in evs)

    # Action 1: Cancel ACC -> ButtonType.cancel
    ext1 = CarStateExt(CP, CP_SP)
    ext1.params = FakeParams(1)
    ext1._refresh_params()
    ext1.update_stalk_controls(ret, {Bus.pt: cp})
    evs = ext1.update_stalk_controls(ret, {Bus.pt: cp})
    assert any(be.type == ButtonType.cancel and be.pressed for be in evs)
    assert not any(be.type == ButtonType.lkas for be in evs)

    # Action 2: Disengage All -> ButtonType.cancel + ButtonType.altButton2
    ext2 = CarStateExt(CP, CP_SP)
    ext2.params = FakeParams(2)
    ext2._refresh_params()
    ext2.update_stalk_controls(ret, {Bus.pt: cp})
    evs = ext2.update_stalk_controls(ret, {Bus.pt: cp})
    assert any(be.type == ButtonType.cancel and be.pressed for be in evs)
    assert any(be.type == ButtonType.altButton2 and be.pressed for be in evs)

  def test_rivian_speed_click_step_delta(self):
    """Verify CarStateExt applies 1 mph vs 5 mph click delta based on RivianSpeedClickStep."""
    from types import SimpleNamespace
    from opendbc.car import Bus, structs
    from opendbc.car.common.conversions import Conversions as CV
    from opendbc.sunnypilot.car.rivian.carstate_ext import CarStateExt
    from opendbc.sunnypilot.car.rivian.values import RivianFlagsSP

    CP = structs.CarParams.new_message()
    CP.brand = 'rivian'
    CP.openpilotLongitudinalControl = True
    CP_SP = structs.CarParamsSP()
    CP_SP.flags |= RivianFlagsSP.LONGITUDINAL_HARNESS_UPGRADE

    class FakeParams:
      def __init__(self, step):
        self.step = str(step)
      def get(self, key, block=False, return_default=False):
        if key == "RivianSpeedClickStep":
          return self.step
        return None
      def get_bool(self, key, block=False):
        return False

    # Step 0 (1 mph step)
    ext0 = CarStateExt(CP, CP_SP)
    ext0.params = FakeParams(0)
    ext0._refresh_params()
    ext0.set_speed = 30.0 * CV.MPH_TO_MS

    ret = structs.CarState()
    ret.cruiseState.enabled = True
    ret.vEgoCluster = 30.0 * CV.MPH_TO_MS
    cp_park = SimpleNamespace(vl={"WheelButtons_Fwd": {"RightButton_Scroll": 255, "RightButton_RightClick": 2, "RightButton_LeftClick": 0}})
    cp_adas = SimpleNamespace(vl={"Cluster": {"Cluster_Unit": 1}}) # MPH
    cp_pt = SimpleNamespace(vl={"VDM_AdasSts": {"VDM_UserAdasRequest": 0}})

    ext0.update_longitudinal_upgrade(ret, {Bus.alt: cp_park, Bus.adas: cp_adas, Bus.pt: cp_pt})
    assert abs(ext0.set_speed - (31.0 * CV.MPH_TO_MS)) < 1e-4

    # Step 1 (5 mph step)
    ext1 = CarStateExt(CP, CP_SP)
    ext1.params = FakeParams(1)
    ext1._refresh_params()
    ext1.set_speed = 30.0 * CV.MPH_TO_MS
    ext1.update_longitudinal_upgrade(ret, {Bus.alt: cp_park, Bus.adas: cp_adas, Bus.pt: cp_pt})
    assert abs(ext1.set_speed - (35.0 * CV.MPH_TO_MS)) < 1e-4

  def test_rivian_driver_override_sensitivity(self):
    """Verify steering allowance and pressed threshold match RivianSteerOverrideSensitivity."""
    from opendbc.car import structs
    from opendbc.sunnypilot.car.rivian.carstate_ext import CarStateExt
    from opendbc.car.rivian.values import CarControllerParams
    from opendbc.car.rivian.ext_controller import ExternalController

    CP = structs.CarParams.new_message()
    CP.brand = 'rivian'
    CP_SP = structs.CarParamsSP()

    class FakeParams:
      def __init__(self, sens):
        self.sens = str(sens)
      def get(self, key, block=False, return_default=False):
        if key == "RivianSteerOverrideSensitivity":
          return self.sens
        return None
      def get_bool(self, key, block=False):
        return False

    # Light (0)
    ext_light = CarStateExt(CP, CP_SP)
    ext_light.params = FakeParams(0)
    ext_light._refresh_params()
    assert ext_light.steer_driver_allowance == 75
    assert ext_light.steer_driver_pressed_threshold == 0.75

    # Standard (1)
    ext_std = CarStateExt(CP, CP_SP)
    ext_std.params = FakeParams(1)
    ext_std._refresh_params()
    assert ext_std.steer_driver_allowance == 100
    assert ext_std.steer_driver_pressed_threshold == 1.00

    # Firm (2)
    ext_firm = CarStateExt(CP, CP_SP)
    ext_firm.params = FakeParams(2)
    ext_firm._refresh_params()
    assert ext_firm.steer_driver_allowance == 100  # Capped at Panda safety limit of 100
    assert ext_firm.steer_driver_pressed_threshold == 1.30

    # Verify ExternalController uses CS.steer_driver_allowance and clamps to Panda safety limit (100)
    class MockCS:
      def __init__(self, allowance):
        self.out = structs.CarState()
        self.out.vEgoRaw = 20.0
        self.out.steeringTorque = 50.0
        self.steer_driver_allowance = allowance

    erc = ExternalController()
    cs_mock = MockCS(75)
    erc.torque_active = True
    actuators = structs.CarControl.Actuators()
    actuators.torque = 0.5
    erc._update_torque(cs_mock, actuators)
    assert erc.ccp.STEER_DRIVER_ALLOWANCE == 75

    # If CS reports higher than Panda limit, verify it clamps to 100
    cs_firm = MockCS(130)
    erc._update_torque(cs_firm, actuators)
    assert erc.ccp.STEER_DRIVER_ALLOWANCE == 100

  def test_rivian_stalk_sweep_up1_to_up2_no_phantom_release(self):
    """Sweeping stalk rapidly from neutral through UP_1 to UP_2 must NOT emit phantom release for UP_1."""
    from opendbc.car import structs
    from opendbc.sunnypilot.car.rivian.carstate_ext import CarStateExt

    CP = structs.CarParams.new_message()
    CP.brand = "rivian"
    CP_SP = structs.CarParamsSP()
    ext = CarStateExt(CP, CP_SP)
    # Configure Action 2 ("Disengage All")
    ext.stalk_up1_action = 2

    class MockParser:
      def __init__(self, val):
        self.vl = {"VDM_AdasSts": {"VDM_UserAdasRequest": val}}

    ret = structs.CarState.new_message()

    # Frame 1: Stalk hits UP_1 detent (vdm = 1)
    parsers_1 = {"pt": MockParser(1)}
    events_1 = ext.update_stalk_controls(ret, parsers_1)
    # In frame 1, UP_1 is pending (lookahead to see if it sweeps to UP_2)
    assert len(events_1) == 0
    assert ext._lkas_pending is True
    assert ext._up1_pressed is False

    # Frame 2: Stalk advances to UP_2 detent (vdm = 2)
    parsers_2 = {"pt": MockParser(2)}
    events_2 = ext.update_stalk_controls(ret, parsers_2)
    # Must emit ONLY altButton2 (pressed=True) for UP_2
    # Must NOT emit cancel(pressed=False) or altButton2(pressed=False)
    assert ext._lkas_pending is False
    assert ext._up1_pressed is False
    assert len(events_2) == 1
    assert events_2[0].type == structs.CarState.ButtonEvent.Type.altButton2
    assert events_2[0].pressed is True

    # Frame 3: Stalk held at UP_2 detent (vdm = 2)
    parsers_3 = {"pt": MockParser(2)}
    events_3 = ext.update_stalk_controls(ret, parsers_3)
    assert len(events_3) == 0

    # Frame 4: Stalk released back to neutral (vdm = 0)
    parsers_4 = {"pt": MockParser(0)}
    events_4 = ext.update_stalk_controls(ret, parsers_4)
    assert len(events_4) == 1
    assert events_4[0].type == structs.CarState.ButtonEvent.Type.altButton2
    assert events_4[0].pressed is False

  def test_rivian_stalk_up1_normal_click_and_release(self):
    """Normal UP_1 press and release emits press followed by release."""
    from opendbc.car import structs
    from opendbc.sunnypilot.car.rivian.carstate_ext import CarStateExt

    CP = structs.CarParams.new_message()
    CP.brand = "rivian"
    CP_SP = structs.CarParamsSP()
    ext = CarStateExt(CP, CP_SP)
    ext.stalk_up1_action = 2

    class MockParser:
      def __init__(self, val):
        self.vl = {"VDM_AdasSts": {"VDM_UserAdasRequest": val}}

    ret = structs.CarState.new_message()

    # Frame 1: vdm = 1
    ext.update_stalk_controls(ret, {"pt": MockParser(1)})
    # Frame 2: vdm = 1 (held at UP_1 detent, lookahead resolves)
    ev2 = ext.update_stalk_controls(ret, {"pt": MockParser(1)})
    assert len(ev2) == 2  # cancel and altButton2 for Action 2
    assert all(e.pressed for e in ev2)
    assert ext._up1_pressed is True

    # Frame 3: vdm = 0 (released)
    ev3 = ext.update_stalk_controls(ret, {"pt": MockParser(0)})
    assert len(ev3) == 2
    assert all(not e.pressed for e in ev3)
    assert ext._up1_pressed is False

  def test_virtual_params_cross_process_cache_invalidation(self):
    """Virtual param cache must invalidate when file on disk is modified by another process."""
    import tempfile
    from openpilot.common.params import Params, _virtual_cache
    import time

    with tempfile.TemporaryDirectory() as tmp_dir:
      params = Params(tmp_dir)
      params.put("RivianStalkUp1Action", 1)
      assert params.get("RivianStalkUp1Action") == 1

      # Simulate another process directly updating the file on disk
      target = params._virtual_param_path(b"RivianStalkUp1Action")
      time.sleep(0.01)
      target.write_bytes(b"2")
      cache_key = (params.get_param_path(), b"RivianStalkUp1Action")
      mtime, val, ctime = _virtual_cache[cache_key]
      _virtual_cache[cache_key] = (mtime, val, ctime - 1.0)  # simulate past TTL

      # Next get() must detect disk modification and return new value
      assert params.get("RivianStalkUp1Action") == 2



  def test_longitudinal_control_in_toggles_not_developer(self, schema):
    """GaryPilot longitudinal control must reside in Toggles panel, not Developer."""
    toggles_panel = next((p for p in schema.get("panels", []) if p.get("id") == "toggles"), None)
    assert toggles_panel is not None, "Toggles panel not found"
    toggles_keys = [item.get("key") for section in toggles_panel.get("sections", []) for item in section.get("items", [])]
    assert "AlphaLongitudinalEnabled" in toggles_keys, "AlphaLongitudinalEnabled not found in Toggles panel"

    dev_panel = next((p for p in schema.get("panels", []) if p.get("id") == "developer"), None)
    assert dev_panel is not None, "Developer panel not found"
    dev_keys = [item.get("key") for section in dev_panel.get("sections", []) for item in section.get("items", [])]
    assert "AlphaLongitudinalEnabled" not in dev_keys, "AlphaLongitudinalEnabled still present in Developer panel"

  def test_alpha_longitudinal_warning_mentions_rivian(self, schema):
    """AlphaLongitudinalEnabled description must accurately reflect Rivian XNOR XTREME AEB retention."""
    item = _find_item(schema, "AlphaLongitudinalEnabled")
    assert item is not None, "AlphaLongitudinalEnabled not found"
    desc = item.get("description", "")
    assert "Rivian R1 with XNOR XTREME hardware" in desc
    assert "factory Automatic Emergency Braking (AEB) remains fully active" in desc

  def test_rivian_interface_hardware_check_gating(self):
    """Rivian longitudinal control must be strictly gated by hardware check (0x131a)."""
    from opendbc.car.rivian.values import CAR
    from opendbc.car.rivian.interface import CarInterface

    # Case 1: No longitudinal hardware upgrade (0x131a missing), toggle disabled (default)
    fp_no_hw = {0: {0x321: 8}, 1: {0x1310: 8}, 2: {}}
    cp1 = CarInterface.get_params(CAR.RIVIAN_R1, fp_no_hw, [], alpha_long=False, is_release=False, docs=False)
    CarInterface.get_params_sp(cp1, CAR.RIVIAN_R1, fp_no_hw, [], alpha_long=False, is_release_sp=False, docs=False)
    assert not cp1.alphaLongitudinalAvailable
    assert not cp1.openpilotLongitudinalControl

    # Case 2: No longitudinal hardware upgrade (0x131a missing), toggle enabled
    cp2 = CarInterface.get_params(CAR.RIVIAN_R1, fp_no_hw, [], alpha_long=True, is_release=False, docs=False)
    CarInterface.get_params_sp(cp2, CAR.RIVIAN_R1, fp_no_hw, [], alpha_long=True, is_release_sp=False, docs=False)
    assert not cp2.alphaLongitudinalAvailable
    assert not cp2.openpilotLongitudinalControl

    # Case 3: Longitudinal hardware upgrade present (0x131a on bus 1), toggle disabled (default state)
    fp_with_hw = {0: {0x321: 8}, 1: {0x1310: 8, 0x131a: 8}, 2: {}}
    cp3 = CarInterface.get_params(CAR.RIVIAN_R1, fp_with_hw, [], alpha_long=False, is_release=False, docs=False)
    CarInterface.get_params_sp(cp3, CAR.RIVIAN_R1, fp_with_hw, [], alpha_long=False, is_release_sp=False, docs=False)
    assert cp3.alphaLongitudinalAvailable
    assert not cp3.openpilotLongitudinalControl

    # Case 4: Longitudinal hardware upgrade present (0x131a on bus 1), toggle enabled
    cp4 = CarInterface.get_params(CAR.RIVIAN_R1, fp_with_hw, [], alpha_long=True, is_release=False, docs=False)
    CarInterface.get_params_sp(cp4, CAR.RIVIAN_R1, fp_with_hw, [], alpha_long=True, is_release_sp=False, docs=False)
    assert cp4.alphaLongitudinalAvailable
    assert cp4.openpilotLongitudinalControl

