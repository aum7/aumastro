# sweph/calculations/positions.py
# ruff: noqa: E402, E701
import swisseph as swe
from ui.helpers import _object_name_to_code as objcode
from sweph.calculations.naksatras import calculate_naksatra
from sweph.calculations.varga import get_varga_lon
from sweph.constants import AVG_SPEEDS


def get_relative_speed(body, speed):
    avg = AVG_SPEEDS.get(body, 0)
    if avg == 0:
        return 0
    return int((speed / avg) * 100)


def get_house_for_lon(lon, cusps):
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


def calculate_positions(
    jd_ut: float,
    objs: list,
    sweph_flag: int,
    use_mean_node: bool,
    use_28_naks: bool,
    first_nak: int,
    division: int,
    topo_coords: tuple = (),
):
    if topo_coords and len(topo_coords) == 3:
        swe.set_topo(topo_coords[0], topo_coords[1], topo_coords[2])
    data = {}
    for obj in objs:
        code, name = objcode(obj, use_mean_node)
        if code is None:
            continue
        try:
            result = swe.calc_ut(jd_ut, code, sweph_flag)
            pos = result[0] if isinstance(result, tuple) else result
            naksatra = calculate_naksatra(pos[0], use_28_naks, first_nak)
            varga = get_varga_lon(pos[0], division)
            varga_nak = calculate_naksatra(varga, use_28_naks, first_nak)
            data[code] = {
                "name": name,
                "lon": pos[0],
                "lat": pos[1],
                "lon speed": pos[3],
                "naksatra": naksatra,
                "varga": varga,
                "varga naksatra": varga_nak,
                "speed relative": get_relative_speed(code, pos[3]),
            }
        except swe.Error:
            continue
    lumies = {}
    for lumine in ("su", "mo"):
        code, name = objcode(lumine, False)
        if code is None:
            continue
        try:
            result = swe.calc_ut(jd_ut, code, sweph_flag)
            pos = result[0] if isinstance(result, tuple) else result
            lumies[code] = {
                "name": name,
                "lon": pos[0],
            }
        except swe.Error:
            continue

    return {"positions": data, "lumies": lumies, "jd_ut": jd_ut}
