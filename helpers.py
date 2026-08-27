# ui/helpers.py
# ruff: noqa: E402
from math import modf
from swisseph import contrib as swh
from ui.fonts.glyphs import SIGNS
from user.settings import OBJECTS
from sweph.constants import AVG_SPEEDS


def _house_for_lon(lon: float, cusps: list):
    if not cusps:
        return ""
    cusp_list = [(c, i + 1) for i, c in enumerate(cusps)]
    n = len(cusp_list)
    for i in range(n):
        c0, h0 = cusp_list[i]
        c1, _ = cusp_list[(i + 1) % n]
        if c0 <= c1:
            if c0 <= lon < c1:
                return f"{h0:2d}"
        else:
            if lon >= c0 or lon < c1:
                return f"{h0:2d}"
    return ""


def _relative_speed(code, speed: float):
    mean = AVG_SPEEDS.get(code, 1.0)
    if not mean:
        return 0
    return int(round((speed / mean) * 100))


def _decimal_to_ymd(period: float, year_length: float):
    # decimal period to years, months, days, hours
    y = int(period)
    rem_y = period - y
    dec_m = rem_y * 12
    m = int(dec_m)
    rem_m = dec_m - m
    rem_d = rem_m * (year_length / 12)
    d = int(rem_d)
    rem_h = rem_d * 24
    H = int(rem_h)
    if y != 0 and m == 0 and d == 0:
        return f"{y:02} y"
    elif y == 0 and m == 0 and d == 0:
        return f"{H:02} h"
    elif y == 0 and m == 0:
        return f"{d:02d} d"
    elif y == 0:
        return f"{m:02d} m {d:02d} d"
    return f"{y:02d} y {m:02d} m {d:02d} d"


def _decimal_to_dms(decimal: float):
    # convert decimal number to degree-minute-second
    min_, deg_ = modf(decimal)
    sec_, _ = modf(min_ * 60)
    deg = int(deg_)
    min = int(min_ * 60)
    sec = int(sec_ * 60)

    return deg, min, sec


def _decimal_to_hms(decimal: float):
    # convert decimal hour to hour
    H = int(decimal)
    M = int((decimal - H) * 60)
    S = int((decimal - H - M / 60) * 3600)
    return H, M, S


def _decimal_to_ra(decimal: float):
    # convert circle degrees into right ascension h-m-s todo used ???
    hour = decimal / 15.0
    H = int(hour)
    minute = (hour - H) * 60
    M = int(minute)
    S = int(round((minute - M) * 60))
    return H, M, S


def _object_name_to_code(name: str, use_mean_node: bool):
    # get object name as int
    if name == "true node" and use_mean_node:
        name = "mean node"
    for code, obj in OBJECTS.items():
        if obj[1] == name or obj[0] == name:
            # return int & short name
            return code, obj[0]
    if name == "mean node":
        # return mean node int & same short name as true node
        return 10, "ra"
    return None, ""


def _decimal_to_sign_dms(lon: float, use_glyph: bool = True):
    # convert lon to sign & dms
    deg, sign, min, sec = swh.degsplit(lon)
    sign_keys = list(SIGNS.keys())
    sign_key = sign_keys[sign]
    glyph = SIGNS[sign_key][0] if use_glyph else sign_key
    return f"{deg:2d}°{min:02d}'{sec:02d}\" {glyph}"


# logger : simplify message reply to dispatcher
# DISPATCHER ONLY
def ok(data=None):
    # dispatcher = caller expects below format
    return {"status": "ok", "data": data, "error": None}


def err(e):
    # dispatcher = caller expects below format
    return {"status": "error", "data": None, "error": str(e)}
