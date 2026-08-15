# sweph/calculations/lunation.py
# ruff: noqa: E402
import swisseph as swe  # type:ignore
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from typing import List
from sweph.swetime import jd_to_custom_iso as jdtoiso


def calculate_lunation(event: str):
    """calculate prenatal (last) full or new moon - syzygy"""
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"event {event}\n"
    events: List[str] = [event] if event else ["e1", "e2"]
    if "e2" in events and not app.e2_sweph.get("jd_ut"):
        # skip e2 if no datetime / julian day utc set = user not interested in e2
        events.remove("e2")
        msg += "e2 removed\n"
    lunation_data = []
    for event_name in events:
        event_data, jd_ut = None, None
        swe_flag = getattr(app, "sweph_flag", None)
        # get existing data needed
        if event_name == "e1":
            event_data = getattr(app, "e1_sweph", None)
            prenatal = getattr(app, "selected_prenatal_e1")
        elif event_name in ("e2", "p3"):
            # progression is linked to event 2
            event_data = getattr(app, "e2_sweph", None)
            prenatal = getattr(app, "selected_prenatal_e2", None)
        if event_data:
            jd_ut = event_data.get("jd_ut")
        # msg += f"eventdata : {event_data}\n"
        if jd_ut is None:
            notify.warning(
                f"data for {event_name} missing : exiting ...",
                source="lunation",
                route=[""],
            )
            return
        if prenatal and "lunation" in prenatal:  # type:ignore
            flag = swe_flag
            # find closest lunation
            flag |= swe.ECL_ONE_TRY
            # get lunar occultation of sun 0 & 180 degrees
            find_type = 0  # any eclipse type
            # find occultation of sun
            _, tret = swe.lun_occult_when_glob(
                jd_ut, 0, swe_flag, find_type, backwards=True
            )
            # maximum occultation
            jd_max_occ = tret[0]
            msg += f"occultation datetime : {jdtoiso(jd_max_occ)}\n"
            try:
                data, e = swe.calc_ut(jd_max_occ, 1, swe_flag)
                mo_lon = data[0]
                lunation_data.append({
                    "event": event,
                    "datetime": jdtoiso(jd_max_occ),
                })
                lunation_data.append({"name": "conj", "lon": mo_lon})
                return lunation_data
            except Exception as e:
                notify.error(
                    f"lunation error : exiting ...\n\t{e}",
                    source="lunation",
                    route=["terminal"],
                )
                return
        msg += f"lunationdata : {lunation_data}\n"
    notify.debug(
        msg,
        source="lunation",
        route=[""],
    )
    return None
