"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import math
from enum import StrEnum

from opendbc.car import Bus, structs
from opendbc.can.parser import CANParser
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.rivian.values import DBC
from opendbc.sunnypilot.car.rivian.values import RivianFlagsSP

ButtonType = structs.CarState.ButtonEvent.Type

MAX_SET_SPEED = 85 * CV.MPH_TO_MS
MIN_SET_SPEED = 20 * CV.MPH_TO_MS

class CarStateExt:
  def __init__(self, CP: structs.CarParams, CP_SP: structs.CarParamsSP):
    self.CP = CP
    self.CP_SP = CP_SP

    self.set_speed = 10
    self.increase_button = False
    self.decrease_button = False
    self.distance_button = 0
    self.increase_counter = 0
    self.decrease_counter = 0

    self.vdm_user_adas_request = 0
    self._lkas_pending = False

    # lazy openpilot imports: opendbc must stay importable standalone (safety test suite)
    from openpilot.common.params import Params
    from openpilot.sunnypilot.mads.helpers import read_steering_mode_param
    self.params = Params()
    # Fork decision (deviates from AdventurePilot, which seeds DISENGAGE on a first install): the Rivian default is the
    # stock MadsSteeringMode default, REMAIN_ACTIVE, so lateral steers through braking in turns. Pushing the stalk to
    # UP_2 is the reliable full disengage. Never write this param here: the user's choice in settings always wins.
    self.steering_mode_on_brake = read_steering_mode_param(CP, CP_SP, self.params)
    self.auto_resume = self.params.get_bool("RivianStopAndGoAutoResume")
    self.param_check_counter = 0

  def update_stalk_controls(self, ret: structs.CarState, can_parsers: dict[StrEnum, CANParser]) -> list:
    cp = can_parsers[Bus.pt]
    vdm = int(cp.vl["VDM_AdasSts"]["VDM_UserAdasRequest"])

    button_events = []

    # Signal UP_2 state via altButton2 so car_specific.py can fire lkasDisable
    # and suppress pcmEnable. UP_2 disengages ACC; without this, MADS can persist
    # in Mode B (lateral only) after ACC cancels.
    if vdm == 2 and self.vdm_user_adas_request != 2:
      button_events.append(structs.CarState.ButtonEvent(pressed=True, type=ButtonType.altButton2))
    elif vdm != 2 and self.vdm_user_adas_request == 2:
      button_events.append(structs.CarState.ButtonEvent(pressed=False, type=ButtonType.altButton2))

    # Signal UP_1 state via lkas button to toggle MADS
    # 1-frame lookahead to prevent UP_1 flashing during sweep to UP_2
    if self._lkas_pending:
      if vdm != 2:
        button_events.append(structs.CarState.ButtonEvent(pressed=True, type=ButtonType.lkas))
      self._lkas_pending = False

    if vdm == 1 and self.vdm_user_adas_request not in (1, 2):
      # DISENGAGE mode (value 2).
      if not (self.steering_mode_on_brake == 2 and ret.cruiseState.enabled):
        self._lkas_pending = True
    elif vdm != 1 and self.vdm_user_adas_request == 1:
      button_events.append(structs.CarState.ButtonEvent(pressed=False, type=ButtonType.lkas))

    self.vdm_user_adas_request = vdm
    return button_events

  def update_longitudinal_upgrade(self, ret: structs.CarState, can_parsers: dict[StrEnum, CANParser]) -> list:
    cp_park = can_parsers[Bus.alt]
    cp_adas = can_parsers[Bus.adas]
    cp = can_parsers[Bus.pt]

    button_events = []

    prev_increase_button = self.increase_button
    prev_decrease_button = self.decrease_button

    if self.CP.openpilotLongitudinalControl:
      # distance scroll wheel
      right_scroll = cp_park.vl["WheelButtons_Fwd"]["RightButton_Scroll"]
      if right_scroll != 255:
        if self.distance_button != right_scroll:
          button_events.append(structs.CarState.ButtonEvent(pressed=False, type=ButtonType.gapAdjustCruise))
        self.distance_button = right_scroll

      # button logic for set-speed
      self.increase_button = cp_park.vl["WheelButtons_Fwd"]["RightButton_RightClick"] == 2
      self.decrease_button = cp_park.vl["WheelButtons_Fwd"]["RightButton_LeftClick"] == 2

      self.increase_counter = self.increase_counter + 1 if self.increase_button else 0
      self.decrease_counter = self.decrease_counter + 1 if self.decrease_button else 0

      metric = cp_adas.vl["Cluster"]["Cluster_Unit"] == 0
      conversion = CV.KPH_TO_MS if metric else CV.MPH_TO_MS
      long_press_step = 10.0 if metric else 5.0
      set_speed_converted = self.set_speed * (CV.MS_TO_KPH if metric else CV.MS_TO_MPH)

      if self.increase_button:
        if self.increase_counter % 66 == 0:
          self.set_speed = (int(math.ceil((set_speed_converted + 1) / long_press_step)) * long_press_step) * conversion
        elif not prev_increase_button:
          self.set_speed += conversion

      if self.decrease_button:
        if self.decrease_counter % 66 == 0:
          self.set_speed = (int(math.floor((set_speed_converted - 1) / long_press_step)) * long_press_step) * conversion
        elif not prev_decrease_button:
          self.set_speed -= conversion

      if not ret.cruiseState.enabled:
        self.set_speed = ret.vEgoCluster

      # VDM_UserAdasRequest: 0=IDLE, 1=UP_1, 2=UP_2, 3=DOWN_1, 4=DOWN_2
      stalk_down = int(cp.vl["VDM_AdasSts"]["VDM_UserAdasRequest"]) in (3, 4)
      if stalk_down:
        # Mimic Rivian ACC: stalk down sets speed to current speed (never decreases)
        self.set_speed = max(self.set_speed, ret.vEgoCluster)

      self.set_speed = max(MIN_SET_SPEED, min(self.set_speed, MAX_SET_SPEED))
      ret.cruiseState.speed = self.set_speed

      self.param_check_counter += 1
      if self.param_check_counter % 100 == 0:
        self.auto_resume = self.params.get_bool("RivianStopAndGoAutoResume")

      if self.auto_resume and ret.standstill:
        ret.cruiseState.standstill = False

    if self.CP.enableBsm:
      ret.leftBlindspot = cp_park.vl["BSM_BlindSpotIndicator_Fwd"]["BSM_BlindSpotIndicator_Left"] != 0
      ret.rightBlindspot = cp_park.vl["BSM_BlindSpotIndicator_Fwd"]["BSM_BlindSpotIndicator_Right"] != 0

    return button_events

  def update(self, ret: structs.CarState, can_parsers: dict[StrEnum, CANParser]) -> None:
    button_events = []
    if self.CP_SP.flags & RivianFlagsSP.LONGITUDINAL_HARNESS_UPGRADE:
      button_events.extend(self.update_longitudinal_upgrade(ret, can_parsers))

    button_events.extend(self.update_stalk_controls(ret, can_parsers))
    ret.buttonEvents = button_events

  @staticmethod
  def get_parser(CP, CP_SP) -> dict[StrEnum, CANParser]:
    messages = {}

    if CP_SP.flags & RivianFlagsSP.LONGITUDINAL_HARNESS_UPGRADE:
      messages[Bus.alt] = CANParser(DBC[CP.carFingerprint][Bus.alt], [], 1)

    return messages
