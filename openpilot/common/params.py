import os
import sys
import json
import time
import ctypes
import weakref
import builtins
import datetime
import tempfile
from pathlib import Path
from enum import IntEnum, IntFlag

from openpilot.common.swaglog import cloudlog


class ParamKeyFlag(IntFlag):
  PERSISTENT = 0x02
  CLEAR_ON_MANAGER_START = 0x04
  CLEAR_ON_ONROAD_TRANSITION = 0x08
  CLEAR_ON_OFFROAD_TRANSITION = 0x10
  DEVELOPMENT_ONLY = 0x40
  CLEAR_ON_IGNITION_ON = 0x80
  BACKUP = 0x100
  ALL = 0xFFFFFFFF


class ParamKeyType(IntEnum):
  STRING = 0
  BOOL = 1
  INT = 2
  FLOAT = 3
  TIME = 4
  JSON = 5
  BYTES = 6


# Virtual parameters supported for fork-specific platforms (e.g. Rivian R1 on GaryPilot)
# without requiring modification of prebuilt aarch64 binary schemas (params_keys.h).
VIRTUAL_PARAMS: dict[bytes, tuple[ParamKeyType, ParamKeyFlag, bytes]] = {}

# In-memory virtual param cache mapping (param_path, key_bytes) -> (mtime_ns, bytes_val | None, check_time)
_virtual_cache: dict[tuple[str, bytes], tuple[int, bytes | None, float]] = {}


_suffix = ".dylib" if sys.platform == "darwin" else ".so"
lib = ctypes.CDLL(Path(__file__).with_name(f"libparams_c{_suffix}"))

ParamsHandle = ctypes.c_void_p


class ParamsBuffer(ctypes.Structure):
  _fields_ = [("data", ctypes.c_void_p), ("size", ctypes.c_size_t)]


def _bind_raw(name, args, result=None):
  function = getattr(lib, name)
  function.argtypes = args
  function.restype = result
  return function


params_last_error = _bind_raw("params_last_error", [], ctypes.c_char_p)


def _bind(name, args, result=None):
  function = _bind_raw(name, args, result)

  def checked(*call_args):
    value = function(*call_args)
    if error := params_last_error():
      raise RuntimeError(error.decode())
    return value

  return checked


params_create = _bind("params_create", [ctypes.c_char_p, ctypes.c_size_t], ParamsHandle)
params_destroy = _bind("params_destroy", [ParamsHandle])
params_clear_all = _bind("params_clear_all", [ParamsHandle, ctypes.c_uint])
params_check_key = _bind("params_check_key", [ParamsHandle, ctypes.c_char_p], ctypes.c_bool)
params_get_key_type = _bind("params_get_key_type", [ParamsHandle, ctypes.c_char_p], ctypes.c_int)
params_get_default = _bind("params_get_default", [ParamsHandle, ctypes.c_char_p], ParamsBuffer)
params_get = _bind("params_get", [ParamsHandle, ctypes.c_char_p, ctypes.c_bool], ParamsBuffer)
params_get_bool = _bind("params_get_bool", [ParamsHandle, ctypes.c_char_p, ctypes.c_bool], ctypes.c_bool)
params_put = _bind("params_put", [ParamsHandle, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_bool], ctypes.c_int)
params_put_bool = _bind("params_put_bool", [ParamsHandle, ctypes.c_char_p, ctypes.c_bool, ctypes.c_bool], ctypes.c_int)
params_remove = _bind("params_remove", [ParamsHandle, ctypes.c_char_p], ctypes.c_int)
params_get_path = _bind("params_get_path", [ParamsHandle, ctypes.c_char_p, ctypes.c_size_t], ParamsBuffer)
params_keys_size = _bind("params_keys_size", [ParamsHandle], ctypes.c_size_t)
params_key_at = _bind("params_key_at", [ParamsHandle, ctypes.c_size_t], ParamsBuffer)
params_keys_by_flag = _bind("params_keys_by_flag", [ParamsHandle, ctypes.c_uint, ctypes.POINTER(ParamsBuffer), ctypes.c_size_t], ctypes.c_size_t)

