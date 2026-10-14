#!/usr/bin/env python3
"""INTEGRATION_PLAN B5b (Python side) and Rivian steer-through-braking.

B5b: ACC on, steering mode REMAIN_ACTIVE or PAUSE, driver taps the stalk to UP_1.
  * The car cancels stock ACC natively (not modelled here; it is the car).
  * CarStateExt emits ButtonType.lkas after its one-frame UP_2 lookahead (DISENGAGE mode suppresses it).
  * MADS sees lkas while selfdrive is engaged -> manualSteeringRequired (ET.USER_DISABLE) -> State.disabled.
So the result is "ACC and steering both off". The panda half (panda ignores the press, then revokes lateral via the
heartbeat check, with every not-steering frame accepted) is test_rivian.py::test_b5b_up_1_with_acc_on_remain_active_or_pause.

Steer-through-braking: in REMAIN_ACTIVE (the Rivian default on this fork) braking must not emit any lateral disable
from the Rivian car-specific layer, and the MADS state machine must stay enabled.
"""
from types import SimpleNamespace

import openpilot.common.params as params_module
from openpilot.common.parameterized import parameterized

from opendbc.car import Bus, structs
from opendbc.sunnypilot.car.rivian.carstate_ext import CarStateExt
from openpilot.cereal import custom, log
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived.events import Events
from openpilot.sunnypilot.mads.helpers import MadsSteeringModeOnBrake
from openpilot.sunnypilot.mads.tests.test_mads_steering_mode import make_mads, run_frames
from openpilot.sunnypilot.selfdrive.car.car_specific import CarSpecificEventsSP

ButtonType = structs.CarState.ButtonEvent.Type
EventName = log.OnroadEvent.EventName
EventNameSP = custom.OnroadEventSP.EventName
State = custom.ModularAssistiveDrivingSystem.ModularAssistiveDrivingSystemState

REMAIN_ACTIVE = MadsSteeringModeOnBrake.REMAIN_ACTIVE
PAUSE = MadsSteeringModeOnBrake.PAUSE
DISENGAGE = MadsSteeringModeOnBrake.DISENGAGE

IDLE, UP_1, UP_2 = 0, 1, 2
LATERAL_DISABLES = (EventNameSP.lkasDisable, EventNameSP.silentLkasDisable, EventNameSP.manualSteeringRequired)


class _FakeParams:
  def __init__(self, steering_mode):
    self._mode = steering_mode

  def get(self, key, block=False, return_default=False):
    return self._mode if key == "MadsSteeringMode" else None

  def get_bool(self, key, block=False):
    return False


def _rivian_cp():
  CP = structs.CarParams.new_message()
  CP.brand = 'rivian'
  return CP


def _stalk_events(monkeypatch, steering_mode, frames, cruise_enabled=True):
  """Run VDM_UserAdasRequest frames through CarStateExt.update_stalk_controls. Returns the button events per frame."""
  monkeypatch.setattr(params_module, "Params", lambda: _FakeParams(steering_mode))
  ext = CarStateExt(_rivian_cp(), structs.CarParamsSP())
  assert ext.steering_mode_on_brake == steering_mode

  out = []
  for vdm in frames:
    ret = structs.CarState()
    ret.cruiseState.enabled = cruise_enabled
    cp = SimpleNamespace(vl={"VDM_AdasSts": {"VDM_UserAdasRequest": vdm}})
    out.append([(be.type, be.pressed) for be in ext.update_stalk_controls(ret, {Bus.pt: cp})])
  return out


class TestB5bStalkDecoding(OpenpilotTestCase):
  @parameterized.expand([(REMAIN_ACTIVE,), (PAUSE,)], names=["mode"])
  def test_up_1_with_acc_on_emits_lkas_after_lookahead(self, monkeypatch, mode):
    events = _stalk_events(monkeypatch, mode, [IDLE, UP_1, UP_1, IDLE])
    # frame of UP_1: held back one frame in case this is a sweep to UP_2; next frame: press; back to idle: release
    assert events == [[], [], [(ButtonType.lkas, True)], [(ButtonType.lkas, False)]]

  def test_disengage_mode_suppresses_lkas_with_acc_on(self, monkeypatch):
    # DISENGAGE + ACC on: the press only cancels ACC natively, MADS must not toggle
    events = _stalk_events(monkeypatch, DISENGAGE, [IDLE, UP_1, UP_1, IDLE])
    assert all((ButtonType.lkas, True) not in f for f in events)

  @parameterized.expand([(REMAIN_ACTIVE,), (PAUSE,), (DISENGAGE,)], names=["mode"])
  def test_sweep_through_to_up_2_never_emits_lkas(self, monkeypatch, mode):
    # B3 under B5b conditions: UP_1 transit on the way to UP_2 must not toggle MADS
    events = _stalk_events(monkeypatch, mode, [IDLE, UP_1, UP_2, UP_2, IDLE])
    assert all((ButtonType.lkas, True) not in f for f in events)
    assert (ButtonType.altButton2, True) in events[2]


