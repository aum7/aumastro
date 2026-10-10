# sweph/calculations/lots.py
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "lots"
routeuser = {"source": source, "route": ["terminal", "user"]}
from helpers import ok, err


def calculate_lots(lots_package):
    # calculate arabic parts aka hermetic lots for event
    ascmc = lots_package["ascmc"]
    positions = lots_package["positions"]
    lot_defs = lots_package["lots"]
    calc_data = {"asc": ascmc[0], "mc": ascmc[1]}
    for v in positions.values():
        calc_data[v["name"]] = v["lon"]
    lots = []
    for lot, data in lot_defs.items():
        try:
            lot_lon = eval(data["day"], {"__builtins__": None}, calc_data) % 360.0
        except Exception as e:
            LOG.error(f"lot calculation error for {lot} : {e}")
            return err(e)
        lots.append({"name": lot, "lon": lot_lon})

    return ok(lots)
