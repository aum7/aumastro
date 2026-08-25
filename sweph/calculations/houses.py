# sweph/calculations/houses.py
# ruff: noqa: E402, E701
import logging as log
import swisseph as swe  # type:ignore
from sweph.helpers import ok, err


def calculate_houses(jd_ut, geo=(), objs=(), flags=0, params=None):
    """calculate houses & ascendant & midheaven + planet sign"""
    # ascmc : 0 asc 1 mc 2 armc 3 vertex 4 equ. asc
    # 5 co-asc koch 6 co-asc munkasey 7 polar asc munkasey
    # event 1 data is manadatory
    if jd_ut is None or len(geo) < 2:
        return err("invalid jd_ut or geo coordinates")
    lat, lon = geo[0], geo[1]
    p = params or {}
    hsys = p.get("house_sys", "P")
    if isinstance(hsys, str):
        hsys = hsys.encode("ascii")
    try:
        cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, hsys, flags)
        return ok({
            "cusps": list(cusps),
            "ascmc": list(ascmc),
        })
    except swe.Error as e:
        log.error(f"houses calculations failed : {e}")
        return err(str(e))
