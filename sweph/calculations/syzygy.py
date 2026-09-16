# sweph/calculations/syzygy.py
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "syzygy"
routing = {"source": source, "route": ["terminal"]}
from helpers import ok, err
import swisseph as swe
from sweph.swetime import jd_to_custom_iso as jdtoiso


def calculate_syzygy(jd_ut, su_lon, mo_lon, flag):
    # calculate last prenatal full or new moon - syzygy
    try:
        # determine if syzygy was new or full moon
        if su_lon is not None and mo_lon is not None:
            diff = (mo_lon - su_lon) % 360.0
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
                sun_data, _ = swe.calc_ut(syzygy_jd, 0, flag)
                moon_data, _ = swe.calc_ut(syzygy_jd, 1, flag)
                current_separation = moon_data[0] - sun_data[0]
                angular_error = (current_separation - target_angle) % 360.0
                if angular_error > 180.0:
                    angular_error -= 360.0
                relative_speed = moon_data[3] - sun_data[3]
                if relative_speed != 0:
                    syzygy_jd -= angular_error / relative_speed
            # moon longitude at exact syzygy day
            final_moon_data, _ = swe.calc_ut(syzygy_jd, 1, flag)
            syzygy_lon = final_moon_data[0]

            return ok([
                {
                    "name": "syzygy",
                    "lun_type": lun_type,
                    "lon": syzygy_lon,
                    "datetime": jdtoiso(syzygy_jd),  # todo to event local time
                }
            ])
    except Exception as e:
        LOG.error(
            f"syzygy calculation error : {e}",
            extra=routing,
        )
        return err(e)
