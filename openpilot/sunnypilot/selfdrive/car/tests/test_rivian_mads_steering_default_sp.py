#!/usr/bin/env python3
"""Rivian MadsSteeringMode: the default is REMAIN_ACTIVE (steer through braking), and CarStateExt never writes it.

Fork decision (deviates from AdventurePilot, which seeds DISENGAGE on a first install): lateral should keep steering
through a braking turn, and pushing the stalk to UP_2 is the reliable full disengage. So the Rivian default is simply
the stock param default (REMAIN_ACTIVE, "0" in params_keys.h), and whatever the user picks in settings always wins.

Two layers of tests:
  * FakeParams records every write, so "never writes" can be asserted for each install state.
  * The real Params class (temp store) proves the API and types, which a fake cannot: an earlier revision called
    Params.put_int(), which does not exist, and would have crashed card at startup.
"""
import openpilot.common.params as params_module
from opendbc.car import structs
from opendbc.sunnypilot.car.rivian import carstate_ext
from opendbc.sunnypilot.car.rivian.carstate_ext import CarStateExt
from openpilot.sunnypilot.mads.helpers import MadsSteeringModeOnBrake

REMAIN_ACTIVE = MadsSteeringModeOnBrake.REMAIN_ACTIVE
PAUSE = MadsSteeringModeOnBrake.PAUSE
DISENGAGE = MadsSteeringModeOnBrake.DISENGAGE
_REAL_PARAMS = params_module.Params  # captured before any test monkeypatches it


class FakeParams:
  """Stand-in for Params, recording writes so the "does not write" cases can be asserted.

  `steering_mode=None` means the key is unset, in which case get(..., return_default=True) returns the stock default.
  """

  def __init__(self, car_params_persistent, steering_mode):
    self._values = {"RivianResumeEnabled": False}
    if steering_mode is not None:
      self._values["MadsSteeringMode"] = steering_mode
    if car_params_persistent is not None:
      self._values["CarParamsPersistent"] = car_params_persistent
    self.writes = []

  def get(self, key, block=False, return_default=False):
    if key == "MadsSteeringMode" and key not in self._values and return_default:
      return REMAIN_ACTIVE  # params_keys.h default "0"
    return self._values.get(key)

  def get_bool(self, key, block=False):
    return bool(self._values.get(key, False))

  def put(self, key, value, block=False):
    self.writes.append((key, value))
    self._values[key] = value

  def put_bool(self, key, value, block=False):
    self.writes.append((key, bool(value)))
    self._values[key] = bool(value)


def _construct(monkeypatch, car_params_persistent, steering_mode):
  """Build one CarStateExt against a fake Params. Returns that fake, with the ext attached."""
  fake = FakeParams(car_params_persistent, steering_mode)
  monkeypatch.setattr(params_module, "Params", lambda: fake)
  monkeypatch.setattr(carstate_ext, "Params", lambda: fake, raising=False)

  CP = structs.CarParams.new_message()
  CP.brand = 'rivian'
  ext = CarStateExt.__new__(CarStateExt)
  CarStateExt.__init__(ext, CP, structs.CarParamsSP())
  fake.ext = ext
  return fake


class TestRivianMadsSteeringDefault:
  def test_fresh_install_unset_resolves_to_remain_active(self, monkeypatch):
    # never driven, key unset: the stock default applies and lateral steers through braking
    fake = _construct(monkeypatch, None, None)
    assert fake.ext.steering_mode_on_brake == REMAIN_ACTIVE

  def test_never_writes_the_mode(self, monkeypatch):
    for cpp in (None, b"cp"):
      for mode in (None, REMAIN_ACTIVE, PAUSE, DISENGAGE):
        fake = _construct(monkeypatch, cpp, mode)
        assert fake.writes == [], f"CarParamsPersistent={cpp!r} MadsSteeringMode={mode}"

  def test_user_choice_is_honored(self, monkeypatch):
    for cpp in (None, b"cp"):
      for mode in (REMAIN_ACTIVE, PAUSE, DISENGAGE):
        fake = _construct(monkeypatch, cpp, mode)
        assert fake.ext.steering_mode_on_brake == mode, f"CarParamsPersistent={cpp!r} MadsSteeringMode={mode}"


def _construct_real(monkeypatch, tmp_path, steering_mode=None, car_params_persistent=None):
  """Build one CarStateExt against the REAL Params, backed by a throwaway directory."""
  real_params = _REAL_PARAMS
  path = str(tmp_path / "params")
  store = real_params(path)
  if car_params_persistent is not None:
    store.put("CarParamsPersistent", car_params_persistent, block=True)  # non-blocking put is async
  if steering_mode is not None:
    store.put("MadsSteeringMode", steering_mode, block=True)
  monkeypatch.setattr(params_module, "Params", lambda: real_params(path))
  monkeypatch.setattr(carstate_ext, "Params", lambda: real_params(path), raising=False)

  CP = structs.CarParams.new_message()
  CP.brand = 'rivian'
  ext = CarStateExt.__new__(CarStateExt)
  CarStateExt.__init__(ext, CP, structs.CarParamsSP())
  return ext, real_params(path)


class TestRivianMadsSteeringDefaultRealParams:
  def test_fresh_install_is_remain_active_and_untouched(self, monkeypatch, tmp_path):
    ext, store = _construct_real(monkeypatch, tmp_path)
    assert ext.steering_mode_on_brake == REMAIN_ACTIVE
    assert store.get("MadsSteeringMode") is None  # still unset: nothing was written

  def test_existing_choice_is_honored(self, monkeypatch, tmp_path):
    for mode in (PAUSE, DISENGAGE):
      ext, store = _construct_real(monkeypatch, tmp_path / str(mode), steering_mode=mode, car_params_persistent=b"cp")
      assert ext.steering_mode_on_brake == mode
      assert store.get("MadsSteeringMode") == mode
