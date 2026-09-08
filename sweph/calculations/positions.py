# sweph/calculations/positions.py
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "positions"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import _object_name_to_code as objcode, _relative_speed, ok, err
from sweph.calculations.naksatras import get_naksatra
from sweph.calculations.transitvarga import get_varga_lon


def calculate_positions(jd_ut, objs, flag, mean_node, mans_28, first_nak, division):
    # let dispatcher worry about delivering proper data
    if jd_ut is None:
        return err("invalid jd_ut")
    positions = {}
    for obj in objs:
        code, name = objcode(obj, mean_node)
        if code is None:
            return err("unknown object code")
        try:
            result = swe.calc_ut(jd_ut, code, flag)
            # todo we know our data
            positions = result[0]
            naksatra = get_naksatra(positions[0], mans_28, first_nak)
            varga = get_varga_lon(positions[0], division)
            varga_nak = get_naksatra(varga, mans_28, first_nak)
            positions[code] = {
                "name": name,
                "lon": positions[0],
                "lat": positions[1],
                "lon speed": positions[3],
                "naksatra": naksatra,
                "varga": varga,
                "varga naksatra": varga_nak,
                "speed relative": _relative_speed(code, positions[3]),
            }
        except swe.Error as e:
            LOG.error(
                f"positions calculations error : {e}",
                extra=routing,
            )
            return err(e)

    return ok({"positions": positions})
