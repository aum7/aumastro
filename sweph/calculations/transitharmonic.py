# sweph/calculations/transitharmonic.py
# simple division by user input
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "transitharmonic"
routing = {"source": source, "route": ["terminal"]}
from helpers import ok, err


def get_harmonic_lon(lon, division):
    # LOG.debug(f"getharmonic : division={division} type={type(division)}")
    if division <= 1:
        return None
    sign = int(lon // 30)
    seg = int((lon % 30) // (30 / division))
    harmonic_sign = (sign * division + seg) % 12
    harmonic = (harmonic_sign * 30) + ((lon % (30 / division)) * division)

    return harmonic


def calculate_transit_harmonic(positions, houses, division):
    # calculate planetary positions & houses & ascmc in harmonic chart
    # jd_ut is not needed if we receive e2 pos division houses from datamanager
    try:
        cusps = houses["cusps"]
        ascmc = houses["ascmc"]
        LOG.debug(
            f"types : pos={type(positions)} | cusps={type(cusps)} | ascmc={type(ascmc)}",
            extra=routing,
        )
        transit_harmonic = []
        for v in positions.values():
            harmonic = get_harmonic_lon(v["lon"], division)
            transit_harmonic.append({"name": v["name"], "lon": harmonic})
        for house_num, cusp_lon in enumerate(cusps, start=1):
            harmonic = get_harmonic_lon(cusp_lon, division)
            transit_harmonic.append({"name": f"h {house_num}", "lon": harmonic})
        if ascmc and len(ascmc) >= 2:
            asc = get_harmonic_lon(ascmc[0], division)
            mc = get_harmonic_lon(ascmc[1], division)
            transit_harmonic.append({"name": "asc", "lon": asc})
            transit_harmonic.append({"name": "mc", "lon": mc})

        return ok(transit_harmonic)

    except Exception as e:
        LOG.error(
            f"transit harmonic calculation error : {e}",
            extra=routing,
        )
        return err(e)
