# sweph/calculations/transitvarga.py
# simple division by user input
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "transitvarga"
routing = {"source": source, "route": ["terminal"]}
from helpers import ok, err


def get_varga_lon(lon, division=9):
    try:
        division = int(division)
    except (ValueError, TypeError):
        return lon
    # actual division requires integer > 1 todo not needed datamanager cares
    # if division <= 1:
    #     return lon
    sign = int(lon // 30)
    seg = int((lon % 30) // (30 / division))
    varga_sign = (sign * division + seg) % 12
    varga = (varga_sign * 30) + ((lon % (30 / division)) * division)
    return varga


def calculate_transit_varga(positions, houses, division):
    # calculate planetary positions & houses & ascmc in varga chart
    # jd_ut is not needed if we receive e2 pos division houses from datamanager
    division = division  # harmonic chart[0]
    if division and int(division) < 2:
        return err("division too small - dont send me this")
    positions = positions  # they be e2 as this is transit
    houses = houses  # also e2 houses
    if division is None or positions is None or houses is None:
        return err("missing e2 / transit data")
    cusps = houses.get("cusps")
    ascmc = houses.get("ascmc")
    LOG.debug(
        f"types : pos={type(positions)} | cusps={type(cusps)} | ascmc={type(ascmc)}",
        extra=routing,
    )
    transit_varga = []
    if isinstance(positions, dict):
        for obj in positions:  # todo fix code
            name = obj.get("name", "")
            lon = obj.get("lon", 0.0)
            varga = get_varga_lon(lon, division)
            transit_varga.append({"name": name, "lon": varga})
    # add asc & mc from houses / ascmc
    if cusps and isinstance(cusps, (list, tuple)):  # todo or dict ???
        for obj in cusps:  # todo fix code
            name = obj.get("name", "")
            lon = obj.get("lon", 0.0)
            varga = get_varga_lon(lon, division)
            transit_varga.append({"name": name, "lon": varga})
    if ascmc and len(ascmc) >= 2:
        asc = get_varga_lon(ascmc[0], division)
        mc = get_varga_lon(ascmc[1], division)
        transit_varga.append({"name": "asc", "lon": asc})
        transit_varga.append({"name": "mc", "lon": mc})

    return ok(transit_varga)