def _lkas_press_cs():
  cs = structs.CarState()
  cs.cruiseState.available = True
  cs.cruiseState.enabled = True
  cs.vEgo = 15.0
  cs.buttonEvents = [structs.CarState.ButtonEvent(pressed=True, type=ButtonType.lkas)]
  return cs


def _make_rivian_mads(mocker, mode):
  mads, sd = make_mads(mocker, mode)
  mads.CP.brand = 'rivian'
  mads.allow_always = False
  mads.no_main_cruise = True
  mads.state_machine.state = State.enabled
  mads.enabled = True
  mads.active = True
  sd.enabled = True  # stock ACC engaged: selfdrive (longitudinal) is enabled
  return mads, sd


class TestB5bMadsResponse(OpenpilotTestCase):
  @parameterized.expand([(REMAIN_ACTIVE,), (PAUSE,)], names=["mode"])
  def test_lkas_with_acc_on_requires_manual_steering(self, mocker, mode):
    mads, sd = _make_rivian_mads(mocker, mode)
    mads.update_events(_lkas_press_cs())
    assert sd.events_sp.has(EventNameSP.manualSteeringRequired)
    assert not sd.events_sp.has(EventNameSP.lkasEnable)

  @parameterized.expand([(REMAIN_ACTIVE,), (PAUSE,)], names=["mode"])
  def test_lkas_with_acc_on_ends_disabled_not_paused(self, mocker, mode):
    # disabled, not paused: paused would silently re-arm lateral, which the panda has already revoked
    mads, sd = _make_rivian_mads(mocker, mode)
    run_frames(mads, sd, _lkas_press_cs())
    assert mads.state_machine.state == State.disabled
    assert not mads.enabled


def _car_specific_events(monkeypatch, mode, brake_pressed):
  monkeypatch.setattr(params_module, "Params", lambda: _FakeParams(mode))
  ev = CarSpecificEventsSP(_rivian_cp(), structs.CarParamsSP())
  CS = structs.CarState.new_message()
  CS.gearShifter = structs.CarState.GearShifter.drive
  CS.brakePressed = brake_pressed
  CS.vEgo = 15.0
  return ev.update(CS, Events())


class TestRivianSteerThroughBraking:
  def test_remain_active_brake_emits_no_lateral_disable(self, monkeypatch):
    events = _car_specific_events(monkeypatch, REMAIN_ACTIVE, brake_pressed=True)
    assert not any(events.has(e) for e in LATERAL_DISABLES)

  def test_pause_brake_pauses(self, monkeypatch):
    # contrast: PAUSE mode does pause lateral on the brake
    events = _car_specific_events(monkeypatch, PAUSE, brake_pressed=True)
    assert events.has(EventNameSP.silentLkasDisable)


class TestRivianSteerThroughBrakingMads(OpenpilotTestCase):
  def test_remain_active_brake_with_acc_cancel_keeps_lateral(self, mocker):
    # braking cancels stock ACC (pcmDisable); in REMAIN_ACTIVE MADS must keep steering through the turn
    mads, sd = _make_rivian_mads(mocker, REMAIN_ACTIVE)
    cs = structs.CarState()
    cs.cruiseState.available = True
    cs.brakePressed = True
    cs.vEgo = 15.0
    sd.events.add(EventName.pedalPressed)
    sd.events.add(EventName.pcmDisable)
    run_frames(mads, sd, cs)
    assert mads.state_machine.state == State.enabled


