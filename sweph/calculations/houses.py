# sweph/calculations/houses.py
# ruff: noqa: E402, E701
import swisseph as swe  # type:ignore
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from typing import List


# def calculate_houses(event: Optional[str] = None) -> None:
def calculate_houses(event: str):
    """calculate houses & ascendant & midheaven + planet sign"""
    # ascmc : 0 asc 1 mc 2 armc 3 vertex 4 equ. asc
    # 5 co-asc koch 6 co-asc munkasey 7 polar asc munkasey
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"{event}\n"
    # event 1 data is manadatory
    events: List[str] = [event] if event else ["e1", "e2"]
    msg += f"both events [?] : {events}\n"
    if "e2" in events and not app.e2_sweph.get("jd_ut"):
        # skip event two if no datetime / julian day utc set = user not interested
        events.remove("e2")
    for event in events:
        sweph = app.e1_sweph if event == "e1" else app.e2_sweph
        hsys = app.selected_house_sys
        # sweph_flag = app.sweph_flag
        jd_ut = sweph.get("jd_ut")
        msg += (
            f"house system : {hsys}\n\tswephflag : {app.sweph_flag}\n\tjdut : {jd_ut}"
        )
        houses = {}
        try:
            cusps, ascmc = swe.houses_ex(
                jd_ut,
                sweph["lat"],
                sweph["lon"],
                hsys.encode("ascii"),
                app.sweph_flag,
            )
            houses = (cusps, ascmc)
            # emit signals
            if event == "e1":
                app.e1_houses = houses
                # msg += f"houses {event} [e1] :\n\t{app.e1_houses}\n"
                app.signal_manager._emit("houses_changed", event)
            elif event == "e2":
                app.e2_houses = houses
                # msg += f"houses {event} [e2] :\n\t{app.e2_houses}\n"
                app.signal_manager._emit("houses_changed", event)
        except swe.Error as e:
            notify.error(
                f"houses calculation failed for : {event}\n\tdata : {houses}\n\tswe error\n\t{e}",
                source="houses",
                route=["terminal"],
            )
        notify.debug(
            msg,
            source="houses",
            route=[""],
        )
    return


def connect_signals_houses(signal_manager):
    signal_manager._connect("event_changed", calculate_houses)
    signal_manager._connect("settings_changed", calculate_houses)