PYTHON_2_CPP = {
  (str, ParamKeyType.STRING): lambda v: v,
  (builtins.bool, ParamKeyType.BOOL): lambda v: "1" if v else "0",
  (int, ParamKeyType.INT): str,
  (float, ParamKeyType.FLOAT): str,
  (datetime.datetime, ParamKeyType.TIME): lambda v: v.isoformat(),
  (dict, ParamKeyType.JSON): json.dumps,
  (list, ParamKeyType.JSON): json.dumps,
  (bytes, ParamKeyType.BYTES): lambda v: v,
}
CPP_2_PYTHON = {
  ParamKeyType.STRING: lambda v: v.decode("utf-8"),
  ParamKeyType.BOOL: lambda v: v == b"1",
  ParamKeyType.INT: int,
  ParamKeyType.FLOAT: float,
  ParamKeyType.TIME: lambda v: datetime.datetime.fromisoformat(v.decode("utf-8")),
  ParamKeyType.JSON: json.loads,
  ParamKeyType.BYTES: lambda v: v,
}


def ensure_bytes(v):
  return v.encode() if isinstance(v, str) else v


def _copy_string(value):
  if value.data is None:
    return None
  return ctypes.string_at(value.data, value.size)


class UnknownKeyName(Exception):
  pass


class Params:
  def __init__(self, d=""):
    path = ensure_bytes(d)
    self.p = params_create(path, len(path))
    self._finalizer = weakref.finalize(self, params_destroy, self.p)
    self._finalizer.atexit = False  # daemon threads can still be using live Params handles during interpreter shutdown
    self.d = d

  def __reduce__(self):
    return (type(self), (self.d,))

  def _virtual_param_path(self, k: bytes) -> Path:
    return Path(self.get_param_path()) / ".virtual" / k.decode()

  def clear_all(self, tx_flag=ParamKeyFlag.ALL):
    params_clear_all(self.p, int(tx_flag))
    if tx_flag == ParamKeyFlag.ALL:
      _virtual_cache.clear()
      try:
        for k in VIRTUAL_PARAMS:
          self._virtual_param_path(k).unlink(missing_ok=True)
          (Path(self.get_param_path()) / k.decode()).unlink(missing_ok=True)
      except Exception:
        pass
    else:
      for k, meta in VIRTUAL_PARAMS.items():
        if meta[1] & tx_flag:
          _virtual_cache.pop((self.get_param_path(), k), None)
          try:
            self._virtual_param_path(k).unlink(missing_ok=True)
            (Path(self.get_param_path()) / k.decode()).unlink(missing_ok=True)
          except Exception:
            pass

  def check_key(self, key):
    key = ensure_bytes(key)
    if key in VIRTUAL_PARAMS:
      return key
    if b"\0" in key or not params_check_key(self.p, key):
      raise UnknownKeyName(key)
    return key

  def python2cpp(self, proposed_type, expected_type, value, key):
    cast = PYTHON_2_CPP.get((proposed_type, expected_type))
    if cast:
      return cast(value)
    raise TypeError(f"Type mismatch while writing param {key}: {proposed_type=} {expected_type=} {value=}")

  def _cpp2python(self, t, value, default, key):
    if value is None:
      return None
    try:
      return CPP_2_PYTHON[t](value)
    except (KeyError, TypeError, ValueError):
      cloudlog.warning(f"Failed to cast param {key} with {value=} from type {t=}")
      return self._cpp2python(t, default, None, key)

  def _default(self, key):
    k = self.check_key(key)
    if k in VIRTUAL_PARAMS:
      return VIRTUAL_PARAMS[k][2]
    return _copy_string(params_get_default(self.p, key))

  def get(self, key, block=False, return_default=False):
    k = self.check_key(key)
    t = self.get_type(k)
    default = self._default(k) if return_default else None
    if k in VIRTUAL_PARAMS:
      cache_key = (self.get_param_path(), k)
      while True:
        now = time.monotonic()
        cached = _virtual_cache.get(cache_key)
        if cached is not None:
          mtime_ns, val, cache_time = cached
          if val is not None:
            return self._cpp2python(t, val, default, key)
          elif not block and (now - cache_time < 0.5):
            return self._cpp2python(t, default, None, key)

        target = self._virtual_param_path(k)
        if not target.exists():
          legacy_target = Path(self.get_param_path()) / k.decode()
          if legacy_target.exists():
            try:
              target.parent.mkdir(parents=True, exist_ok=True)
              os.replace(legacy_target, target)
            except Exception:
              pass

        try:
          stat = target.stat()
          mtime_ns = stat.st_mtime_ns
          if cached is not None and cached[0] == mtime_ns and cached[1] is not None:
            value = cached[1]
          else:
            value = target.read_bytes()
            _virtual_cache[cache_key] = (mtime_ns, value, now)
        except FileNotFoundError:
          _virtual_cache[cache_key] = (0, None, now)
          value = default
        except Exception:
          value = default

        if value is not None or not block:
          break
        time.sleep(0.1)

      if value == b"":
        return self._cpp2python(t, default, None, key)
      return self._cpp2python(t, value, default, key)
    value = _copy_string(params_get(self.p, k, block))
    if value == b"":
      if block:
        raise KeyboardInterrupt
      return self._cpp2python(t, default, None, key)
    return self._cpp2python(t, value, default, key)

  def get_bool(self, key, block=False):
    k = self.check_key(key)
    if k in VIRTUAL_PARAMS:
      val = self.get(k, block)
      return bool(val) if val is not None else (VIRTUAL_PARAMS[k][2] == b"1")
    return bool(params_get_bool(self.p, self.check_key(key), block))

  def _put_cast(self, key, dat):
    return ensure_bytes(self.python2cpp(type(dat), self.get_type(key), dat, key))

  def put(self, key, dat, block=False):
    """Write a parameter. block=True waits until it is persisted to disk."""
    k = self.check_key(key)
    value = self._put_cast(k, dat)
    if k in VIRTUAL_PARAMS:
      target = self._virtual_param_path(k)
      p = target.parent
      p.mkdir(parents=True, exist_ok=True)
      tmp_name = None
      try:
        with tempfile.NamedTemporaryFile("wb", dir=p, delete=False) as tf:
          tf.write(value)
          tf.flush()
          os.fsync(tf.fileno())
          tmp_name = tf.name
        os.replace(tmp_name, target)
        tmp_name = None  # replaced successfully
        try:
          (Path(self.get_param_path()) / k.decode()).unlink(missing_ok=True)
        except Exception:
          pass
        if sys.platform != "win32":
          try:
            dir_fd = os.open(str(p), os.O_RDONLY | os.O_DIRECTORY)
            try:
              os.fsync(dir_fd)
            finally:
              os.close(dir_fd)
          except Exception:
            pass
        try:
          _virtual_cache[(self.get_param_path(), k)] = (target.stat().st_mtime_ns, value, time.monotonic())
        except Exception:
          _virtual_cache.pop((self.get_param_path(), k), None)
      except Exception as e:
        cloudlog.warning(f"Failed to persist virtual param {key}: {e}")
      finally:
        if tmp_name is not None:
          try:
            os.unlink(tmp_name)
          except Exception:
            pass
      return
    params_put(self.p, k, value, len(value), block)

  def put_bool(self, key, val, block=False):
    k = self.check_key(key)
    if k in VIRTUAL_PARAMS:
      self.put(k, bool(val), block)
      return
    params_put_bool(self.p, self.check_key(key), val, block)

  def remove(self, key):
    k = self.check_key(key)
    if k in VIRTUAL_PARAMS:
      try:
        self._virtual_param_path(k).unlink(missing_ok=True)
        (Path(self.get_param_path()) / k.decode()).unlink(missing_ok=True)
      except Exception:
        pass
      _virtual_cache.pop((self.get_param_path(), k), None)
      return
    params_remove(self.p, self.check_key(key))

  def get_param_path(self, key=""):
    key = ensure_bytes(key)
    return _copy_string(params_get_path(self.p, key, len(key))).decode()

  def get_type(self, key):
    k = self.check_key(key)
    if k in VIRTUAL_PARAMS:
      return VIRTUAL_PARAMS[k][0]
    return ParamKeyType(params_get_key_type(self.p, self.check_key(key)))

  def all_keys(self, flag=ParamKeyFlag.ALL):
    virtual_keys = [k for k, meta in VIRTUAL_PARAMS.items() if (flag == ParamKeyFlag.ALL) or bool(meta[1] & flag)]
    if flag == ParamKeyFlag.ALL:
      keys = []
      for i in range(params_keys_size(self.p)):
        keys.append(_copy_string(params_key_at(self.p, i)))
      return keys + virtual_keys
    max_keys = 1024
    buf = (ParamsBuffer * max_keys)()
    count = params_keys_by_flag(self.p, int(flag), buf, max_keys)
    return [_copy_string(buf[i]) for i in range(min(count, max_keys))] + virtual_keys

  def get_default_value(self, key):
    k = self.check_key(key)
    return self._cpp2python(self.get_type(k), self._default(k), None, key)

  def cpp2python(self, key, value):
    return self._cpp2python(self.get_type(key), value, None, key)


if __name__ == "__main__":
  import sys

  params = Params()
  key = sys.argv[1]
  params.check_key(key)
  if len(sys.argv) == 3:
    val = sys.argv[2]
    print(f"SET: {key} = {val}")
    params.put(key, val, block=True)
  elif len(sys.argv) == 2:
    print(f"GET: {key} = {params.get(key)}")
