# sweph/calculations/lots.py
# ruff: noqa: E402, E701
import logging as log
from sweph.helpers import ok, err


source = "lots"
route = ["terminal"]


def calculate_lots(jd_ut, geo=(), objs=(), flag=0, params=None):
    # calculate arabic parts aka hermetic lots for event
    if jd_ut is None:
        return err("invalid jd_ut")
    # grab existing positions with lon
    p = params or {}
    lots_def = p.get("lots_def", p.get("lots", {}))
    if not lots_def:
        return err("missing lots definitions")
    is_day = p.get("is_day", True)
    calc_data = {}
    if "calc_data" in p:
        calc_data = p["calc_data"]
    else:
        ascmc = p.get("ascmc", [])
        if len(ascmc) > 0:
            calc_data["asc"] = ascmc[0]
        if len(ascmc) > 1:
            calc_data["mc"] = ascmc[1]
        positions = p.get("positions", {})
        if isinstance(positions, dict):
            for k, v in positions.items():
                if isinstance(v, dict) and "lon" in v:
                    calc_data[k] = v["lon"]
                elif isinstance(v, (int, float)):
                    calc_data[k] = float(v)
        elif isinstance(positions, list):
            for item in positions:
                if isinstance(item, dict) and "name" in item and "lon" in item:
                    calc_data[item["name"]] = item["lon"]
    if not calc_data:
        return err("missing calculation data for lots")
    lots = []
    for lot, data in lots_def.items():
        if not isinstance(data, dict):
            continue
        # night is not implemented - left to others to play with that
        formula = data.get("day") if is_day else data.get("night", data.get("day"))
        if not formula:
            continue
        try:
            lot_lon = eval(formula, {"__builtins__": None}, data) % 360.0
            lots.append({
                "name": lot,
                "lon": lot_lon,
            })
        except Exception as e:
            log.error(
                f"lot calculation error for {lot} : {e}",
                extra={"source": source, "route": route},
            )
            continue

    return ok(lots)
