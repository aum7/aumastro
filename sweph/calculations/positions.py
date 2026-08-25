# sweph/calculations/positions.py
# ruff: noqa: E402, E701
import swisseph as swe
from ui.helpers import _object_name_to_code as objcode, _relative_speed
from sweph.calculations.naksatras import calculate_naksatra
from sweph.calculations.varga import get_varga_lon


def calculate_positions(
    jd_ut,
    geo=(),
    objs=(),
    flags=0,
    params=None,
):
    if jd_ut is None:
        return {"status": "error", "data": {}, "error": "invalid jd_ut"}

    p = params or {}
    use_mean_node = p.get("use_mean_node", False)
    use_28_naks = p.get("use_28_naks", False)
    first_nak = p.get("first_nak", 1)
    division = p.get("division", 1)
    # check if topocentric flag is set
    if (flags & swe.FLG_TOPOCTR) and geo and len(geo) == 3:
        swe.set_topo(geo[0], geo[1], geo[2])
    # if topo_coords and len(topo_coords) == 3:
    # swe.set_topo(topo_coords[0], topo_coords[1], topo_coords[2])
    data = {}
    for obj in objs:
        code, name = objcode(obj, use_mean_node)
        if code is None:
            continue
        try:
            result = swe.calc_ut(jd_ut, code, flags)
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
                "speed relative": _relative_speed(code, pos[3]),
            }
        except swe.Error:
            continue
    lumies = {}
    for lumine in ("su", "mo"):
        code, name = objcode(lumine, False)
        if code is None:
            continue
        try:
            result = swe.calc_ut(jd_ut, code, flags)
            pos = result[0] if isinstance(result, tuple) else result
            lumies[code] = {
                "name": name,
                "lon": pos[0],
            }
        except swe.Error:
            continue

    return {
        "status": "ok",
        "data": {"positions": data, "lumies": lumies, "jd_ut": jd_ut},
        "error": None,
    }
