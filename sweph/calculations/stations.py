# sweph/calculations/retro.py
# ruff: noqa: E402, E701
import swisseph as swe  # type:ignore
from ui.helpers import _object_name_to_code as objcode
from sweph.constants import STATION_SPEED, RETRO_DAYS

last_stations = {}


def get_retro_phases(body, jd_ut, sweph_flag):
    if body in (0, 1):
        return " "
    curr_speed = lon_speed(body, jd_ut, sweph_flag)
    if body in (10, 11):
        return "r" if curr_speed < 0 else " "
    # used in positions.py & tables todo ???
    treshold = STATION_SPEED.get(body, 0)
    if abs(curr_speed) < treshold:
        speed_next = lon_speed(body, jd_ut + 0.1, sweph_flag)
        if speed_next < curr_speed:
            return "sr"
        return "sd"
    return "r" if curr_speed < 0 else " "


def lon_speed(body, jd_ut, sweph_flag):
    # calculate lon speed in degree/day
    result = swe.calc_ut(jd_ut, body, sweph_flag)
    # longitude speed
    return result[0][3]


def refine_root(body, bracket, sweph_flag):
    # fast exact direction change calculation
    a, b = bracket
    fa = lon_speed(body, a, sweph_flag)
    fb = lon_speed(body, b, sweph_flag)
    # bisect
    for _ in range(10):
        m = 0.5 * (a + b)
        fm = lon_speed(body, m, sweph_flag)
        if fa * fm <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm

    # secant
    for _ in range(5):
        denom = fb - fa
        if denom == 0:
            break
        m = (a * fb - b * fa) / denom
        if not (a < m < b):
            break
        fm = lon_speed(body, m, sweph_flag)
        if fa * fm <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


def find_closest_station(body, start_jd, step, sweph_flag):
    # iterative search for nearest station
    eps = 1e-7
    t = start_jd + (eps * (1 if step > 0 else -1))
    s0 = lon_speed(body, t, sweph_flag)
    max_iter = int(365.25 * 3 / abs(step))
    for _ in range(max_iter):
        t += step
        s = lon_speed(body, t, sweph_flag)
        # sign change = station
        if s0 * s <= 0:
            return refine_root(body, (t - step, t), sweph_flag)
        s0 = s
    return None


def find_stations(body, jd, sweph_flag):
    # find previous & next station, use cache to avoid recalculation
    jd_rounded = round(jd * 86400) / 86400
    cache_key = (body, round(jd, 2))
    curr_dir = get_retro_phases(body, jd, sweph_flag)
    old_prev_s, old_next_s = last_stations.get(cache_key, (None, None))
    # cached results first
    old_prev_s, old_next_s = last_stations.get(body, (None, None))
    if old_prev_s and old_next_s:
        if old_prev_s < jd_rounded < old_next_s:
            return old_prev_s, old_next_s, curr_dir
    retro_length = RETRO_DAYS.get(body, 180.0)
    step = min(retro_length / 20.0, 0.5)
    # find previous & next station
    s_prev = find_closest_station(body, jd_rounded, -step, sweph_flag)
    s_next = find_closest_station(body, jd_rounded, step, sweph_flag)
    last_stations[cache_key] = (s_prev, s_next)

    return s_prev, s_next, curr_dir


def calculate_stations(jd_ut, sweph_flag, objs, use_mean_node):
    """calculate retro stations & direction for event"""
    # calculate direction & stations
    stations = []
    if not jd_ut:
        return stations

    for obj in objs:
        code, name = objcode(obj, use_mean_node)
        if code not in STATION_SPEED:
            continue
        # station previous & next + current direction
        s_prev, s_next, direction = find_stations(code, jd_ut, sweph_flag)
        if s_prev is None or s_next is None:
            continue
        stations.append({
            "name": name,
            "prevstation": s_prev,
            "nextstation": s_next,
            "direction": direction,
        })
    return stations
