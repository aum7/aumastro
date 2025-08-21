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
    return total_norm  # type:ignore
    # return {
    #     "members": ordered,
    #     "angles": angles,
    #     "pairs": pairs,
    #     "pairs num": len(pairs),
    #     "result": (total_idx, total_norm),  # type: ignore
    # }


def calculate_cycle(event: str):
    """calculate phases matrix for one event"""
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = "cycle wave :\n"
    app_sett = getattr(app, "chart_settings", None)
    if not app_sett:
        notify.error(
            "missing application settings : exiting ...",
            source="cycle",
            route=["terminal"],
        )
        return
    file_name = app.files.get("data")
    cycle_members = app.chart_settings.get("cycle members")
    if isinstance(cycle_members, list):
        members_str = " ".join(cycle_members)
    members_list = members_str.replace(",", " ").split()  # type:ignore
    members = [m.strip() for m in members_list if m.strip()]
    # print(f"members : {members}")
    # get file to be plotted on graph
    price_df = pd.read_csv(file_name)
    price_df["datetime"] = pd.to_datetime(price_df["datetime"])
    price_df = price_df.set_index("datetime")
    cycle_vals = []
    pos_map = {}
    for dt in price_df.index:
        jd = swe.julday(dt.year, dt.month, dt.day, dt.hour)
        for name in members:
            code, name = objcode(name, app.chart_settings.get("mean node"))
            result = swe.calc_ut(jd, code, app.sweph_flag)
            lon = result[0][0]
            pos_map[name] = {"lon": lon}
        members_ordered = [n for n in MEMBERS if n in pos_map]
        cycle = total_cycle(members_ordered, pos_map)
        cycle_vals.append(cycle)
    cycle_df = pd.DataFrame({"datetime": price_df.index, "cycle": cycle_vals})
    # print(f"cycledf : {cycle_df}")
    cycle_data = {
        "dataframe": cycle_df,
    }
    msg += f"cycledata :\nmembers :{members}\ndataframe :\n{cycle_df}\n"
    # app.signal_manager._emit("cycle_changed", event, cycle_data)
    # msg += "emitted signal\n"
    notify.debug(
        msg,
        source="cycle",
        route=[""],
    )
    return cycle_data


def connect_signals_cycle(signal_manager):
    """update cycle wave when positions change"""
    # signal_manager._connect("positions_changed", calculate_cycle)
    signal_manager._connect("settings_changed", calculate_cycle)
