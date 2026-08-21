# sweph/calculations/syzygy.py
# ruff: noqa: E402
import swisseph as swe  # type:ignore
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from sweph.swetime import jd_to_custom_iso as jdtoiso


def calculate_syzygy():
    # def calculate_syzygy(event: str = "e1"):
    """calculate last prenatal full or new moon - syzygy"""
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    # get event 1 luminaries : they be calculated separately
    e1_lumies = getattr(app, "e1_lumies", None)
    # print(f"syzygy : lumies={e1_lumies}")
    prenatal = getattr(app, "selected_prenatal_e1", None)
    swe_flag = getattr(app, "sweph_flag", 0)
    if not e1_lumies or "jd_ut" not in e1_lumies:
        notify.error(
            "data for event 1 missing : exiting ...",
            source="syzygy",
            route=[""],  # "user",terminal
        )
        return None
    if not (prenatal and "syzygy" in prenatal):
        return None
    jd_ut = e1_lumies["jd_ut"]
    # get sun & moon longitudes
    sun_lon, moon_lon = None, None
    syzygy_jd, lun_type, syzygy_lon = None, None, None
    if isinstance(e1_lumies, dict):
        for item in e1_lumies.values():
            if isinstance(item, dict):
                if item.get("name") == "su":
                    sun_lon = item.get("lon")
                elif item.get("name") == "mo":
                    moon_lon = item.get("lon")
    try:
        # determine if syzygy was new or full moon
        if sun_lon is not None and moon_lon is not None:
            diff = (moon_lon - sun_lon) % 360.0
            if diff < 180.0:
                target_angle = 0.0
                lun_type = "syznew"  # new moon
                angle_since = diff
            else:
                target_angle = 180.0
                lun_type = "syzful"  # full moon
                angle_since = diff - 180.0
            # initial estimate using average sun & moon daily speed
            average_elongation_speed = 12.19075
            days_since_syzygy = angle_since / average_elongation_speed
            syzygy_jd = jd_ut - days_since_syzygy
            # refine time with newton-raphson iteration
            for _ in range(4):
                sun_data, _ = swe.calc_ut(syzygy_jd, 0, swe_flag)
                moon_data, _ = swe.calc_ut(syzygy_jd, 1, swe_flag)
                current_separation = moon_data[0] - sun_data[0]
                angular_error = (current_separation - target_angle) % 360.0
                if angular_error > 180.0:
                    angular_error -= 360.0
                relative_speed = moon_data[3] - sun_data[3]
                if relative_speed != 0:
                    syzygy_jd -= angular_error / relative_speed
            # moon longitude at exact syzygy day
            final_moon_data, _ = swe.calc_ut(syzygy_jd, 1, swe_flag)
            syzygy_lon = final_moon_data[0]
        if syzygy_jd is not None and lun_type is not None and syzygy_lon is not None:
            return [
                {"event": "e1", "datetime": jdtoiso(syzygy_jd)},
                {"name": lun_type, "lon": syzygy_lon},
            ]
    except Exception as e:
        notify.error(
            f"syzygy calculation error :\n{e}\nexiting ...",
            source="syzygy",
            route=["user", "terminal"],
        )
        return None
