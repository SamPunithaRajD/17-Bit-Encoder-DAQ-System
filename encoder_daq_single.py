

from __future__ import annotations




import sys
import os
import time
import datetime
import logging
import logging.handlers
import configparser
import ctypes
import csv
from ctypes import (
    Structure,
    POINTER,
    c_ushort,
    c_ulong,
    c_ubyte,
    c_ulonglong,
    c_char_p,
    byref,
    create_string_buffer,
)
from pathlib import Path
from collections import deque
from dataclasses import dataclass
from typing import Optional


try:
    import wx
except ImportError:
    print(
        "ERROR: wxPython is not installed.\n"
        "Install it with:  pip install wxPython"
    )
    sys.exit(1)





APP_NAME    = "17-Bit Absolute Encoder DAQ"
APP_VERSION = "2.1.0"
BUILD_INFO  = "Industrial Real-Time Edition — IIA / VBO Kavalur"


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)          
else:
    BASE_DIR = Path(__file__).resolve().parent

CONFIG_FILE = str(BASE_DIR / "config.ini")

LOG_DIR  = BASE_DIR / "logs"
LOG_FILE = str(LOG_DIR / "encoder.log")


ENCODER_BITS      = 17
TOTAL_POSITIONS   = 2 ** ENCODER_BITS          
DEGREES_PER_COUNT = 360.0 / TOTAL_POSITIONS    


ENCODER_PORT_LOW  = 0
ENCODER_PORT_HIGH = 1
ENCODER_PORT_MSB  = 2


UNIDAQ_DLL_NAME = "UniDAQ.dll"
BOARD_MODEL_HINT = "144"
BOARD_AUTO_DETECT = -1


DEFAULT_READ_INTERVAL_MS = 50
MIN_READ_INTERVAL_MS     = 10     


DEFAULT_MAX_CONSECUTIVE_FAILURES = 3
DEFAULT_RECONNECT_RETRY_MS = 2000


DEBUG_LOG_EVERY_N_READS = 20      
HEARTBEAT_INTERVAL_S    = 5       


DIRECTION_DEADBAND_COUNTS = 0     

# ── GUI indicator colours (R, G, B) ────────────────────────────────────
CLR_GREEN = (0,   180, 80)
CLR_RED   = (210, 40,  40)
CLR_AMBER = (220, 150,  0)
CLR_GREY  = (140, 140, 140)


THEME_BG_PANEL   = (32,  34,  38)     
THEME_BG_SECTION = (44,  47,  52)     
THEME_TEXT       = (222, 224, 227)    
THEME_TEXT_DIM   = (150, 153, 158)    
THEME_ACCENT     = (0,   150, 199)    
THEME_FIELD_BG   = (20,  21,  24)     

_DEFAULTS: dict = {
    "Application": {
        "read_interval_ms":          str(DEFAULT_READ_INTERVAL_MS),
        "logging_enabled":           "true",
        "log_level":                 "DEBUG",
        "theme":                     "industrial_dark",
        "max_consecutive_failures":  str(DEFAULT_MAX_CONSECUTIVE_FAILURES),
        "reconnect_retry_ms":        str(DEFAULT_RECONNECT_RETRY_MS),
        "debug_log_every_n_reads":   str(DEBUG_LOG_EVERY_N_READS),
    },
    "Encoder": {
        "bits":                  str(ENCODER_BITS),
        "counts_per_revolution": str(TOTAL_POSITIONS),
        "calibration_offset":    "0.0",
    },
    "Hardware": {
        "board_number": str(BOARD_AUTO_DETECT),
        "connector":    "auto",
        "port_low":     str(ENCODER_PORT_LOW),
        "port_high":    str(ENCODER_PORT_HIGH),
        "port_msb":     str(ENCODER_PORT_MSB),
        "dll_name":     UNIDAQ_DLL_NAME,
    },
}


class Config:
    """
    Thin wrapper around configparser that exposes typed properties
    and writes defaults if config.ini does not exist yet.
    """

    def __init__(self, path: str = CONFIG_FILE) -> None:
        self._path = Path(path)
        self._cfg = configparser.ConfigParser()
        self._load()

    def _load(self) -> None:
        for section, values in _DEFAULTS.items():
            self._cfg[section] = values

        if self._path.exists():
            self._cfg.read(self._path, encoding="utf-8")
            log.debug("Config loaded from %s", self._path)
        else:
            self.save()
            log.info("Default config written to %s", self._path)

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as fh:
            self._cfg.write(fh)
        log.debug("Config saved to %s", self._path)

    

    @property
    def read_interval_ms(self) -> int:
        value = self._cfg.getint(
            "Application", "read_interval_ms", fallback=DEFAULT_READ_INTERVAL_MS
        )
        return max(MIN_READ_INTERVAL_MS, value)

    @property
    def logging_enabled(self) -> bool:
        return self._cfg.getboolean("Application", "logging_enabled", fallback=True)

    @property
    def theme(self) -> str:
        return self._cfg.get("Application", "theme", fallback="industrial_dark")

    @property
    def max_consecutive_failures(self) -> int:
        return max(1, self._cfg.getint(
            "Application", "max_consecutive_failures",
            fallback=DEFAULT_MAX_CONSECUTIVE_FAILURES,
        ))

    @property
    def reconnect_retry_ms(self) -> int:
        return max(500, self._cfg.getint(
            "Application", "reconnect_retry_ms", fallback=DEFAULT_RECONNECT_RETRY_MS,
        ))

    @property
    def debug_log_every_n_reads(self) -> int:
        return max(1, self._cfg.getint(
            "Application", "debug_log_every_n_reads",
            fallback=DEBUG_LOG_EVERY_N_READS,
        ))

    def set_read_interval_ms(self, value: int) -> None:
        value = max(MIN_READ_INTERVAL_MS, int(value))
        self._cfg.set("Application", "read_interval_ms", str(value))
        self.save()
        log.info("read_interval_ms changed to %d ms via Preferences", value)

    def set_reconnect_retry_ms(self, value: int) -> None:
        value = max(500, int(value))
        self._cfg.set("Application", "reconnect_retry_ms", str(value))
        self.save()
        log.info("reconnect_retry_ms changed to %d ms via Preferences", value)

    @property
    def log_level(self) -> str:
        return self._cfg.get("Application", "log_level", fallback="DEBUG")

    def set_log_level(self, value: str) -> None:
        value = str(value).upper()
        if value not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            value = "DEBUG"
        self._cfg.set("Application", "log_level", value)
        self.save()
        log.info("log_level changed to %s via Preferences", value)
        log.setLevel(getattr(logging, value, logging.DEBUG))

    

    @property
    def calibration_offset(self) -> float:
        return self._cfg.getfloat("Encoder", "calibration_offset", fallback=0.0)

    def set_calibration_offset(self, value: float) -> None:
        value = float(value) % 360.0
        self._cfg.set("Encoder", "calibration_offset", str(value))
        self.save()
        log.info("calibration_offset changed to %.4f deg via Preferences", value)

    

    @property
    def board_number(self) -> int:
        return self._cfg.getint("Hardware", "board_number", fallback=BOARD_AUTO_DETECT)

    @property
    def connector(self) -> str:
        return self._cfg.get("Hardware", "connector", fallback="auto")

    def set_connector(self, value: str) -> None:
        value = str(value).strip().lower()
        if value not in ("auto", "1", "2", "3", "4", "5", "6"):
            value = "auto"
        self._cfg.set("Hardware", "connector", value)
        self.save()
        log.info("connector setting changed to %s via Preferences", value)

    @property
    def port_low(self) -> int:
        return self._cfg.getint("Hardware", "port_low", fallback=ENCODER_PORT_LOW)

    @property
    def port_high(self) -> int:
        return self._cfg.getint("Hardware", "port_high", fallback=ENCODER_PORT_HIGH)

    @property
    def port_msb(self) -> int:
        return self._cfg.getint("Hardware", "port_msb", fallback=ENCODER_PORT_MSB)

    @property
    def dll_name(self) -> str:
        return self._cfg.get("Hardware", "dll_name", fallback=UNIDAQ_DLL_NAME)