class TestRivianDriverOverrideDisengage(OpenpilotTestCase):
  def test_steer_disengage_event_disables_mads(self, mocker):
    # Rivian EPAS error 12 (EPAS_Hands_On_Detn_Err) -> ret.steeringDisengage -> EventName.steerDisengage (ET.USER_DISABLE)
    mads, sd = _make_rivian_mads(mocker, REMAIN_ACTIVE)
    cs = structs.CarState()
    cs.steeringDisengage = True
    sd.events.add(EventName.steerDisengage)
    run_frames(mads, sd, cs)
    assert mads.state_machine.state == State.disabled
    assert not mads.enabled

  def test_pause_mode_brake_plus_explicit_disable_ends_disabled_not_paused(self, monkeypatch, mocker):
    # Regression test: in PAUSE mode while holding the brake pedal, any explicit disable
    # (UP_2, Reverse/Park gear shift, or steerDisengage) must NOT be shadowed by silentLkasDisable
    # into State.paused (which would uncommandedly re-engage lateral steering on brake release).
    monkeypatch.setattr(params_module, "Params", lambda: _FakeParams(PAUSE))

    # 1. UP_2 while braking in PAUSE mode -> emits lkasDisable (for 2 frames), NOT silentLkasDisable
    ev = CarSpecificEventsSP(_rivian_cp(), structs.CarParamsSP())
    cs_up2 = structs.CarState.new_message()
    cs_up2.gearShifter = structs.CarState.GearShifter.drive
    cs_up2.brakePressed = True
    cs_up2.buttonEvents = [structs.CarState.ButtonEvent(pressed=True, type=ButtonType.altButton2)]
    events_f1 = ev.update(cs_up2, Events())
    assert events_f1.has(EventNameSP.lkasDisable)
    assert not events_f1.has(EventNameSP.silentLkasDisable)

    # Frame 2 (held at UP_2): two-frame lkasDisable ensures transition out of paused completes
    cs_up2_held = structs.CarState.new_message()
    cs_up2_held.gearShifter = structs.CarState.GearShifter.drive
    cs_up2_held.brakePressed = True
    events_f2 = ev.update(cs_up2_held, Events())
    assert events_f2.has(EventNameSP.lkasDisable)
    assert not events_f2.has(EventNameSP.silentLkasDisable)

    # 2. Shifting to Reverse while holding brake in PAUSE mode -> emits lkasDisable, NOT silentLkasDisable
    ev_gear = CarSpecificEventsSP(_rivian_cp(), structs.CarParamsSP())
    cs_drive = structs.CarState.new_message()
    cs_drive.gearShifter = structs.CarState.GearShifter.drive
    cs_drive.brakePressed = True
    ev_gear.update(cs_drive, Events())

    cs_rev = structs.CarState.new_message()
    cs_rev.gearShifter = structs.CarState.GearShifter.reverse
    cs_rev.brakePressed = True
    events_rev1 = ev_gear.update(cs_rev, Events())
    events_rev2 = ev_gear.update(cs_rev, Events())
    assert events_rev1.has(EventNameSP.lkasDisable)
    assert not events_rev1.has(EventNameSP.silentLkasDisable)
    assert events_rev2.has(EventNameSP.lkasDisable)
    assert not events_rev2.has(EventNameSP.silentLkasDisable)

    # 3. Verify full MADS state machine transitions from paused -> disabled and stays disabled on brake release
    mads, sd = _make_rivian_mads(mocker, PAUSE)
    # First pause via brake
    cs_brake = structs.CarState()
    cs_brake.cruiseState.available = True
    cs_brake.brakePressed = True
    sd.events_sp.add(EventNameSP.silentLkasDisable)
    run_frames(mads, sd, cs_brake)
    assert mads.state_machine.state == State.paused

    # Now explicit disable (e.g., UP_2 / Reverse / steerDisengage) while brake is still held
    sd.events_sp.clear()
    sd.events_sp.add(EventNameSP.lkasDisable)
    run_frames(mads, sd, cs_brake, n=2)
    assert mads.state_machine.state == State.disabled

    # Release brake: MADS must remain disabled (never auto-resume)
    sd.events_sp.clear()
    cs_release = structs.CarState()
    cs_release.cruiseState.available = True
    cs_release.brakePressed = False
    run_frames(mads, sd, cs_release, n=2)
    assert mads.state_machine.state == State.disabled
    assert not mads.enabled
