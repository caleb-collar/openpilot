import capnp
from typing import Any

from openpilot.cereal import custom
from openpilot.common.swaglog import cloudlog
from opendbc.car import structs

_FIELDS = '__dataclass_fields__'  # copy of dataclasses._FIELDS


def is_dataclass(obj):
  """Similar to dataclasses.is_dataclass without instance type check checking"""
  return hasattr(obj, _FIELDS)


def _asdictref_inner(obj) -> dict[str, Any] | Any:
  if is_dataclass(obj):
    ret = {}
    for field in getattr(obj, _FIELDS):  # similar to dataclasses.fields()
      ret[field] = _asdictref_inner(getattr(obj, field))
    return ret
  elif isinstance(obj, (tuple, list)):
    return type(obj)(_asdictref_inner(v) for v in obj)
  else:
    return obj


def asdictref(obj) -> dict[str, Any]:
  """
  Similar to dataclasses.asdict without recursive type checking and copy.deepcopy
  Note that the resulting dict will contain references to the original struct as a result
  """
  if not is_dataclass(obj):
    raise TypeError("asdictref() should be called on dataclass instances")

  return _asdictref_inner(obj)


def convert_to_capnp(struct: structs.CarParamsSP | structs.CarStateSP) -> capnp.lib.capnp._DynamicStructBuilder:
  struct_dict = asdictref(struct)

  if isinstance(struct, structs.CarParamsSP):
    struct_capnp = custom.CarParamsSP.new_message(**struct_dict)
  elif isinstance(struct, structs.CarStateSP):
    struct_capnp = custom.CarStateSP.new_message(**struct_dict)
  else:
    raise ValueError(f"Unsupported struct type: {type(struct)}")

  return struct_capnp


def convert_carControlSP(struct: capnp.lib.capnp._DynamicStructReader) -> structs.CarControlSP:
  # TODO: recursively handle any car struct as needed
  def remove_deprecated(s: dict) -> dict:
    return {k: v for k, v in s.items() if not k.endswith('DEPRECATED')}

  struct_dict = struct.to_dict()
  struct_dataclass = structs.CarControlSP(**remove_deprecated({k: v for k, v in struct_dict.items() if not isinstance(k, dict)}))

  struct_dataclass.mads = structs.ModularAssistiveDrivingSystem(**remove_deprecated(struct_dict.get('mads', {})))
  # struct_dataclass.params = [structs.CarControlSP.Param(**remove_deprecated(p)) for p in struct_dict.get('params', [])]
  struct_dataclass.leadOne = structs.LeadData(**remove_deprecated(struct_dict.get('leadOne', {})))
  struct_dataclass.leadTwo = structs.LeadData(**remove_deprecated(struct_dict.get('leadTwo', {})))
  struct_dataclass.intelligentCruiseButtonManagement = structs.IntelligentCruiseButtonManagement(
    **remove_deprecated(struct_dict.get('intelligentCruiseButtonManagement', {}))
  )

  return struct_dataclass


def enforce_vehicle_safety_gate(CP, CI_CC, openpilot_enabled_toggle: bool) -> bool:
  """GaryPilot safety lockout: strictly enforce Rivian R1 platform.

  Any non-Rivian vehicle is permanently locked into passive dashcam-only mode
  with SafetyModel.noOutput so no CAN actuation packets can ever be sent.
  """
  is_rivian = (CP.brand == "rivian")
  if not is_rivian:
    cloudlog.error(
      f"GaryPilot: Non-Rivian vehicle detected (brand='{CP.brand}', fingerprint='{CP.carFingerprint}'). " +
      "Actuation is strictly disabled."
    )
    CP.dashcamOnly = True

  controller_available = CI_CC is not None and openpilot_enabled_toggle and not CP.dashcamOnly
  CP.passive = not controller_available or CP.dashcamOnly
  if CP.passive:
    safety_config = structs.CarParams.SafetyConfig()
    safety_config.safetyModel = structs.CarParams.SafetyModel.noOutput
    CP.safetyConfigs = [safety_config]

  return controller_available

