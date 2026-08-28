# sweph/calculations/stations.py
# ruff: noqa: E402, E701
import logging as log
import swisseph as swe
from helpers import _object_name_to_code as objcode, ok, err
from sweph.constants import STATION_SPEED, RETRO_DAYS

source = "stations"
route = ["terminal"]
last_stations = {}


def get_retro_phases(body, jd_ut, flag):
    if body in (0, 1):
        return " "
    curr_speed = lon_speed(body, jd_ut, flag)
    if body in (10, 11):
        return "r" if curr_speed < 0 else " "
    # used in positions.py & tables todo ???
    treshold = STATION_SPEED.get(body, 0)
    if abs(curr_speed) < treshold:
        speed_next = lon_speed(body, jd_ut + 0.1, flag)
        if speed_next < curr_speed:
            return "sr"
        return "sd"
    return "r" if curr_speed < 0 else " "


def lon_speed(body, jd_ut, flag):
    # calculate longitude speed in degree/day
    result = swe.calc_ut(jd_ut, body, flag)
    return result[0][3]


def refine_root(body, bracket, flag):
    # fast exact direction change calculation
    a, b = bracket
    fa = lon_speed(body, a, flag)
    fb = lon_speed(body, b, flag)
    # bisect
    for _ in range(10):
        m = 0.5 * (a + b)
        fm = lon_speed(body, m, flag)
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
        fm = lon_speed(body, m, flag)
        if fa * fm <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


def find_closest_station(body, start_jd, step, flag):
    # iterative search for nearest station
    eps = 1e-7
    t = start_jd + (eps * (1 if step > 0 else -1))
    s0 = lon_speed(body, t, flag)
    max_iter = int(365.25 * 3 / abs(step))
    for _ in range(max_iter):
        t += step
        s = lon_speed(body, t, flag)
        # sign change = station
        if s0 * s <= 0:
            return refine_root(body, (t - step, t), flag)
        s0 = s
    return None


def find_stations(body, jd, flag):
    # find previous & next station, use cache to avoid recalculation
    jd_rounded = round(jd * 86400) / 86400
    cache_key = (body, flag)
    curr_dir = get_retro_phases(body, jd, flag)
    old_prev_s, old_next_s = last_stations.get(cache_key, (None, None))
    # cached results first
    # old_prev_s, old_next_s = last_stations.get(cache_key, (None, None))
    # old_prev_s, old_next_s = last_stations.get(body, (None, None))
    if old_prev_s and old_next_s:
        if old_prev_s < jd_rounded < old_next_s:
            return old_prev_s, old_next_s, curr_dir
    retro_length = RETRO_DAYS.get(body, 180.0)
    step = min(retro_length / 20.0, 0.5)
    # find previous & next station
    s_prev = find_closest_station(body, jd_rounded, -step, flag)
    s_next = find_closest_station(body, jd_rounded, step, flag)
    last_stations[cache_key] = (s_prev, s_next)

    return s_prev, s_next, curr_dir


def calculate_stations(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    # calculate retro stations & direction for event
    if jd_ut is None:
        return err("invalid jd_ut")
    p = params or {}
    use_mean_node = p.get("use_mean_node", False)
    # if topocentric calculations
    # if (flag & swe.FLG_TOPOCTR) and geo and len(geo) == 3:
    #     swe.set_topo(geo[0], geo[1], geo[2])
    stations = []
    for obj in objs:
        code, name = objcode(obj, use_mean_node)
        if code not in STATION_SPEED:
            log.error(
                "code not in stations speed",
                extra={"source": source, "route": route},
            )
            continue
        # station previous & next + current direction
        s_prev, s_next, direction = find_stations(code, jd_ut, flag)
        if s_prev is None or s_next is None:
            log.error(
                "missing previous or next station",
                extra={"source": source, "route": route},
            )
            continue
        stations.append({
            "name": name,
            "prevstation": s_prev,
            "nextstation": s_next,
            "direction": direction,
        })
    return ok(stations)
