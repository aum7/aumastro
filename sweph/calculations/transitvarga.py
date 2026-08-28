# sweph/calculations/transitvarga.py
# simple division by user input
# ruff: noqa: E402, E701
import logging as log
from helpers import ok, err

source = "transitvarga"
route = ["terminal"]
routing = {"source": source, "route": route}


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


def calculate_transit_varga(jd_ut=None, objs=(), flag=0, params=None):
    # calculate planetary positions & houses & ascmc in varga chart
    # jd_ut is not needed if we receive e2 pos division houses from datamanager
    p = params or {}
    division = p.get("division")  # harmonic chart[0]
    if division and int(division) < 2:
        return err("division too small - dont send me this")
    pos = p.get("positions")  # they be e2 as this is transit
    houses = p.get("houses")
    if division is None or pos is None or houses is None:
        return err("missing e2 / transit data")
    cusps = houses.get("cusps")
    ascmc = houses.get("ascmc")
    log.debug(
        f"types : pos={type(pos)} | cusps={type(cusps)} | ascmc={type(ascmc)}",
        extra=routing,
    )
    transit_varga = []
    if isinstance(pos, dict):
        for obj in pos:  # todo fix code
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
