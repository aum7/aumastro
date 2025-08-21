# sweph/calculations/aspects.py
# ruff: noqa: E402, E701, F821
import swisseph as swe
import pandas as pd
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from ui.helpers import _object_name_to_code as objcode

MEMBERS = [
    "pl",
    "ne",
    "ur",
    "sa",
    "ra",
    "ju",
    "ma",
    "su",
    "ve",
    "me",
    "mo",
]


def total_cycle(ordered, pos_map):
    # sum all pairwise angles for members
    num = len(ordered)
    angles = []
    pairs = []
    for i in range(num):
        for j in range(i + 1, num):
            slow, fast = ordered[i], ordered[j]
            lon_slow = pos_map[slow]["lon"]
            lon_fast = pos_map[fast]["lon"]
            angle = abs((lon_fast - lon_slow) % 360)
            # doolaard implies shortest angle
            shortest = min(angle, 360 - angle)
            angles.append(shortest)
            pairs.append((f"{slow}-{fast}", shortest))
        total_idx = sum(angles)
        total_norm = total_idx % 360
    return {
        "members": ordered,
        "angles": angles,
        "pairs": pairs,
        "pairs num": len(pairs),
        "result": (total_idx, total_norm),  # type: ignore
    }


# def cycle_range(df_dates):
#     cycle_vals = []
#     for dt in df_dates:
#         jd = swe.julday(dt.year, dt.month, dt.day, dt.hour)
#         members_ordered = [n for n in MEMBERS if n in pos_map]


def calculate_cycle(event: str):
    """calculate phases matrix for one event"""
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = "cycle wave :\n"
    app_sett = getattr(app, "chart_settings", None)
    if not app_sett:
        notify.error(
            "missing application settings : exiting ...",
            source="phases",
            route=["terminal"],
        )
        return
    file_name = app.files.get("data")
    members = app.chart_settings.get("cycle members")
    cycle_vals = []
    # get file to be plotted on graph

    price_df = pd.read_csv(file_name)
    msg += f"pricedf : {price_df}\n"
    # if event not in ("e1", "e2"):
    #     return
    # pos = getattr(app, f"{event}_positions", None)
    # if not pos or not isinstance(pos, dict):
    #     notify.error(
    #         f"missing positions for {event} : phases abort",
    #         source="phases",
    #         route=["terminal"],
    #     )
    #     return
    # map by name (only numeric keys)
    # pos_map = {v["name"]: v for k, v in pos.items() if isinstance(k, int)}
    # objs_map = [name for name in DRAW_ORDER if name in pos_map]
    # if not objs_map:
    #     notify.error(
    #         f"no objects available for {event}",
    #         source="phases",
    #         route=["terminal"],
    #     )
    #     return
    # obj_names, matrix, speeds = phases_matrix(objs_map, pos_map, aspect_orb=3.0)
    cycle_data = {
        #     "obj names": obj_names,
        #     "matrix": matrix,
        #     "speeds": speeds,
    }
    app.signal_manager._emit("cycle_changed", event, cycle_data)
    msg += "emitted signal\n"
    notify.debug(
        msg,
        # f"cycle updated for {event}",
        source="cycle",
        route=["terminal"],
    )


def connect_signals_cycle(signal_manager):
    """update cycle when positions change"""
    signal_manager._connect("positions_changed", calculate_cycle)
