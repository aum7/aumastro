# sweph/calculations/transitvarga.py
# simple division by user input
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "transitvarga"
routing = {"source": source, "route": ["terminal"]}
from helpers import ok, err


def get_varga_lon(lon, division):
    # LOG.debug(f"getvargalon : division={division} type={type(division)}")
    if division <= 1:
        return None
    sign = int(lon // 30)
    seg = int((lon % 30) // (30 / division))
    varga_sign = (sign * division + seg) % 12
    varga = (varga_sign * 30) + ((lon % (30 / division)) * division)

    return varga


def calculate_transit_varga(positions, houses, division):
    # calculate planetary positions & houses & ascmc in varga chart
    # jd_ut is not needed if we receive e2 pos division houses from datamanager
    try:
        cusps = houses["cusps"]
        ascmc = houses["ascmc"]
        LOG.debug(
            f"types : pos={type(positions)} | cusps={type(cusps)} | ascmc={type(ascmc)}",
            extra=routing,
        )
        transit_varga = []
        for v in positions.values():
            varga = get_varga_lon(v["lon"], division)
            transit_varga.append({"name": v["name"], "lon": varga})
        for house_num, cusp_lon in enumerate(cusps, start=1):
            varga = get_varga_lon(cusp_lon, division)
            transit_varga.append({"name": f"h {house_num}", "lon": varga})
        if ascmc and len(ascmc) >= 2:
            asc = get_varga_lon(ascmc[0], division)
            mc = get_varga_lon(ascmc[1], division)
            transit_varga.append({"name": "asc", "lon": asc})
            transit_varga.append({"name": "mc", "lon": mc})

        return ok(transit_varga)

    except Exception as e:
        LOG.error(
            f"transit varga calculation error : {e}",
            extra=routing,
        )
        return err(e)
