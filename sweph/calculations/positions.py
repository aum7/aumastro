# sweph/calculations/positions.py
# ruff: noqa: E402, E701
import logging as log
import swisseph as swe
from helpers import _object_name_to_code as objcode, _relative_speed, ok, err
from sweph.calculations.naksatras import calculate_naksatras
from sweph.calculations.transitvarga import get_varga_lon


source = "positions"
route = ["terminal"]
routing = {"source": source, "route": route}


def calculate_positions(
    jd_ut=None,
    geo=(),
    objs=(),
    flag=0,
    params=None,
):
    if jd_ut is None:
        return err("invalid jd_ut")

    p = params or {}
    use_mean_node = p.get("use_mean_node", False)
    use_28_naks = p.get("use_28_naks", False)
    first_nak = p.get("first_nak", 1)
    division = p.get("division", 1)
    # check if topocentric flag is set todo in datamanager
    # if (flag & swe.FLG_TOPOCTR) and geo and len(geo) == 3:
    #     swe.set_topo(geo[0], geo[1], geo[2])
    positions = {}
    for obj in objs:
        code, name = objcode(obj, use_mean_node)
        if code is None:
            continue
        try:
            result = swe.calc_ut(jd_ut, code, flag)
            pos = result[0] if isinstance(result, tuple) else result
            naksatra = calculate_naksatras(pos[0], use_28_naks, first_nak)
            varga = get_varga_lon(pos[0], division)
            varga_nak = calculate_naksatras(varga, use_28_naks, first_nak)
            positions[code] = {
                "name": name,
                "lon": pos[0],
                "lat": pos[1],
                "lon speed": pos[3],
                "naksatra": naksatra,
                "varga": varga,
                "varga naksatra": varga_nak,
                "speed relative": _relative_speed(code, pos[3]),
            }
        except swe.Error as e:
            log.error(
                f"positions calculations error : {e}",
                extra=routing,
            )
            continue
    lumies = {}
    for lumine in ("su", "mo"):
        code, name = objcode(lumine, False)
        if code is None:
            continue
        try:
            result = swe.calc_ut(jd_ut, code, flag)
            pos = result[0] if isinstance(result, tuple) else result
            lumies[code] = {
                "name": name,
                "lon": pos[0],
            }
        except swe.Error as e:
            log.error(
                f"lumies calculation error : {e}",
                extra=routing,
            )
            continue

    return ok({"positions": positions, "lumies": lumies})
