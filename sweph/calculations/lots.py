# sweph/calculations/lots.py
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "lots"
routing = {"source": source, "route": ["terminal"]}
from helpers import ok, err


def calculate_lots(lots_package):
    # calculate arabic parts aka hermetic lots for event
    ascmc = lots_package["ascmc"]
    positions = lots_package("positions")
    lot_defs = lots_package("lots")
    calc_data = {"asc": ascmc[0], "mc": ascmc[1]}
    for v in positions.values():
        calc_data[v["name"]] = v["lon"]
    lots = []
    for lot, data in lot_defs.items():
        try:
            lot_lon = eval(data["day"], {"__builtins__": None}, calc_data) % 360.0
        except Exception as e:
            LOG.error(
                f"lot calculation error for {lot} : {e}",
                extra=routing,
            )
            return err(e)
        lots.append({"name": lot, "lon": lot_lon})

    return ok(lots)

    # todo figure which one below it is & remove other (terminate elif)
    #     if isinstance(positions, dict):
    #         for k, v in positions.items():
    #             if isinstance(v, dict) and "lon" in v:
    #                 calc_data[k] = v["lon"]
    #             elif isinstance(v, (int, float)):
    #                 calc_data[k] = float(v)
    #     elif isinstance(positions, list):
    #         for item in positions:
    #             if isinstance(item, dict) and "name" in item and "lon" in item:
    #                 calc_data[item["name"]] = item["lon"]
    # if not calc_data:
    #     return err("missing calculation data for lots")
    # lots = []
    # for lot, data in lots_pckg.items():
    #     if not isinstance(data, dict):
    #         msg = "lots package is not dictionary"
    #         LOG.error(
    #             msg,
    #             extra=routing,
    #         )
    #         return err(msg)
    #         # continue
    #     # night is not implemented - left to others to play with that
    #     formula = data.get("day") if is_day else data.get("night")
    #     if not formula:
    #         msg = "lot calculation : missing formula"
    #         LOG.error(
    #             msg,
    #             extra=routing,
    #         )
    #         return err(msg)
    #         # continue
    #     try:
    #         lot_lon = eval(formula, {"__builtins__": None}, data) % 360.0
    #         lots.append({
    #             "name": lot,
    #             "lon": lot_lon,
    #         })
    #     except Exception as e:
    #         LOG.error(
    #             f"lot calculation error for {lot} : {e}",
    #             extra=routing,
    #         )
    #         return err(e)
    #         # continue

    # return ok(lots)
