#!/usr/bin/env python3
"""Tests for GaryPilot vehicle safety gate and onboarding verification.

GaryPilot is strictly built and configured for Rivian R1T & R1S vehicles with
the XNOR angle harness.
1. Any non-Rivian brand/fingerprint must be locked to passive dashcam mode with
   SafetyModel.noOutput.
2. Rivian vehicles allow controls when openpilot toggle is enabled.
3. terms_version_sp is set to '2.0' to force vehicle verification onboarding.
"""
from opendbc.car import structs
from openpilot.common.version import terms_version_sp
from openpilot.selfdrive.car.helpers import enforce_vehicle_safety_gate


class TestRivianVehicleGate:
  def test_terms_version_sp_bumped(self):
    """terms_version_sp must be '2.0' so fresh boots require Rivian verification."""
    assert terms_version_sp == "2.0"

  def test_non_rivian_vehicles_locked_out(self):
    """Non-Rivian vehicles (Toyota, Honda, Tesla, etc.) must have actuation strictly disabled."""
    non_rivian_brands = ["toyota", "honda", "hyundai", "ford", "tesla", "subaru", "chrysler", "volkswagen", "mock"]
    fake_cc = object()

    for brand in non_rivian_brands:
      CP = structs.CarParams.new_message()
      CP.brand = brand
      CP.carFingerprint = f"{brand.upper()}_TEST"
      CP.dashcamOnly = False
      CP.passive = False

      # Initial dummy safety config
      cfg = structs.CarParams.SafetyConfig()
      cfg.safetyModel = structs.CarParams.SafetyModel.silent
      CP.safetyConfigs = [cfg]

      controller_available = enforce_vehicle_safety_gate(CP, fake_cc, openpilot_enabled_toggle=True)

      assert not controller_available, f"controller_available should be False for {brand}"
      assert CP.dashcamOnly is True, f"dashcamOnly should be True for {brand}"
      assert CP.passive is True, f"passive should be True for {brand}"
      assert len(CP.safetyConfigs) == 1, f"safetyConfigs length should be 1 for {brand}"
      assert CP.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput, (
        f"safetyModel should be noOutput for {brand}"
      )

  def test_rivian_vehicle_allowed_controls(self):
    """Rivian vehicles must allow actuation when openpilot toggle is enabled."""
    fake_cc = object()
    CP = structs.CarParams.new_message()
    CP.brand = "rivian"
    CP.carFingerprint = "RIVIAN_R1"
    CP.dashcamOnly = False
    CP.passive = False

    cfg = structs.CarParams.SafetyConfig()
    cfg.safetyModel = structs.CarParams.SafetyModel.rivian
    CP.safetyConfigs = [cfg]

    controller_available = enforce_vehicle_safety_gate(CP, fake_cc, openpilot_enabled_toggle=True)

    assert controller_available is True
    assert CP.dashcamOnly is False
    assert CP.passive is False
    assert len(CP.safetyConfigs) == 1
    assert CP.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.rivian

  def test_rivian_vehicle_disabled_when_toggle_off(self):
    """If user disables openpilot toggle, Rivian must still be passive."""
    fake_cc = object()
    CP = structs.CarParams.new_message()
    CP.brand = "rivian"
    CP.carFingerprint = "RIVIAN_R1"
    CP.dashcamOnly = False
    CP.passive = False

    controller_available = enforce_vehicle_safety_gate(CP, fake_cc, openpilot_enabled_toggle=False)

    assert controller_available is False
    assert CP.passive is True
    assert CP.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput

  def test_rivian_vehicle_user_dashcam_toggle(self):
    """If user enables dashcam-only toggle, Rivian must be passive with noOutput."""
    fake_cc = object()
    CP = structs.CarParams.new_message()
    CP.brand = "rivian"
    CP.carFingerprint = "RIVIAN_R1"
    CP.dashcamOnly = True
    CP.passive = False

    controller_available = enforce_vehicle_safety_gate(CP, fake_cc, openpilot_enabled_toggle=True)

    assert controller_available is False
    assert CP.passive is True
    assert CP.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput
