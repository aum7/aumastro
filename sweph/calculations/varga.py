# sweph/calculations/varga.py
# simple division by user input
# ruff: noqa: E402, E701
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore


def get_varga_lon(lon: float, division: int = 9):
    if division == "" or division == 1:
        return lon
    sign = int(lon // 30)
    seg = int((lon % 30) // (30 / division))
    varga_sign = (sign * division + seg) % 12
    varga = (varga_sign * 30) + ((lon % (30 / division)) * division)
    return varga


def calculate_varga(event: str, division: int = 9):
    # calculate planetary positions in varga chart
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"event {event}\n"
    varga_data = []
    varga_data.append({"event": event})
    # event 1 is mandatory
    if event == "e1":
        # check by event 1 sweph attribute
        if not app.e1_sweph.get("jd_ut"):
            notify.error(
                "missing event 1 data : exiting ...",
                source="varga",
                route=[""],
            )
            return
        # e1 positions
        e1_pos = getattr(app, "e1_positions", None)
        e1_houses = getattr(app, "e1_houses", None)
        if e1_pos and e1_houses:
            for _, data in e1_pos.items():
                if isinstance(data, dict) and "lon" in data:
                    name = data.get("name", "")
                    lon = data.get("lon", 0.0)
                    varga = get_varga_lon(lon, division)
                    varga_data.append({"name": name, "lon": varga})
            # add asc & mc from houses / ascmc
            ascmc = e1_houses[1]
            if ascmc:
                asc = ascmc[0]
                mc = ascmc[1]
                for obj, name in zip((asc, mc), ("asc", "mc")):
                    varga = get_varga_lon(obj, division)
                    varga_data.append({"name": name, "lon": varga})

    if event == "e2":
        # check by event 2 sweph attribute
        if not app.e2_sweph.get("jd_ut"):
            notify.error(
                "missing event 2 data : exiting ...",
                source="varga",
                route=[""],
            )
            return
        # e2 positions
        e2_pos = getattr(app, "e2_positions", None)
        e2_houses = getattr(app, "e2_houses", None)
        msg += f"e2houses : {e2_houses}\n"
        if e2_pos and e2_houses:
            for _, data in e2_pos.items():
                if isinstance(data, dict) and "lon" in data:
                    name = data.get("name", "")
                    lon = data.get("lon", 0.0)
                    varga = get_varga_lon(lon, division)
                    varga_data.append({"name": name, "lon": varga})
            # add asc & mc from houses / ascmc
            ascmc = e2_houses[1]
            msg += f"ascmc : {ascmc}\n"
            if ascmc:
                asc = ascmc[0]
                mc = ascmc[1]
                for obj, name in zip((asc, mc), ("asc", "mc")):
                    varga = get_varga_lon(obj, division)
                    varga_data.append({"name": name, "lon": varga})
    msg += f"vargadata : {varga_data}"
    # emit signal
    app.signal_manager._emit("varga_changed", event)
    notify.debug(
        msg,
        source="varga",
        route=[""],
    )
    return varga_data


def connect_signals_varga(signal_manager):
    # update varga chart
    signal_manager._connect("event_changed", calculate_varga)
    signal_manager._connect("settings_changed", calculate_varga)