def _build_logger() -> logging.Logger:
    """Build and return the application logger."""
    logger = logging.getLogger(APP_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(module)-20s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"WARNING: Could not create log directory {LOG_DIR}: {exc}")

    try:
        fh = logging.handlers.RotatingFileHandler(
            Path(LOG_FILE),
            maxBytes=2_000_000,
            backupCount=8,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as exc:
        print(f"WARNING: Could not open log file {LOG_FILE}: {exc}")

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger

log = _build_logger()





class ReadRateMonitor:
    """
    Maintains a short rolling window of read timestamps and computes
    the average measured read rate in Hz.
    """

    def __init__(self, window_size: int = 20) -> None:
        self._window_size = max(2, window_size)
        self._timestamps: deque = deque(maxlen=self._window_size)

    def reset(self) -> None:
        self._timestamps.clear()

    def tick(self) -> None:
        """Record that a successful read just happened, right now."""
        self._timestamps.append(time.perf_counter())

    @property
    def hz(self) -> float:
        """Measured average read rate in Hz over the rolling window."""
        if len(self._timestamps) < 2:
            return 0.0
        span = self._timestamps[-1] - self._timestamps[0]
        if span <= 0:
            return 0.0
        return (len(self._timestamps) - 1) / span





@dataclass(frozen=True)
class EncoderReading:
    """Immutable snapshot of one complete encoder reading."""
    gray_code: str      
    binary:    str      
    hex_value: str       
    decimal:   int       
    angle_deg: float     
    dms_str:   str       
    dms_tuple: tuple     


def int_to_gray(n: int) -> str:
    """Convert a position integer to a 17-bit Gray Code binary string."""
    gray = n ^ (n >> 1)
    return format(gray, f"0{ENCODER_BITS}b")


def gray_to_binary(gray_code: str) -> str:
    """
    Convert a Gray Code string to a standard binary string.
    Algorithm: B[0] = G[0]; B[i] = B[i-1] XOR G[i]  (cascade L->R)
    """
    if len(gray_code) != ENCODER_BITS or not all(c in "01" for c in gray_code):
        raise ValueError(
            f"Invalid Gray Code: expected {ENCODER_BITS}-char binary string, "
            f"got {gray_code!r}"
        )
    bits = [gray_code[0]]
    for i in range(1, len(gray_code)):
        bits.append(str(int(bits[i - 1]) ^ int(gray_code[i])))
    return "".join(bits)


def binary_to_hex(binary_str: str) -> str:
    """Convert a binary string to a hex string with 0x prefix."""
    return "0x" + hex(int(binary_str, 2))[2:].upper()


def binary_to_decimal(binary_str: str) -> int:
    """Convert a binary string to a decimal integer."""
    return int(binary_str, 2)


def decimal_to_angle(count: int, offset: float = 0.0) -> float:
    """Convert a raw encoder count to degrees, with calibration offset."""
    raw = (count * 360.0) / TOTAL_POSITIONS
    return (raw + offset) % 360.0


def angle_to_dms(angle: float) -> tuple:
    """Convert decimal degrees to (degrees, minutes, seconds)."""
    d = int(angle)
    remainder = (angle - d) * 60.0
    m = int(remainder)
    s = round((remainder - m) * 60.0, 4)

    
    if s >= 60.0:
        s = 0.0
        m += 1
    if m >= 60:
        m = 0
        d += 1
    if d >= 360:
        d = 0

    return d, m, s


def build_reading(natural_binary_count: int, offset: float = 0.0) -> EncoderReading:
    """Build a complete EncoderReading from a raw encoder count integer."""
    if not (0 <= natural_binary_count < TOTAL_POSITIONS):
        raise ValueError(
            f"Encoder count {natural_binary_count} outside valid range "
            f"0-{TOTAL_POSITIONS - 1}"
        )

    binary    = format(natural_binary_count, f"0{ENCODER_BITS}b")
    gray_code = int_to_gray(natural_binary_count)
    angle     = decimal_to_angle(natural_binary_count, offset)
    d, m, s   = angle_to_dms(angle)

    return EncoderReading(
        gray_code = gray_code,
        binary    = binary,
        hex_value = binary_to_hex(binary),
        decimal   = natural_binary_count,
        angle_deg = angle,
        dms_str   = f"{d:03d}\u00b0 {m:02d}' {s:05.2f}\"",
        dms_tuple = (d, m, s),
    )





DIRECTION_CW          = "CLOCKWISE"
DIRECTION_CCW         = "COUNTER-CLOCKWISE"
DIRECTION_STATIONARY  = "STATIONARY"
DIRECTION_UNKNOWN     = "UNKNOWN"


def signed_wrap_delta(prev_count: int, curr_count: int,
                       total: int = TOTAL_POSITIONS) -> int:
    """Return the shortest signed step from prev_count to curr_count."""
    half = total // 2
    return ((curr_count - prev_count + half) % total) - half


class DirectionTracker:
    """Stateful helper to track absolute rotary direction across wraps."""

    def __init__(self, deadband_counts: int = 0) -> None:
        self._deadband = max(0, deadband_counts)
        self._prev_count: int | None = None

    def reset(self) -> None:
        self._prev_count = None

    def update(self, count: int) -> str:
        if self._prev_count is None:
            self._prev_count = count
            return DIRECTION_UNKNOWN

        delta = signed_wrap_delta(self._prev_count, count)
        self._prev_count = count

        if delta > self._deadband:
            return DIRECTION_CW
        if delta < -self._deadband:
            return DIRECTION_CCW
        return DIRECTION_STATIONARY





UNIDAQ_ERROR_MESSAGES = {
    0:  "Ixud_NoErr - Successfully",
    1:  "Ixud_OpenDriverErr - Open Driver Failure",
    2:  "Ixud_PnPDriverErr - Plug&Play Failure",
    3:  "Ixud_DriverNoOpen - Driver was not open",
    4:  "Ixud_GetDriverVersionErr - Get Driver Version Failure",
    5:  "Ixud_ExceedBoardNumber - Board number error",
    6:  "Ixud_FindBoardErr - Cannot Find Board",
    7:  "Ixud_BoardMappingErr - Board Mapping Error",
    8:  "Ixud_DIOModesErr - Configure DIO Port Failure",
    9:  "Ixud_InvalidAddress - Invalid Address",
    10: "Ixud_InvalidSize - Invalid Size",
    11: "Ixud_InvalidPortNumber - Invalid Port Number",
    12: "Ixud_UnSupportedModel - Model Is Not Supported",
    13: "Ixud_UnSupportedFun - Function Is Not Supported",
    14: "Ixud_InvalidChannelNumber - Invalid Channel Number",
    15: "Ixud_InvalidValue - Invalid Value",
    16: "Ixud_InvalidMode - Invalid Mode",
    17: "Ixud_GetAIStatusTimeOut - Data Not Ready",
    18: "Ixud_TimeOutErr - Timeout",
    19: "Ixud_CfgCodeIndexErr - Cannot Find Configuration Code Index",
    20: "ADC Timeout",
    21: "Cannot Find Board Index",
    22: "Invalid Setting",
    23: "Allocate Memory Space Failed",
    24: "Install Interrupt Event Failure",
    25: "Install Interrupt IRQ Failure",
    26: "Remove Interrupt IRQ Failure",
    27: "Clear Interrupt Count Failure",
    28: "Get System Buffer Failure",
    29: "Call CreateEvent() Failed",
    30: "Resolution Is Not Supported",
    31: "Call CreateThread() Failed",
}


def decode_error(code: int) -> str:
    """Translate a UniDAQ WORD return code into a readable message."""
    return UNIDAQ_ERROR_MESSAGES.get(code, f"Unknown UniDAQ error code {code}")


class UniDaqError(Exception):
    """Raised when a UniDAQ.dll call returns a non-zero (failure) code."""

    def __init__(self, function_name: str, code: int) -> None:
        self.function_name = function_name
        self.code = code
        self.message = decode_error(code)
        super().__init__(f"{function_name} failed: {self.message} (code {code})")


class IXUD_DEVICE_INFO(Structure):
    _fields_ = [
        ("dwSize",              c_ulong),
        ("wVendorID",           c_ushort),
        ("wDeviceID",           c_ushort),
        ("wSubVendorID",        c_ushort),
        ("wSubDeviceID",        c_ushort),
        ("dwBAR",               c_ulong * 6),
        ("BusNo",               c_ubyte),
        ("DevNo",               c_ubyte),
        ("IRQ",                 c_ubyte),
        ("Aux",                 c_ubyte),
        ("dwBarVirtualAddress", c_ulonglong * 6),
    ]


PIXUD_DEVICE_INFO = POINTER(IXUD_DEVICE_INFO)


class IXUD_CARD_INFO(Structure):
    _fields_ = [
        ("dwSize",           c_ulong),
        ("dwModelNo",        c_ulong),
        ("CardID",           c_ubyte),
        ("wSingleEnded",     c_ubyte),
        ("wAIOResolution",   c_ushort),
        ("wAIChannels",      c_ushort),
        ("wAOChannels",      c_ushort),
        ("wDIPorts",         c_ushort),
        ("wDOPorts",         c_ushort),
        ("wDIOPorts",        c_ushort),
        ("wDIOPortWidth",    c_ushort),
        ("wCounterChannels", c_ushort),
        ("wMemorySize",      c_ushort),
        ("dwReservedl",      c_ulong * 6),
    ]


PIXUD_CARD_INFO = POINTER(IXUD_CARD_INFO)


class UniDaqBindings:
    """Loads UniDAQ.dll and exposes wrapped methods around the official API."""

    def __init__(self, dll_name: str = "UniDAQ.dll") -> None:
        self.dll_name = dll_name
        self._dll: Optional[ctypes.WinDLL] = None

    def load(self) -> None:
        """Load UniDAQ.dll and declare explicit argtypes/restype."""
        
        dll_path = self.dll_name
        if not os.path.isabs(dll_path):
            dll_path = os.path.join(str(BASE_DIR), dll_path)

        self._dll = ctypes.WinDLL(dll_path)

        self._dll.Ixud_DriverInit.argtypes = [POINTER(c_ushort)]
        self._dll.Ixud_DriverInit.restype = c_ushort

        self._dll.Ixud_DriverClose.argtypes = []
        self._dll.Ixud_DriverClose.restype = c_ushort

        self._dll.Ixud_GetCardInfo.argtypes = [
            c_ushort, PIXUD_DEVICE_INFO, PIXUD_CARD_INFO, c_char_p,
        ]
        self._dll.Ixud_GetCardInfo.restype = c_ushort

        self._dll.Ixud_SetDIOMode.argtypes = [c_ushort, c_ushort, c_ushort]
        self._dll.Ixud_SetDIOMode.restype = c_ushort

        self._dll.Ixud_ReadDI.argtypes = [c_ushort, c_ushort, POINTER(c_ulong)]
        self._dll.Ixud_ReadDI.restype = c_ushort

        self._dll.Ixud_GetDllVersion.argtypes = [POINTER(c_ulong)]
        self._dll.Ixud_GetDllVersion.restype = c_ushort

    @property
    def is_loaded(self) -> bool:
        return self._dll is not None

    def driver_init(self) -> int:
        total = c_ushort(0)
        ret = self._dll.Ixud_DriverInit(byref(total))
        if ret != 0:
            raise UniDaqError("Ixud_DriverInit", ret)
        return total.value

    def driver_close(self) -> None:
        ret = self._dll.Ixud_DriverClose()
        if ret != 0:
            raise UniDaqError("Ixud_DriverClose", ret)

    def get_dll_version(self) -> int:
        version = c_ulong(0)
        ret = self._dll.Ixud_GetDllVersion(byref(version))
        if ret != 0:
            raise UniDaqError("Ixud_GetDllVersion", ret)
        return version.value

    def get_card_info(self, board_no: int) -> dict:
        dev_info = IXUD_DEVICE_INFO()
        card_info = IXUD_CARD_INFO()
        name_buf = create_string_buffer(20)

        ret = self._dll.Ixud_GetCardInfo(
            c_ushort(board_no), byref(dev_info), byref(card_info), name_buf,
        )
        if ret != 0:
            raise UniDaqError("Ixud_GetCardInfo", ret)

        return {
            "model_name": name_buf.value.decode("utf-8", errors="replace").strip(),
            "model_no": card_info.dwModelNo,
            "vendor_id": dev_info.wVendorID,
            "device_id": dev_info.wDeviceID,
            "bus_no": dev_info.BusNo,
            "dev_no": dev_info.DevNo,
            "irq": dev_info.IRQ,
            "card_id": card_info.CardID,
            "di_ports": card_info.wDIPorts,
            "do_ports": card_info.wDOPorts,
            "dio_ports": card_info.wDIOPorts,
            "dio_port_width": card_info.wDIOPortWidth,
        }

    def set_dio_mode(self, board_no: int, port_no: int, mode_output: bool) -> None:
        ret = self._dll.Ixud_SetDIOMode(
            c_ushort(board_no), c_ushort(port_no), c_ushort(1 if mode_output else 0),
        )
        if ret != 0:
            raise UniDaqError("Ixud_SetDIOMode", ret)

    def read_di(self, board_no: int, port_no: int) -> int:
        value = c_ulong(0)
        ret = self._dll.Ixud_ReadDI(c_ushort(board_no), c_ushort(port_no), byref(value))
        if ret != 0:
            raise UniDaqError("Ixud_ReadDI", ret)
        return value.value & 0xFF





class HardwareConnectionError(Exception):
    """Raised when the PIO-D144 cannot be reached (DLL/driver/connection failure)."""
    pass



CONNECTOR_MAP = {
    1: {"low": 0, "high": 1, "msb": 2},
    2: {"low": 3, "high": 4, "msb": 5},
    3: {"low": 6, "high": 7, "msb": 8},
    4: {"low": 9, "high": 10, "msb": 11},
    5: {"low": 12, "high": 13, "msb": 14},
    6: {"low": 15, "high": 16, "msb": 17},
}


class HardwareManager:
    """Manages driver life cycle and card/port registration details."""

    def __init__(
        self,
        board_number: int = BOARD_AUTO_DETECT,
        connector_setting: str = "auto",
        port_low: int = 0,
        port_high: int = 1,
        port_msb: int = 2,
        dll_name: str = "UniDAQ.dll",
        debug_log_every_n: int = 1,
    ) -> None:
        self._requested_board = board_number
        self._connector_setting = connector_setting
        self._p_low = port_low
        self._p_high = port_high
        self._p_msb = port_msb
        self._debug_log_every_n = max(1, debug_log_every_n)
        self._read_counter = 0

        self._api = UniDaqBindings(dll_name)
        self._board: int = 0
        self._model_name: str = ""
        self._connected: bool = False
        self._dll_version: Optional[int] = None
        self._last_raw_ports: tuple = (0, 0, 0)
        self._active_connector: int = 1
        self._card_info: dict = {}
        self._card_connected: bool = False
        self._encoder_present: bool = False

    @property
    def board_number(self) -> int:
        return self._board

    @property
    def card_connected(self) -> bool:
        return self._card_connected

    @property
    def encoder_present(self) -> bool:
        return self._encoder_present

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def card_info(self) -> dict:
        return self._card_info

    @property
    def dll_version_hex(self) -> str:
        if self._dll_version is None:
            return "Unknown"
        return f"0x{self._dll_version:08X}"

    @property
    def last_raw_ports(self) -> tuple:
        return self._last_raw_ports

    @property
    def active_connector(self) -> int:
        return self._active_connector

    @property
    def port_low(self) -> int:
        return self._p_low

    @property
    def port_high(self) -> int:
        return self._p_high

    @property
    def port_msb(self) -> int:
        return self._p_msb

    def connect(self, log_cb=None) -> bool:
        self._card_connected = False
        self._encoder_present = False
        self._connected = False

        
        try:
            if log_cb:
                log_cb("Loading UniDAQ.dll...")
            self._api.load()
            if log_cb:
                log_cb("PASS")
                log_cb("Initializing UniDAQ Driver...")
            
            
            total_boards = self._api.driver_init()
            self._total_boards = total_boards
            if total_boards == 0:
                raise HardwareConnectionError(
                    "Ixud_DriverInit found 0 boards. Check that the PIO-D144 "
                    "is seated correctly and the UniDAQ driver is installed."
                )
            if log_cb:
                log_cb("PASS")
            
            
            self._fetch_dll_version()
            if log_cb and self._dll_version is not None:
                log_cb(f"Driver Version: {self.dll_version_hex}")
                
            if log_cb:
                log_cb("Searching PCI Boards...")
                
            
            self._select_board()
            
            if log_cb:
                log_cb("PASS")
                log_cb(f"PIO-D144 Detected")
                log_cb(f"Board Number: {self._board}")
                card_id_val = self._card_info.get("card_id", "N/A")
                log_cb(f"Card ID: {card_id_val}")
                log_cb("Hardware Communication Test...")
                
            
            self._p_low = 0
            self._p_high = 1
            self._p_msb = 2
            self._configure_ports()
            
            
            self._verify_communication()
            
            if log_cb:
                log_cb("PASS")
                log_cb("Hardware Status: CONNECTED")
                
            self._card_connected = True
            self._connected = True
            self._read_counter = 0
            
        except Exception as exc:
            self._connected = False
            self._card_connected = False
            self._encoder_present = False
            if log_cb:
                log_cb("ERROR")
                log_cb("No PIO-D144 Card Found")
                log_cb("Hardware Connection Failed")
            log.error("PCI hardware verification failed: %s", exc)
            return False

        
        try:
            if log_cb:
                log_cb("Searching Encoder Connectors...")
            
            
            self._detect_and_configure_connector(log_cb)
            
            
            self._encoder_present = True
            log.info("HardwareManager: connected and encoder detected on active connector %d", self._active_connector)
            return True
            
        except HardwareConnectionError as exc:
            
            self._encoder_present = False
            log.warning("PCI card verified but encoder not found: %s", exc)
            return True
        except Exception as exc:
            self._encoder_present = False
            log.error("Unexpected error during connector scan: %s", exc)
            return True

    def disconnect(self) -> None:
        if self._api.is_loaded:
            try:
                self._api.driver_close()
            except UniDaqError as exc:
                log.warning("Ixud_DriverClose reported an error: %s", exc)
            except Exception as exc:
                log.warning("Error closing UniDAQ driver: %s", exc)
        self._connected = False
        log.info("HardwareManager: disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def read_count(self) -> int:
        if not self._connected:
            raise ConnectionError("Hardware not connected")

        try:
            b0 = self._api.read_di(self._board, self._p_low)    
            b1 = self._api.read_di(self._board, self._p_high)   
            b2 = self._api.read_di(self._board, self._p_msb)    

            raw = ((b2 & 0x01) << 16) | (b1 << 8) | b0
            raw &= (TOTAL_POSITIONS - 1)

            self._last_raw_ports = (b0, b1, b2)

            self._read_counter += 1
            if self._read_counter % self._debug_log_every_n == 0:
                log.debug("HW read: port2=%02X port1=%02X port0=%02X -> count=%d",
                           b2, b1, b0, raw)
            return raw

        except ConnectionError:
            raise
        except UniDaqError as exc:
            raise IOError(f"Port read failed: {exc}") from exc
        except Exception as exc:
            raise IOError(f"Port read failed: {exc}") from exc

    def _load_driver(self) -> None:
        self._api.load()
        total_boards = self._api.driver_init()
        log.info("UniDAQ driver initialised: %d board(s) found", total_boards)
        if total_boards == 0:
            raise HardwareConnectionError(
                "Ixud_DriverInit found 0 boards. Check that the PIO-D144 "
                "is seated correctly and the UniDAQ driver is installed."
            )
        self._total_boards = total_boards

    def _fetch_dll_version(self) -> None:
        try:
            self._dll_version = self._api.get_dll_version()
            log.info("UniDAQ.dll version: %s", self.dll_version_hex)
        except UniDaqError as exc:
            log.warning("Ixud_GetDllVersion failed (non-fatal): %s", exc)
            self._dll_version = None

    def _select_board(self) -> None:
        if self._requested_board != BOARD_AUTO_DETECT:
            self._board = self._requested_board
            log.info("Using board number forced by config.ini: %d", self._board)
            try:
                info = self._api.get_card_info(self._board)
                self._model_name = info["model_name"]
                self._card_info = info
            except UniDaqError as exc:
                log.warning("Ixud_GetCardInfo failed for forced board %d: %s",
                            self._board, exc)
            return

        for i in range(self._total_boards):
            try:
                info = self._api.get_card_info(i)
            except UniDaqError as exc:
                log.warning("Ixud_GetCardInfo failed for board %d: %s", i, exc)
                continue

            name = info["model_name"]
            log.info("Board %d: model='%s'", i, name)
            if BOARD_MODEL_HINT in name.upper() or BOARD_MODEL_HINT in name:
                self._board = i
                self._model_name = name
                self._card_info = info
                log.info("Auto-detected PIO-D144 at board %d ('%s')", i, name)
                return

        log.warning(
            "No board reported a model name containing '%s'. "
            "Falling back to board 0.", BOARD_MODEL_HINT,
        )
        self._board = 0
        try:
            info = self._api.get_card_info(0)
            self._model_name = info["model_name"]
            self._card_info = info
        except UniDaqError:
            self._model_name = ""

    def _configure_ports(self) -> None:
        for port in (self._p_low, self._p_high, self._p_msb):
            self._api.set_dio_mode(self._board, port, mode_output=False)
        log.debug(
            "Ports %d, %d, %d configured as digital inputs",
            self._p_low, self._p_high, self._p_msb,
        )

    def _detect_and_configure_connector(self, log_cb=None) -> None:
        conn_setting = str(self._connector_setting).strip().lower()
        
        
        if conn_setting in ("1", "2", "3", "4", "5", "6"):
            conn_idx = int(conn_setting)
            mapping = CONNECTOR_MAP[conn_idx]
            self._p_low = mapping["low"]
            self._p_high = mapping["high"]
            self._p_msb = mapping["msb"]
            self._active_connector = conn_idx
            
            
            self._configure_ports()
            
            msg = f"Using manual connector configuration: Connector {conn_idx}"
            if log_cb:
                log_cb(msg)
            log.info(msg)
            return

        
        msg = "Searching for Encoder..."
        if log_cb:
            log_cb(msg)
        log.info(msg)

        detected_conn = -1
        
        
        for conn_idx in sorted(CONNECTOR_MAP.keys()):
            mapping = CONNECTOR_MAP[conn_idx]
            
            
            for port in (mapping["low"], mapping["high"], mapping["msb"]):
                try:
                    self._api.set_dio_mode(self._board, port, mode_output=False)
                except Exception as exc:
                    log.warning("Failed to configure port %d: %s", port, exc)
                
            
            samples = []
            valid = True
            for _ in range(10):
                time.sleep(0.005)
                try:
                    b0 = self._api.read_di(self._board, mapping["low"])
                    b1 = self._api.read_di(self._board, mapping["high"])
                    b2 = self._api.read_di(self._board, mapping["msb"])
                    
                    count = ((b2 & 0x01) << 16) | (b1 << 8) | b0
                    
                    
                    if count == 0 or count == 131071:
                        valid = False
                        break
                    samples.append(count)
                except Exception as exc:
                    log.warning("Sample read failed on Connector %d: %s", conn_idx, exc)
                    valid = False
                    break
            
            if not valid or len(samples) < 10:
                msg = f"Connector {conn_idx} ..... No Signal"
                if log_cb:
                    log_cb(msg)
                log.info(msg)
                continue
                
            
            stable = True
            for i in range(len(samples) - 1):
                delta = abs(signed_wrap_delta(samples[i], samples[i+1]))
                if delta > 500:
                    stable = False
                    break
                    
            if stable:
                detected_conn = conn_idx
                msg = f"Connector {conn_idx} ..... Encoder Detected (stable count={samples[-1]})"
                if log_cb:
                    log_cb(msg)
                log.info(msg)
                break
            else:
                msg = f"Connector {conn_idx} ..... Rejected (noisy or unstable signal)"
                if log_cb:
                    log_cb(msg)
                log.info(msg)

        if detected_conn != -1:
            self._active_connector = detected_conn
            mapping = CONNECTOR_MAP[detected_conn]
            self._p_low = mapping["low"]
            self._p_high = mapping["high"]
            self._p_msb = mapping["msb"]
            
            
            self._configure_ports()
            
            msg = f"Using Connector {detected_conn}"
            if log_cb:
                log_cb(msg)
            log.info(msg)
        else:
            
            self._active_connector = 1  
            mapping = CONNECTOR_MAP[1]
            self._p_low = mapping["low"]
            self._p_high = mapping["high"]
            self._p_msb = mapping["msb"]
            
            
            self._configure_ports()
            
            msg = "No encoder detected on any connector. Defaulting to Connector 1"
            if log_cb:
                log_cb(msg)
            log.warning(msg)
            
            raise HardwareConnectionError("No encoder signal detected on any connector group.")

    def _verify_communication(self) -> None:
        self._api.read_di(self._board, self._p_low)





@dataclass(frozen=True)
class LiveReading:
    """One complete, display-ready snapshot for the industrial GUI."""
    reading:     EncoderReading
    direction:   str
    timestamp:   datetime.datetime
    measured_hz: float
    raw_ports:   tuple


class EncoderService:
    """Merges physical reading pipeline and math calculations."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._hw = HardwareManager(
            board_number=cfg.board_number,
            connector_setting=cfg.connector,
            port_low=cfg.port_low,
            port_high=cfg.port_high,
            port_msb=cfg.port_msb,
            dll_name=cfg.dll_name,
            debug_log_every_n=cfg.debug_log_every_n_reads,
        )
        self._direction = DirectionTracker()
        self._rate = ReadRateMonitor()

    def connect(self, log_cb=None) -> bool:
        ok = self._hw.connect(log_cb=log_cb)
        if ok:
            self._direction.reset()
            self._rate.reset()
        return ok

    def disconnect(self) -> None:
        self._hw.disconnect()

    def is_connected(self) -> bool:
        return self._hw.is_connected()

    @property
    def board_number(self) -> int:
        return self._hw.board_number

    @property
    def card_connected(self) -> bool:
        return self._hw.card_connected

    @property
    def encoder_present(self) -> bool:
        return self._hw.encoder_present

    @property
    def model_name(self) -> str:
        return self._hw.model_name

    @property
    def dll_version_hex(self) -> str:
        return self._hw.dll_version_hex

    def get_reading(self) -> LiveReading:
        if not self.is_connected():
            raise ConnectionError("No active encoder connection")

        count = self._hw.read_count()
        reading = build_reading(count, offset=self._cfg.calibration_offset)

        direction = self._direction.update(count)
        self._rate.tick()

        return LiveReading(
            reading=reading,
            direction=direction,
            timestamp=datetime.datetime.now(),
            measured_hz=self._rate.hz,
            raw_ports=self._hw.last_raw_ports,
        )



# GUI

class LEDIndicator(wx.Panel):
    """Circular coloured status indicator mimicking physical LEDs."""

    _RADIUS = 7

    def __init__(self, parent: wx.Window, colour: tuple = CLR_GREY) -> None:
        super().__init__(parent, size=wx.Size(18, 18))
        self._colour = wx.Colour(*colour)
        self.SetMinSize(wx.Size(18, 18))
        self.SetBackgroundColour(parent.GetBackgroundColour())
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def set_colour(self, colour: tuple) -> None:
        self._colour = wx.Colour(*colour)
        self.Refresh()

    def _on_paint(self, _evt: wx.PaintEvent) -> None:
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        dc.SetBrush(wx.Brush(self._colour))
        dc.SetPen(wx.Pen(wx.Colour(20, 20, 20), 1))
        dc.DrawCircle(9, 9, self._RADIUS)


class MainFrame(wx.Frame):
    """Base layout builder class (wxFormBuilder implementation)."""

    def __init__(self, parent: wx.Window = None) -> None:
        super().__init__(
            parent,
            id=wx.ID_ANY,
            title="17-Bit Absolute Encoder Data Acquisition System",
            size=wx.Size(1180, 820),
            style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL,
        )
        self.SetMinSize(wx.Size(1000, 700))
        self.SetBackgroundColour(wx.Colour(*THEME_BG_PANEL))

        self._build_menu_bar()

        self.CreateStatusBar(1)
        self.SetStatusText("Ready.")

        self._build_ui()
        self.Centre(wx.BOTH)
        self.Layout()

    @staticmethod
    def _font(size: int, weight=wx.FONTWEIGHT_NORMAL, style=wx.FONTSTYLE_NORMAL,
              face: str = "Arial") -> wx.Font:
        return wx.Font(size, wx.FONTFAMILY_DEFAULT, style, weight, False, face)

    def _section(self, label: str) -> wx.StaticBox:
        sb = wx.StaticBox(self, label=label)
        sb.SetBackgroundColour(wx.Colour(*THEME_BG_SECTION))
        sb.SetForegroundColour(wx.Colour(*THEME_ACCENT))
        sb.SetFont(self._font(9, wx.FONTWEIGHT_BOLD))
        return sb

    def _static_text(self, parent, label, size=9, weight=wx.FONTWEIGHT_NORMAL,
                      style=wx.FONTSTYLE_NORMAL, colour=THEME_TEXT,
                      align=0, min_size=None) -> wx.StaticText:
        t = wx.StaticText(parent, label=label, style=align)
        if min_size is not None:
            t.SetMinSize(min_size)
        t.SetFont(self._font(size, weight, style))
        t.SetForegroundColour(wx.Colour(*colour))
        return t

    def _data_field(self, parent) -> wx.TextCtrl:
        tc = wx.TextCtrl(parent, style=wx.TE_READONLY, size=wx.Size(-1, 26))
        tc.SetFont(self._font(10, face="Consolas"))
        tc.SetBackgroundColour(wx.Colour(*THEME_FIELD_BG))
        tc.SetForegroundColour(wx.Colour(*THEME_TEXT))
        return tc

    def _build_menu_bar(self) -> None:
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        self.miSaveReading = file_menu.Append(
            wx.ID_ANY, "&Save Current Reading\tCtrl+S",
            "Save the current encoder reading to a CSV file"
        )
        self.miExportLog = file_menu.Append(
            wx.ID_ANY, "Export Event &Log...",
            "Save the current event log to a text file"
        )
        self.miClearLog = file_menu.Append(
            wx.ID_ANY, "Clear Event &Log\tCtrl+L",
            "Clear the scrolling event log (does not affect encoder readings)",
        )
        file_menu.AppendSeparator()
        self.miExit = file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q", "Close the application")
        menu_bar.Append(file_menu, "&File")

        conn_menu = wx.Menu()
        self.miReconnectNow = conn_menu.Append(
            wx.ID_ANY, "&Reconnect Now\tCtrl+R",
            "Force an immediate reconnect attempt, bypassing the automatic retry cadence",
        )
        conn_menu.AppendSeparator()
        self.miConnectionDetails = conn_menu.Append(
            wx.ID_ANY, "Connection &Details...",
            "Show current driver, board, and DLL version details",
        )
        menu_bar.Append(conn_menu, "&Connection")

        settings_menu = wx.Menu()
        self.miPreferences = settings_menu.Append(
            wx.ID_PREFERENCES, "&Preferences...\tCtrl+,",
            "Edit read interval and calibration offset",
        )
        settings_menu.AppendSeparator()
        self.miToggleEngDiag = settings_menu.AppendCheckItem(
            wx.ID_ANY, "Show &Engineering Diagnostics",
            "Show/hide raw port values and combined bit-level diagnostics",
        )
        menu_bar.Append(settings_menu, "&Settings")

        tools_menu = wx.Menu()
        self.miHardwareInfo = tools_menu.Append(
            wx.ID_ANY, "&Hardware Information",
            "Display comprehensive hardware and driver diagnostics"
        )
        self.miLiveDiagnostics = tools_menu.Append(
            wx.ID_ANY, "&Live Diagnostics",
            "Continuously display real-time port values and reconstruction metrics"
        )
        self.miConnectionTest = tools_menu.Append(
            wx.ID_ANY, "&Connection Test",
            "Run a diagnostic test of the DLL, card, and read flow"
        )
        menu_bar.Append(tools_menu, "&Tools")

        help_menu = wx.Menu()
        self.miAbout = help_menu.Append(wx.ID_ABOUT, "&About...", "About this application")
        menu_bar.Append(help_menu, "&Help")

        self.SetMenuBar(menu_bar)

    def _build_ui(self) -> None:
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(self._build_header(),    0, wx.EXPAND | wx.ALL, 6)
        root.Add(self._build_hw_status(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        data_row = wx.BoxSizer(wx.HORIZONTAL)
        data_row.Add(self._build_encoder_panel(),     3, wx.EXPAND | wx.RIGHT, 4)
        data_row.Add(self._build_diagnostics_panel(), 2, wx.EXPAND)
        root.Add(data_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        root.Add(self._build_engineering_diagnostics_panel(), 0,
                 wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.pnlEngDiag.Hide()

        root.Add(self._build_log_panel(), 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.SetSizer(root)

    def _build_header(self) -> wx.Sizer:
        outer = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)

        self.lblTitle = self._static_text(
            self, "17-Bit Absolute Encoder Data Acquisition System",
            size=14, weight=wx.FONTWEIGHT_BOLD, colour=THEME_ACCENT,
        )

        right = wx.BoxSizer(wx.VERTICAL)
        top_row = wx.BoxSizer(wx.HORIZONTAL)
        self.lblDate = self._static_text(self, "", size=9)
        self.lblTime = self._static_text(self, "", size=9, weight=wx.FONTWEIGHT_BOLD)
        top_row.Add(self.lblDate, 0, wx.RIGHT, 10)
        top_row.Add(self.lblTime, 0)

        self.lblVersion = self._static_text(
            self, f"Version {APP_VERSION}  \u2014  {BUILD_INFO}",
            size=8, style=wx.FONTSTYLE_ITALIC, colour=THEME_TEXT_DIM,
        )

        right.Add(top_row,         0, wx.ALIGN_RIGHT)
        right.Add(self.lblVersion, 0, wx.ALIGN_RIGHT | wx.TOP, 2)

        row.Add(self.lblTitle, 1, wx.ALIGN_CENTER_VERTICAL)
        row.Add(right,         0, wx.ALIGN_CENTER_VERTICAL)

        outer.Add(row, 0, wx.EXPAND | wx.BOTTOM, 4)
        outer.Add(wx.StaticLine(self), 0, wx.EXPAND)
        return outer

    def _build_hw_status(self) -> wx.Sizer:
        sb = self._section("System Status")
        box = wx.StaticBoxSizer(sb, wx.HORIZONTAL)
        p = sb

        def _indicator(label_text: str) -> tuple:
            led = LEDIndicator(p, CLR_GREY)
            lbl = self._static_text(p, label_text, size=9, weight=wx.FONTWEIGHT_BOLD)
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(led, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            box.Add(row, 0, wx.ALL, 8)
            box.Add((14, 0))
            return led, lbl

        self.ledDriver,      self.lblDriver      = _indicator("Driver : Not Loaded")
        self.ledCard,        self.lblCard        = _indicator("Card : Not Connected")
        self.ledEncoder,     self.lblEncoder     = _indicator("Encoder : No Signal")
        self.ledAcquisition, self.lblAcquisition = _indicator("Acquisition : Stopped")

        box.AddStretchSpacer()
        return box

    def _build_encoder_panel(self) -> wx.Sizer:
        sb = self._section("Encoder Data (Live)")
        box = wx.StaticBoxSizer(sb, wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=7, cols=2, vgap=7, hgap=12)
        grid.AddGrowableCol(1)

        def _row(label_text: str, attr_name: str) -> None:
            lbl = self._static_text(
                sb, label_text, size=9, weight=wx.FONTWEIGHT_BOLD,
                align=wx.ALIGN_RIGHT, min_size=wx.Size(150, -1),
            )
            tc = self._data_field(sb)
            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
            grid.Add(tc,  1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
            setattr(self, attr_name, tc)

        _row("Gray Code :",      "txtGrayCode")
        _row("Binary :",         "txtBinary")
        _row("Hexadecimal :",    "txtHex")
        _row("Decimal Count :",  "txtDecimal")
        _row("Angle (\u00b0) :", "txtAngle")
        _row("Angle (DMS) :",    "txtDMS")
        _row("Direction :",      "txtDirection")

        box.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        return box

    def _build_diagnostics_panel(self) -> wx.Sizer:
        sb = self._section("Hardware Information & Diagnostics")
        box = wx.StaticBoxSizer(sb, wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=16, cols=2, vgap=5, hgap=10)
        grid.AddGrowableCol(1)

        def _row(label_text: str, attr_name: str, default: str = "\u2014") -> None:
            lbl = self._static_text(
                sb, label_text, size=8, colour=THEME_TEXT_DIM,
                min_size=wx.Size(140, -1),
            )
            val = self._static_text(sb, default, size=8, weight=wx.FONTWEIGHT_BOLD)
            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(val, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
            setattr(self, attr_name, val)

        _row("Board Name / Model :",   "lblDetectedCard")
        _row("Card ID :",             "lblCardId")
        _row("Board Number :",        "lblBoardNumber")
        _row("Driver Status :",       "lblDriverStatus")
        _row("DLL Status :",          "lblDllStatus")
        _row("DLL Version :",         "lblDllVersion")
        _row("Connection Status :",   "lblConnectionStatus")
        _row("Active Connector :",    "lblActiveConnector")
        _row("Port Mapping :",        "lblPortMapping")
        _row("Read Rate :",           "lblReadRate")
        _row("Read Interval :",       "lblReadIntervalDiag")
        _row("PCI Bus Number :",      "lblPciBus")
        _row("PCI Device Number :",   "lblPciDevice")
        _row("IRQ Number :",          "lblIrqNumber")
        _row("Vendor ID :",           "lblVendorId")
        _row("Device ID :",           "lblDeviceId")

        
        self.lblLastValidReading = wx.StaticText(self, label="")
        self.lblLastValidReading.Hide()
        self.lblLastUpdate = wx.StaticText(self, label="")
        self.lblLastUpdate.Hide()

        box.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        return box

    def _build_engineering_diagnostics_panel(self) -> wx.Panel:
        self.pnlEngDiag = wx.Panel(self)
        self.pnlEngDiag.SetBackgroundColour(wx.Colour(*THEME_BG_PANEL))

        sb = wx.StaticBox(self.pnlEngDiag, label="Engineering Diagnostics")
        sb.SetBackgroundColour(wx.Colour(*THEME_BG_SECTION))
        sb.SetForegroundColour(wx.Colour(*THEME_ACCENT))
        sb.SetFont(self._font(9, wx.FONTWEIGHT_BOLD))

        box = wx.StaticBoxSizer(sb, wx.HORIZONTAL)

        def _field(label_text: str, attr_name: str) -> None:
            col = wx.BoxSizer(wx.VERTICAL)
            lbl = self._static_text(sb, label_text, size=8, colour=THEME_TEXT_DIM)
            val = self._static_text(sb, "\u2014", size=10, weight=wx.FONTWEIGHT_BOLD)
            col.Add(lbl, 0, wx.ALIGN_CENTER_HORIZONTAL)
            col.Add(val, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 2)
            box.Add(col, 0, wx.ALL, 10)
            box.Add((18, 0))
            setattr(self, attr_name, val)

        _field("Raw Port 0",            "lblRawPort0")
        _field("Raw Port 1",            "lblRawPort1")
        _field("Raw Port 2",            "lblRawPort2")
        _field("Combined 17-bit Value", "lblCombined17Bit")
        _field("Gray Code",             "lblGrayCodeDiag")

        box.AddStretchSpacer()
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(box, 0, wx.EXPAND)
        self.pnlEngDiag.SetSizer(outer)
        return self.pnlEngDiag

    def _build_log_panel(self) -> wx.Sizer:
        sb = self._section("Event Log")
        box = wx.StaticBoxSizer(sb, wx.VERTICAL)
        self.txtStatus = wx.TextCtrl(
            sb,
            value="Ready...\n",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_LEFT,
            size=wx.Size(-1, 110),
        )
        self.txtStatus.SetFont(self._font(9, face="Consolas"))
        self.txtStatus.SetBackgroundColour(wx.Colour(*THEME_FIELD_BG))
        self.txtStatus.SetForegroundColour(wx.Colour(*THEME_TEXT))
        box.Add(self.txtStatus, 1, wx.EXPAND | wx.ALL, 4)
        return box

    def set_engineering_diagnostics_visible(self, visible: bool) -> None:
        self.pnlEngDiag.Show(visible)
        self.Layout()


class LiveDiagnosticsDialog(wx.Dialog):
    """Continuously updating diagnostics readouts from the three raw ports."""

    def __init__(self, parent, controller) -> None:
        super().__init__(parent, title="Live Diagnostics", size=wx.Size(460, 360))
        self.controller = controller
        self.SetBackgroundColour(wx.Colour(*THEME_BG_PANEL))

        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(*THEME_BG_PANEL))
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        
        grid = wx.FlexGridSizer(rows=9, cols=2, vgap=8, hgap=14)
        grid.AddGrowableCol(1)

        def _add_row(label_text):
            lbl = wx.StaticText(panel, label=label_text)
            lbl.SetForegroundColour(wx.Colour(*THEME_TEXT))
            lbl.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            
            val = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.TE_RIGHT, size=(-1, 24))
            val.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "Consolas"))
            val.SetBackgroundColour(wx.Colour(*THEME_FIELD_BG))
            val.SetForegroundColour(wx.Colour(0, 255, 0)) 
            
            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(val, 1, wx.EXPAND)
            return val

        self.val_port0 = _add_row("Port 0 (Low Byte):")
        self.val_port1 = _add_row("Port 1 (High Byte):")
        self.val_port2 = _add_row("Port 2 (MSB Bit):")
        self.val_count = _add_row("Reconstructed 17-bit Count:")
        self.val_gray  = _add_row("Gray Code:")
        self.val_bin   = _add_row("Binary Code:")
        self.val_dec   = _add_row("Decimal Value:")
        self.val_ang   = _add_row("Angle (Degrees):")
        self.val_dms   = _add_row("Angle (DMS):")

        vbox.Add(grid, 1, wx.EXPAND | wx.ALL, 16)
        
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        btn_sizer.Add(close_btn)
        vbox.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        
        panel.SetSizer(vbox)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(100) 
        
        
        self.on_timer(None)

    def on_timer(self, _evt) -> None:
        live = self.controller._last_valid_live
        if live and self.controller._service.is_connected():
            p0, p1, p2 = live.raw_ports
            r = live.reading
            self.val_port0.SetValue(f"0x{p0:02X}  ({p0:08b})")
            self.val_port1.SetValue(f"0x{p1:02X}  ({p1:08b})")
            self.val_port2.SetValue(f"0x{p2:02X}  ({p2:08b})")
            self.val_count.SetValue(f"0x{r.decimal:05X}")
            self.val_gray.SetValue(r.gray_code)
            self.val_bin.SetValue(r.binary)
            self.val_dec.SetValue(str(r.decimal))
            self.val_ang.SetValue(f"{r.angle_deg:.6f}\u00b0")
            self.val_dms.SetValue(r.dms_str)
        else:
            self.val_port0.SetValue("N/A")
            self.val_port1.SetValue("N/A")
            self.val_port2.SetValue("N/A")
            self.val_count.SetValue("N/A")
            self.val_gray.SetValue("N/A")
            self.val_bin.SetValue("N/A")
            self.val_dec.SetValue("N/A")
            self.val_ang.SetValue("N/A")
            self.val_dms.SetValue("N/A")

    def Destroy(self):
        self.timer.Stop()
        return super().Destroy()





STATE_CONNECTED  = "CONNECTED"
STATE_RECOVERING = "RECOVERING"


class EncoderController(MainFrame):
    """
    Subclasses MainFrame, hooks up callbacks, and implements state machine
    transitions for automatic connection lifecycle and real-time acquisition.
    """

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self._cfg = cfg
        self._service = EncoderService(cfg)

        self._state = STATE_RECOVERING
        self._consecutive_failures = 0
        self._heartbeat_ticks = 0
        self._last_valid_live: LiveReading | None = None
        self._eng_diag_visible = False
        self._success_reads_count = 0
        self._failed_reads_count = 0

        self._read_timer = wx.Timer(self)
        self._recovery_timer = wx.Timer(self)
        self._clock_timer = wx.Timer(self)

        self._bind_events()
        self._set_initial_state()
        self._clock_timer.Start(1000)

        log.info("Application Started")

        wx.CallAfter(self._attempt_connect)

    def _bind_events(self) -> None:
        self.Bind(wx.EVT_MENU, self._on_save_reading,     self.miSaveReading)
        self.Bind(wx.EVT_MENU, self._on_export_log,       self.miExportLog)
        self.Bind(wx.EVT_MENU, self._on_clear_log,        self.miClearLog)
        self.Bind(wx.EVT_MENU, self._on_exit,             self.miExit)
        self.Bind(wx.EVT_MENU, self._on_reconnect_now,    self.miReconnectNow)
        self.Bind(wx.EVT_MENU, self._on_connection_details, self.miConnectionDetails)
        self.Bind(wx.EVT_MENU, self._on_preferences,      self.miPreferences)
        self.Bind(wx.EVT_MENU, self._on_toggle_eng_diag,  self.miToggleEngDiag)
        self.Bind(wx.EVT_MENU, self._on_hardware_info,     self.miHardwareInfo)
        self.Bind(wx.EVT_MENU, self._on_live_diagnostics,  self.miLiveDiagnostics)
        self.Bind(wx.EVT_MENU, self._on_connection_test,   self.miConnectionTest)
        self.Bind(wx.EVT_MENU, self._on_about,            self.miAbout)
        self.Bind(wx.EVT_TIMER, self._dispatch_timer)
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _dispatch_timer(self, evt: wx.TimerEvent) -> None:
        timer = evt.GetTimer()
        if timer is self._read_timer:
            self._on_read_tick()
        elif timer is self._recovery_timer:
            self._on_recovery_tick()
        elif timer is self._clock_timer:
            self._on_clock_tick()

    def _set_initial_state(self) -> None:
        self.lblReadIntervalDiag.SetLabel(f"{self._cfg.read_interval_ms} ms")
        self._set_status_bar("Initializing driver...")
        self._set_indicators(CLR_GREY, CLR_GREY, CLR_GREY, CLR_GREY)
        self.lblAcquisition.SetLabel("Acquisition : Stopped")
        
        
        self.lblDetectedCard.SetLabel("\u2014")
        self.lblCardId.SetLabel("\u2014")
        self.lblBoardNumber.SetLabel("\u2014")
        self.lblDriverStatus.SetLabel("Not Loaded")
        self.lblDllStatus.SetLabel("Not Loaded")
        self.lblDllVersion.SetLabel("\u2014")
        self.lblConnectionStatus.SetLabel("Disconnected")
        self.lblActiveConnector.SetLabel("\u2014")
        self.lblPortMapping.SetLabel("\u2014")
        self.lblPciBus.SetLabel("\u2014")
        self.lblPciDevice.SetLabel("\u2014")
        self.lblIrqNumber.SetLabel("\u2014")
        self.lblVendorId.SetLabel("\u2014")
        self.lblDeviceId.SetLabel("\u2014")

    def _attempt_connect(self) -> None:
        self._set_status_bar("Connecting...")
        self._set_indicators(CLR_AMBER, CLR_GREY, CLR_GREY, CLR_GREY)

        ok = self._service.connect(log_cb=self._log)

        if ok:
            if self._service.encoder_present:
                self._enter_connected()
            else:
                self._enter_connected_missing_encoder()
        else:
            self._log("Hardware Connection Failed")
            self._log("Waiting for Auto-Reconnect...")
            self._enter_recovery("Initial connection failed")

    def _enter_connected(self) -> None:
        self._state = STATE_CONNECTED
        self._consecutive_failures = 0
        model = self._service.model_name or "PIO-D144"
        board = self._service.board_number
        active_conn = self._service._hw.active_connector
        p_low = self._service._hw.port_low
        p_high = self._service._hw.port_high
        p_msb = self._service._hw.port_msb
        info = self._service._hw.card_info
        dll_ver = self._service.dll_version_hex

        self._set_indicators(CLR_GREEN, CLR_GREEN, CLR_AMBER, CLR_GREEN)
        self.lblDriver.SetLabel("Driver : Loaded")
        self.lblCard.SetLabel(f"Card : Connected (Board {board})")
        self.lblEncoder.SetLabel("Encoder : Waiting")
        self.lblAcquisition.SetLabel("Acquisition : Running")

        
        self.lblDetectedCard.SetLabel(model)
        self.lblCardId.SetLabel(str(info.get("card_id", "N/A")))
        self.lblBoardNumber.SetLabel(str(board))
        self.lblDriverStatus.SetLabel("Loaded")
        self.lblDllStatus.SetLabel("Loaded")
        self.lblDllVersion.SetLabel(dll_ver)
        self.lblConnectionStatus.SetLabel("Connected")
        self.lblActiveConnector.SetLabel(f"Connector {active_conn}")
        self.lblPortMapping.SetLabel(f"Low:{p_low}, Mid:{p_high}, MSB:{p_msb}")
        self.lblReadIntervalDiag.SetLabel(f"{self._cfg.read_interval_ms} ms")
        self.lblPciBus.SetLabel(str(info.get("bus_no", "N/A")))
        self.lblPciDevice.SetLabel(str(info.get("dev_no", "N/A")))
        self.lblIrqNumber.SetLabel(str(info.get("irq", "N/A")))
        
        vendor_val = info.get("vendor_id", 0)
        device_val = info.get("device_id", 0)
        self.lblVendorId.SetLabel(f"0x{vendor_val:04X}" if vendor_val else "N/A")
        self.lblDeviceId.SetLabel(f"0x{device_val:04X}" if device_val else "N/A")

        self._log(f"Connected — {model}, board {board}, Connector {active_conn}. Acquisition started.")
        self._set_status_bar("Reading Encoder...")
        log.info("Driver Loaded")
        log.info("Card Connected: %s (board %d)", model, board)
        log.info("Acquisition Started (interval=%d ms, Connector %d)", self._cfg.read_interval_ms, active_conn)

        self._read_timer.Start(self._cfg.read_interval_ms)

    def _enter_connected_missing_encoder(self) -> None:
        self._state = STATE_CONNECTED
        self._consecutive_failures = 0
        model = self._service.model_name or "PIO-D144"
        board = self._service.board_number
        info = self._service._hw.card_info
        dll_ver = self._service.dll_version_hex

        
        self._set_indicators(CLR_GREEN, CLR_GREEN, CLR_RED, CLR_RED)
        self.lblDriver.SetLabel("Driver : Loaded")
        self.lblCard.SetLabel(f"Card : Connected (Board {board})")
        self.lblEncoder.SetLabel("Encoder : No Signal")
        self.lblAcquisition.SetLabel("Acquisition : Stopped")

        
        self.lblDetectedCard.SetLabel(model)
        self.lblCardId.SetLabel(str(info.get("card_id", "N/A")))
        self.lblBoardNumber.SetLabel(str(board))
        self.lblDriverStatus.SetLabel("Loaded")
        self.lblDllStatus.SetLabel("Loaded")
        self.lblDllVersion.SetLabel(dll_ver)
        self.lblConnectionStatus.SetLabel("Connected")
        self.lblActiveConnector.SetLabel("N/A")
        self.lblPortMapping.SetLabel("N/A")
        self.lblReadIntervalDiag.SetLabel(f"{self._cfg.read_interval_ms} ms")
        self.lblPciBus.SetLabel(str(info.get("bus_no", "N/A")))
        self.lblPciDevice.SetLabel(str(info.get("dev_no", "N/A")))
        self.lblIrqNumber.SetLabel(str(info.get("irq", "N/A")))
        
        vendor_val = info.get("vendor_id", 0)
        device_val = info.get("device_id", 0)
        self.lblVendorId.SetLabel(f"0x{vendor_val:04X}" if vendor_val else "N/A")
        self.lblDeviceId.SetLabel(f"0x{device_val:04X}" if device_val else "N/A")

        self._set_status_bar("PCI Connected — No Encoder Found")
        
        
        if self._read_timer.IsRunning():
            self._read_timer.Stop()
        if not self._recovery_timer.IsRunning():
            self._recovery_timer.Start(self._cfg.reconnect_retry_ms)

    def _on_read_tick(self) -> None:
        try:
            live: LiveReading = self._service.get_reading()
            self._consecutive_failures = 0
            self._success_reads_count += 1
            self._last_valid_live = live
            self._populate_fields(live)
            self.lblEncoder.SetLabel("Encoder : Reading")
            self.ledEncoder.set_colour(CLR_GREEN)
            self._heartbeat_log(live)

        except ConnectionError as exc:
            self._failed_reads_count += 1
            self._register_read_failure(str(exc))
        except (IOError, ValueError) as exc:
            self._failed_reads_count += 1
            self._register_read_failure(str(exc))
        except Exception as exc:
            self._failed_reads_count += 1
            log.exception("Unexpected read error")
            self._register_read_failure(str(exc))

    def _register_read_failure(self, reason: str) -> None:
        self._consecutive_failures += 1
        log.error("Read Failure (%d consecutive): %s",
                   self._consecutive_failures, reason)
        self.ledEncoder.set_colour(CLR_AMBER)
        self.lblEncoder.SetLabel("Encoder : No Signal")

        if self._consecutive_failures >= self._cfg.max_consecutive_failures:
            self._enter_recovery(reason)

    def _populate_fields(self, live: LiveReading) -> None:
        r = live.reading
        self.txtGrayCode.SetValue(r.gray_code)
        self.txtBinary.SetValue(r.binary)
        self.txtHex.SetValue(r.hex_value)
        self.txtDecimal.SetValue(str(r.decimal))
        self.txtAngle.SetValue(f"{r.angle_deg:.6f}\u00b0")
        self.txtDMS.SetValue(r.dms_str)
        self.txtDirection.SetValue(live.direction)

        self.lblReadRate.SetLabel(
            f"{live.measured_hz:.1f} Hz" if live.measured_hz > 0 else "\u2014"
        )
        self.lblLastValidReading.SetLabel(f"{r.angle_deg:.4f}\u00b0  ({r.gray_code})")
        self.lblLastUpdate.SetLabel(live.timestamp.strftime("%H:%M:%S.%f")[:-3])

        p0, p1, p2 = live.raw_ports
        self.lblRawPort0.SetLabel(f"0x{p0:02X}")
        self.lblRawPort1.SetLabel(f"0x{p1:02X}")
        self.lblRawPort2.SetLabel(f"0x{p2:02X}")
        self.lblCombined17Bit.SetLabel(f"0x{r.decimal:05X}  ({r.binary})")
        self.lblGrayCodeDiag.SetLabel(r.gray_code)

    def _enter_recovery(self, reason: str) -> None:
        if self._state == STATE_RECOVERING and self._recovery_timer.IsRunning():
            return

        self._state = STATE_RECOVERING
        if self._read_timer.IsRunning():
            self._read_timer.Stop()

        self._set_indicators(CLR_RED, CLR_RED, CLR_RED, CLR_AMBER)
        self.lblDriver.SetLabel("Driver : Not Loaded")
        self.lblCard.SetLabel("Card : Not Connected")
        self.lblEncoder.SetLabel("Encoder : No Signal")
        self.lblAcquisition.SetLabel("Acquisition : Recovering")

        
        self.lblConnectionStatus.SetLabel("Disconnected")
        self.lblDriverStatus.SetLabel("Not Loaded")
        self.lblDllStatus.SetLabel("Not Loaded")
        self.lblActiveConnector.SetLabel("\u2014")
        self.lblPortMapping.SetLabel("\u2014")
        self.lblPciBus.SetLabel("\u2014")
        self.lblPciDevice.SetLabel("\u2014")
        self.lblIrqNumber.SetLabel("\u2014")
        self.lblVendorId.SetLabel("\u2014")
        self.lblDeviceId.SetLabel("\u2014")

        self._log(f"Connection Lost: {reason}")
        self._set_status_bar("Connection Lost \u2014 attempting automatic recovery...")
        log.error("Connection Lost: %s", reason)

        self._service.disconnect()
        if not self._recovery_timer.IsRunning():
            self._recovery_timer.Start(self._cfg.reconnect_retry_ms)

    def _on_recovery_tick(self) -> None:
        self._log("Reconnecting automatically...")
        log.info("Reconnect (automatic recovery attempt)")

        ok = self._service.connect(log_cb=self._log)
        if ok:
            if self._service.encoder_present:
                self._recovery_timer.Stop()
                self._enter_connected()
            else:
                self._enter_connected_missing_encoder()

    def _log(self, message: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.txtStatus.AppendText(f"[{ts}]  {message}\n")
        
        
        num_lines = self.txtStatus.GetNumberOfLines()
        if num_lines > 1000:
            val = self.txtStatus.GetValue()
            lines = val.splitlines()
            if len(lines) > 1000:
                self.txtStatus.SetValue("\n".join(lines[-1000:]) + "\n")
                self.txtStatus.SetInsertionPointEnd()

    def _set_status_bar(self, message: str) -> None:
        self.SetStatusText(message)

    def _set_indicators(self, driver: tuple, card: tuple, encoder: tuple,
                         acquisition: tuple) -> None:
        self.ledDriver.set_colour(driver)
        self.ledCard.set_colour(card)
        self.ledEncoder.set_colour(encoder)
        self.ledAcquisition.set_colour(acquisition)

    def _heartbeat_log(self, live: LiveReading) -> None:
        if self._heartbeat_ticks % HEARTBEAT_INTERVAL_S == 0:
            log.info(
                "Read Success: count=%d angle=%.4f dir=%s rate=%.1fHz",
                live.reading.decimal, live.reading.angle_deg,
                live.direction, live.measured_hz,
            )

    def _on_clear_log(self, _evt) -> None:
        self.txtStatus.SetValue("Ready...\n")
        log.debug("Event log cleared by user")

    def _on_reconnect_now(self, _evt) -> None:
        if self._read_timer.IsRunning():
            self._read_timer.Stop()
        if self._recovery_timer.IsRunning():
            self._recovery_timer.Stop()

        self._service.disconnect()
        self._log("Reconnect requested by user.")
        self._set_status_bar("Connecting...")
        log.info("Reconnect (manual, requested by user)")
        self._attempt_connect()

    def _on_connection_details(self, _evt) -> None:
        lines = [
            f"State:          {self._state}",
            f"Board Number:   {self.lblBoardNumber.GetLabel()}",
            f"Detected Card:  {self.lblDetectedCard.GetLabel()}",
            f"Input Ports:    {self.lblPortMapping.GetLabel()}",
            f"DLL Version:    {self.lblDllVersion.GetLabel()}",
            f"Read Interval:  {self._cfg.read_interval_ms} ms",
            f"Read Rate:      {self.lblReadRate.GetLabel()}",
        ]
        wx.MessageBox("\n".join(lines), "Connection Details",
                       wx.OK | wx.ICON_INFORMATION, self)

    def _on_save_reading(self, _evt) -> None:
        """Save the current encoder reading to a user-selected CSV file."""
        if not self._last_valid_live:
            wx.MessageBox(
                "No valid encoder reading available to save.",
                "No Data",
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return

        with wx.FileDialog(
            self,
            "Save Current Reading",
            wildcard="CSV files (*.csv)|*.csv",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return

            path = file_dialog.GetPath()
            try:
                live = self._last_valid_live
                r = live.reading
                with open(path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Timestamp", "Gray Code", "Binary", "Hexadecimal",
                        "Decimal Count", "Angle (Deg)", "DMS", "Direction"
                    ])
                    writer.writerow([
                        live.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        r.gray_code,
                        r.binary,
                        r.hex_value,
                        r.decimal,
                        f"{r.angle_deg:.6f}",
                        r.dms_str,
                        live.direction
                    ])
                self._log(f"Current reading saved to {os.path.basename(path)}")
                log.info("Reading saved to %s", path)
            except Exception as exc:
                log.exception("Failed to save reading to CSV")
                wx.MessageBox(
                    f"Failed to save file:\n{exc}",
                    "Error",
                    wx.OK | wx.ICON_ERROR,
                    self,
                )

    def _on_export_log(self, _evt) -> None:
        """Export the current event log to a text file."""
        log_text = self.txtStatus.GetValue()
        with wx.FileDialog(
            self,
            "Export Event Log",
            wildcard="Text files (*.txt)|*.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return

            path = file_dialog.GetPath()
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(log_text)
                self._log(f"Event log exported to {os.path.basename(path)}")
                log.info("Event log exported to %s", path)
            except Exception as exc:
                log.exception("Failed to export event log")
                wx.MessageBox(
                    f"Failed to export log:\n{exc}",
                    "Error",
                    wx.OK | wx.ICON_ERROR,
                    self,
                )

    def _on_preferences(self, _evt) -> None:
        log.info("Menu action: Settings > Preferences")
        dlg = wx.Dialog(self, title="Settings", size=wx.Size(440, 340))
        panel = wx.Panel(dlg)
        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=6, cols=2, vgap=10, hgap=10)
        grid.AddGrowableCol(1)

        
        grid.Add(wx.StaticText(panel, label="Acquisition Interval (ms):"),
                  0, wx.ALIGN_CENTER_VERTICAL)
        interval_ctrl = wx.SpinCtrl(
            panel, min=MIN_READ_INTERVAL_MS, max=60000,
            initial=self._cfg.read_interval_ms,
        )
        grid.Add(interval_ctrl, 1, wx.EXPAND)

        
        grid.Add(wx.StaticText(panel, label="Reconnect Retry (ms):"),
                  0, wx.ALIGN_CENTER_VERTICAL)
        reconnect_ctrl = wx.SpinCtrl(
            panel, min=500, max=60000,
            initial=self._cfg.reconnect_retry_ms,
        )
        grid.Add(reconnect_ctrl, 1, wx.EXPAND)

        
        grid.Add(wx.StaticText(panel, label="Calibration Offset (\u00b0):"),
                  0, wx.ALIGN_CENTER_VERTICAL)
        offset_ctrl = wx.TextCtrl(panel, value=f"{self._cfg.calibration_offset:.4f}")
        grid.Add(offset_ctrl, 1, wx.EXPAND)

        
        grid.Add(wx.StaticText(panel, label="Max Read Failures:"),
                  0, wx.ALIGN_CENTER_VERTICAL)
        max_failures_ctrl = wx.SpinCtrl(
            panel, min=1, max=100,
            initial=self._cfg.max_consecutive_failures,
        )
        grid.Add(max_failures_ctrl, 1, wx.EXPAND)

        
        grid.Add(wx.StaticText(panel, label="Active Connector:"),
                  0, wx.ALIGN_CENTER_VERTICAL)
        connector_options = [
            "Auto Detect",
            "Connector 1",
            "Connector 2",
            "Connector 3",
            "Connector 4",
            "Connector 5",
            "Connector 6"
        ]
        current_conn = self._cfg.connector.strip().lower()
        initial_conn = "Auto Detect"
        if current_conn in ("1", "2", "3", "4", "5", "6"):
            initial_conn = f"Connector {current_conn.upper()}"
        conn_ctrl = wx.ComboBox(
            panel, choices=connector_options, style=wx.CB_READONLY,
            value=initial_conn
        )
        grid.Add(conn_ctrl, 1, wx.EXPAND)

        
        grid.Add(wx.StaticText(panel, label="Log Level:"),
                  0, wx.ALIGN_CENTER_VERTICAL)
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        current_level = self._cfg.log_level.upper()
        if current_level not in log_levels:
            current_level = "DEBUG"
        level_ctrl = wx.ComboBox(
            panel, choices=log_levels, style=wx.CB_READONLY,
            value=current_level
        )
        grid.Add(level_ctrl, 1, wx.EXPAND)

        vbox.Add(grid, 0, wx.EXPAND | wx.ALL, 14)

        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        restore_btn = wx.Button(panel, label="Restore Defaults")
        btn_sizer.Add(restore_btn, 0, wx.RIGHT, 10)
        
        btn_sizer.AddStretchSpacer()
        
        ok_btn = wx.Button(panel, wx.ID_OK, "Save")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        btn_sizer.Add(ok_btn, 0, wx.RIGHT, 5)
        btn_sizer.Add(cancel_btn, 0)
        
        vbox.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        panel.SetSizer(vbox)

        
        def _on_restore_defaults(event):
            interval_ctrl.SetValue(DEFAULT_READ_INTERVAL_MS)
            reconnect_ctrl.SetValue(DEFAULT_RECONNECT_RETRY_MS)
            offset_ctrl.SetValue("0.0000")
            max_failures_ctrl.SetValue(DEFAULT_MAX_CONSECUTIVE_FAILURES)
            conn_ctrl.SetValue("Auto Detect")
            level_ctrl.SetValue("DEBUG")
            log.info("Settings controls restored to defaults in dialog")

        restore_btn.Bind(wx.EVT_BUTTON, _on_restore_defaults)

        dlg_sizer = wx.BoxSizer(wx.VERTICAL)
        dlg_sizer.Add(panel, 1, wx.EXPAND)
        dlg.SetSizerAndFit(dlg_sizer)

        if dlg.ShowModal() == wx.ID_OK:
            try:
                new_interval = int(interval_ctrl.GetValue())
                new_reconnect = int(reconnect_ctrl.GetValue())
                new_offset = float(offset_ctrl.GetValue())
                new_failures = int(max_failures_ctrl.GetValue())
                new_level = level_ctrl.GetValue()
                
                selected_conn = conn_ctrl.GetValue()
                if selected_conn == "Auto Detect":
                    new_conn = "auto"
                else:
                    new_conn = selected_conn.split()[-1]
            except ValueError:
                wx.MessageBox("Calibration offset must be a number.",
                               "Invalid input", wx.OK | wx.ICON_ERROR, self)
                dlg.Destroy()
                return

            self._cfg.set_read_interval_ms(new_interval)
            self._cfg.set_reconnect_retry_ms(new_reconnect)
            self._cfg.set_calibration_offset(new_offset)
            self._cfg.set_max_consecutive_failures(new_failures)
            self._cfg.set_connector(new_conn)
            self._cfg.set_log_level(new_level)

            self.lblReadIntervalDiag.SetLabel(f"{self._cfg.read_interval_ms} ms")

            
            self._service._hw._connector_setting = new_conn

            if self._read_timer.IsRunning():
                self._read_timer.Stop()
                self._read_timer.Start(self._cfg.read_interval_ms)

            if self._recovery_timer.IsRunning():
                self._recovery_timer.Stop()
                self._recovery_timer.Start(self._cfg.reconnect_retry_ms)

            self._log(
                f"Preferences updated: interval={self._cfg.read_interval_ms} ms, "
                f"reconnect={self._cfg.reconnect_retry_ms} ms, "
                f"offset={self._cfg.calibration_offset:.4f}\u00b0, "
                f"max_failures={self._cfg.max_consecutive_failures}, "
                f"connector={new_conn}, "
                f"log_level={self._cfg.log_level}"
            )
        dlg.Destroy()

    def _on_toggle_eng_diag(self, _evt) -> None:
        self._eng_diag_visible = self.miToggleEngDiag.IsChecked()
        self.set_engineering_diagnostics_visible(self._eng_diag_visible)
        log.debug("Engineering diagnostics panel visibility: %s", self._eng_diag_visible)

    def _on_hardware_info(self, _evt) -> None:
        log.info("Menu action: Tools > Hardware Information")
        is_dll_loaded = "Yes" if self._service._hw._api.is_loaded else "No"
        driver_status = "Initialised" if self._service._hw._api.is_loaded else "Failed to Load DLL"
        conn_status = "Connected" if self._service.is_connected() else "Not Connected"
        rate_hz = f"{self._last_valid_live.measured_hz:.1f} Hz" if (self._last_valid_live and self._service.is_connected()) else "0.0 Hz"
        
        info_lines = [
            f"Card Model:                  {self._service.model_name or 'PIO-D144'}",
            f"Card ID (Board No):          {self._service.board_number}",
            f"UniDAQ Driver Status:        {driver_status}",
            f"UniDAQ.dll Loaded:           {is_dll_loaded}",
            f"Connection Status:           {conn_status}",
            f"Acquisition Rate (Hz):       {rate_hz}",
            f"Read Interval:               {self._cfg.read_interval_ms} ms",
            f"Total Successful Reads:      {self._success_reads_count}",
            f"Total Failed Reads:          {self._failed_reads_count}",
            f"Application Version:         {APP_VERSION}",
        ]
        
        wx.MessageBox(
            "\n".join(info_lines),
            "Hardware Information",
            wx.OK | wx.ICON_INFORMATION,
            self
        )

    def _on_live_diagnostics(self, _evt) -> None:
        log.info("Menu action: Tools > Live Diagnostics")
        dlg = LiveDiagnosticsDialog(self, self)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_connection_test(self, _evt) -> None:
        log.info("Menu action: Tools > Connection Test")
        report = []
        success = True
        
        
        report.append("1. Loading UniDAQ.dll...")
        test_api = UniDaqBindings(self._cfg.dll_name)
        try:
            test_api.load()
            report.append("   [SUCCESS] DLL loaded successfully.")
        except Exception as exc:
            report.append(f"   [FAILED] Failed to load DLL: {exc}")
            success = False

        if success:
            
            report.append("\n2. Initializing driver...")
            try:
                boards = test_api.driver_init()
                report.append(f"   [SUCCESS] Driver initialised. Found {boards} compatible board(s).")
                if boards <= 0:
                    report.append("   [FAILED] No compatible cards found.")
                    success = False
            except Exception as exc:
                report.append(f"   [FAILED] Driver init crashed: {exc}")
                success = False

        if success:
            
            report.append("\n3. Detecting PIO-D144 Card...")
            board_found = -1
            for b in range(boards):
                try:
                    info = test_api.get_card_info(b)
                    if BOARD_MODEL_HINT in info["model_name"]:
                        board_found = b
                        report.append(f"   [SUCCESS] Card detected at Board ID {b} (Model: {info['model_name']}).")
                        break
                except Exception as exc:
                    report.append(f"   [WARNING] Error querying Board {b}: {exc}")
            if board_found == -1:
                report.append("   [FAILED] No board matching PIO-D144 was found.")
                success = False

        if success:
            
            report.append("\n4. Reading sample from digital input ports...")
            try:
                test_api.set_dio_mode(board_found, self._cfg.port_low, False)
                test_api.set_dio_mode(board_found, self._cfg.port_high, False)
                test_api.set_dio_mode(board_found, self._cfg.port_msb, False)
                
                b0 = test_api.read_di(board_found, self._cfg.port_low)
                b1 = test_api.read_di(board_found, self._cfg.port_high)
                b2 = test_api.read_di(board_found, self._cfg.port_msb)
                count = ((b2 & 0x01) << 16) | (b1 << 8) | b0
                report.append("   [SUCCESS] Successfully read port inputs:")
                report.append(f"             Port Low (0):  0x{b0:02X}")
                report.append(f"             Port High (1): 0x{b1:02X}")
                report.append(f"             Port MSB (2):  0x{b2:02X}")
                report.append(f"             Reconstructed Count: {count}")
            except Exception as exc:
                report.append(f"   [FAILED] Failed to read sample: {exc}")
                success = False

        
        if 'boards' in locals() and boards > 0:
            try:
                test_api.driver_close()
                report.append("\n5. Releasing driver resources... [SUCCESS]")
            except Exception as exc:
                report.append(f"\n5. Releasing driver resources... [FAILED]: {exc}")

        
        report.append("\n" + "="*40)
        if success:
            report.append("OVERALL TEST STATUS: PASSED")
            icon = wx.ICON_INFORMATION
        else:
            report.append("OVERALL TEST STATUS: FAILED")
            icon = wx.ICON_ERROR

        wx.MessageBox(
            "\n".join(report),
            "Connection Test Report",
            wx.OK | icon,
            self
        )

    def _on_about(self, _evt) -> None:
        log.info("Menu action: Help > About")
        import platform
        py_ver = sys.version.split()[0]
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        message = (
            "Application Name:\n"
            "17-Bit Absolute Encoder Data Acquisition System\n\n"
            f"Version:\n{APP_VERSION}\n\n"
            "Developer:\nSam Punitha Raj D\n\n"
            "Internship:\nIndian Institute of Astrophysics, Vainu Bappu Observatory\n\n"
            "Mentor:\nMrs. Vellai Selvi, Engineer D\n\n"
            "Hardware:\nPIO-D144 PCI Digital I/O Card, UniDAQ Driver, 17-Bit Absolute Encoder\n\n"
            f"GUI Framework:\nwxPython {wx.__version__}\n\n"
            f"Python Version:\n{py_ver}\n\n"
            f"Operating System:\n{os_info}"
        )
        wx.MessageBox(message, "About", wx.OK | wx.ICON_INFORMATION, self)

    def _on_exit(self, _evt) -> None:
        self.Close()

    def _on_close(self, evt: wx.CloseEvent) -> None:
        self._set_status_bar("Stopping...")
        for timer in (self._clock_timer, self._read_timer, self._recovery_timer):
            if timer.IsRunning():
                timer.Stop()
        self._service.disconnect()
        log.info("Application Closed")
        evt.Skip()

    def _on_clock_tick(self) -> None:
        now = datetime.datetime.now()
        self.lblDate.SetLabel(now.strftime("%A, %d %B %Y"))
        self.lblTime.SetLabel(now.strftime("%H:%M:%S"))
        self._heartbeat_ticks += 1





def main() -> None:
    try:
        import wx
    except ImportError:
        print(
            "ERROR: wxPython is not installed.\n"
            "Install it with:  pip install wxPython"
        )
        sys.exit(1)

    cfg = Config()

    
    log.setLevel(getattr(logging, cfg.log_level.upper(), logging.DEBUG))

    log.info("=" * 60)
    log.info("%s  v%s", APP_NAME, APP_VERSION)
    log.info("Startup  interval=%d ms  board_number=%d (config.ini)",
              cfg.read_interval_ms, cfg.board_number)

    app = wx.App(False)
    try:
        frame = EncoderController(cfg)
        frame.Maximize(True)  
        frame.Show()
        app.MainLoop()
    except Exception as exc:
        log.exception("Fatal application error: %s", exc)
        wx.MessageBox(
            f"A fatal error occurred and the application must close.\n\n{exc}",
            "Fatal Error",
            wx.OK | wx.ICON_ERROR,
        )
        sys.exit(1)
    finally:
        log.info("Application exit")
        log.info("=" * 60)
        logging.shutdown()


if __name__ == "__main__":
    main()
