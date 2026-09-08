# sweph/calculations/houses.py
# ruff: noqa: E402, E701
import logging as log

source = "houses"
route = ["terminal"]
routing = {"source": source, "route": route}
import swisseph as swe  # type:ignore
from helpers import ok, err


def calculate_houses(jd_ut, lat, lon, hsys=b"P", flag=0):
    # calculate houses & ascendant & midheaven + planet sign
    # ascmc : 0 asc 1 mc 2 armc 3 vertex 4 equ. asc
    # 5 co-asc koch 6 co-asc munkasey 7 polar asc munkasey
    # event 1 data is manadatory
    if isinstance(hsys, str):
        hsys = hsys.encode("ascii")
    try:
        # proper syntax : swisseph mess
        cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, hsys, flag)
        return ok({
            "cusps": list(cusps),
            "ascmc": list(ascmc),
        })
    except swe.Error as e:
        log.error(
            f"houses calculations failed : {e}",
            extra=routing,
        )
        return err(e)
