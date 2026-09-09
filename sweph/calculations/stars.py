# sweph/calculations/stars.py
# ruff: noqa: E402
# swe.fixstar2_ut : star name (catalog or nomenclature), tjd_ut, flags
# returns : (lon, lat, dist, speeds : lon, lat, dist), star name, flags used
# eta tauri : ("Alcyone", "Alcyone, Krttika", "etTau"),
import logging

LOG = logging.getLogger(__name__)
source = "stars"
routing = {"source": source, "route": ["terminal"]}
from helpers import ok, err
import swisseph as swe


def calculate_stars(jd_ut, stars_list, flag):
    # calculate positions of stars, listed in dispatcher.
    stars = []
    name, nomencl = None, None
    for star in stars_list:
        # todo we know our data : should be list
        # if isinstance(star, (tuple, list)):
        nomencl = star[0]
        name = star[1]
        try:
            # search using name
            pos, _, _ = swe.fixstar2_ut(name, jd_ut, flag)
            lon = pos[0]
            stars.append({
                "name": name,
                "lon": lon,
                "nomencl": nomencl,
            })
        except Exception as e:
            LOG.error(
                f"stars calculation error : {e}",
                extra=routing,
            )
            return err(e)

    return ok(stars)
