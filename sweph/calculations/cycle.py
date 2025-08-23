# sweph/calculations/aspects.py
# ruff: noqa: E402, E701, F821
import swisseph as swe
import pandas as pd
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from pathlib import Path
from ui.helpers import _object_name_to_code as objcode
from sweph.calculations.varga import get_varga_lon

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
    return total_idx


def store_cycle(data):
    # save cycle data for jforex plot
    members = data["members"]
    division = data["division"]
    use_varga = data["use varga"]
    dataframe = data["dataframe"]
    df = dataframe.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    # filename from members
    members_str = "_".join(members)
    if use_varga:
        filename = f"wave_{members_str}_v{division}.csv"
    else:
        filename = f"wave_{members_str}_v1.csv"
    out_path = Path("user/data/wave") / filename
    df.to_csv(out_path, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return out_path


def future_cycle(price_df, days=30, freq="D"):
    # extend cycle wave into the future
    last_dt = price_df.index[-1]
    future_idx = pd.date_range(
        start=last_dt + pd.DateOffset(days=1),
        end=last_dt + pd.DateOffset(days=days),
        freq=freq,
    )
    return price_df.reindex(price_df.index.union(future_idx))


def calculate_cycle(event: str):
    """calculate cycle wave for plot"""
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
    division = int(app.chart_settings.get("harmonic ring", "1").strip())
    use_varga = app.chart_settings.get("use varga", False)
    file_name = app.files.get("data")
    cycle_members = app.chart_settings.get("cycle members")
    if isinstance(cycle_members, list):
        members_str = " ".join(cycle_members)
    elif isinstance(cycle_members, str):
        members_str = cycle_members
    else:
        members_str = "sa ju"  # fallback
    members_list = members_str.replace(",", " ").split()  # type:ignore
    members = [m.strip() for m in members_list if m.strip()]
    # print(f"members : {members}")
    # get file to be plotted on graph
    price_df = pd.read_csv(file_name)
    price_df["datetime"] = pd.to_datetime(price_df["datetime"])
    price_df = price_df.set_index("datetime")
    # extend datetime range into the future
    price_df = future_cycle(price_df)
    cycle_vals = []
    pos_map = {}
    for dt in price_df.index:
        jd = swe.julday(dt.year, dt.month, dt.day, dt.hour)
        for name in members:
            code, name = objcode(name, app.chart_settings.get("mean node"))
            result = swe.calc_ut(jd, code, app.sweph_flag)
            # allow for varga positions
            lon = result[0][0]
            if lon and use_varga:
                lon = get_varga_lon(lon, division)
            pos_map[name] = {"lon": lon}
        members_ordered = [n for n in MEMBERS if n in pos_map]
        # if set(members).issubset(pos_map):
        cycle = total_cycle(members_ordered, pos_map)
        cycle_vals.append(cycle)
    cycle_df = pd.DataFrame({"datetime": price_df.index, "cycle": cycle_vals})
    # print(f"cycledf : {cycle_df}")
    cycle_data = {
        "members": members,
        "division": division,
        "use varga": use_varga,
        "dataframe": cycle_df,
    }
    store_cycle(cycle_data)
    msg += f"cycledata :\n{cycle_data}\n"
    app.signal_manager._emit("cycle_changed", event, cycle_data)
    notify.debug(
        msg,
        source="cycle",
        route=[""],
    )
    return cycle_data


def connect_signals_cycle(signal_manager):
    """update cycle wave when positions change"""
    signal_manager._connect("cycle_settings_changed", calculate_cycle)
