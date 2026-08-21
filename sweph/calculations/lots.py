# sweph/calculations/lots.py
# ruff: noqa: E402, E701
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from user.settings import LOTS


def calculate_lots():
    """calculate arabic parts aka hermetic lots for event"""
    # grab existing positions with lon & calculate positions of lots
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    # msg = f"event {event}\n"
    positions = getattr(app, "e1_positions", None)
    houses = getattr(app, "e1_houses", None)
    # print(f"lots : houses={houses}")
    selected_lots = getattr(app, "selected_lots_e1", None)
    calc_data = None
    if not positions or not selected_lots:
        return None
    # get ascendant longitude
    if houses:
        calc_data = {"asc": houses[1][0]}
        # example if house cusps are needed
        # calc_data["3rd"] = houses[0][2]  # 3rd house cusp
        # calc_data["10th"] = houses[0][9]  # 10th cusp (equal & whole-sign houses)
        # calc_data["mc"] = houses[1][1]  # true midheaven (quadrant houses)
    # get planets longitude
    for planet in positions.values():
        if isinstance(planet, dict) and "name" in planet and "lon" in planet:
            calc_data[planet["name"]] = planet["lon"]  # type:ignore
    lots = [{"event": "e1"}]
    for lot_key in selected_lots:
        lot_data = LOTS.get(lot_key, {})
        formula = lot_data.get("day")
        if not formula:
            continue
        try:
            lot_lon = eval(formula, {}, calc_data) % 360.0
            lots.append({
                "name": lot_key,
                "lon": lot_lon,
            })
        except Exception as e:
            notify.error(
                f"lot calculation error :\n\t{e}\nkey : {lot_key}",
                source="lots",
                route=["user", "terminal"],
            )
    return lots
