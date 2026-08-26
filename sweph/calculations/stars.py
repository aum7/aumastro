# sweph/calculations/start.py
# ruff: noqa: E402
# swe.fixstar2_ut : star name (catalog or nomenclature), tjd_ut, flags
# returns : (lon, lat, dist, speeds : lon, lat, dist), star name, flags used
# eta tauri : ("Alcyone", "Alcyone, Krttika", "etTau"),
import logging as log
from sweph.helpers import ok, err
import swisseph as swe

source = "stars"
route = ["terminal"]


def calculate_stars(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    # calculate positions of stars, listed in user/fixedstars.py
    if jd_ut is None:
        return err("invalid jd_ut")

    p = params or {}
    stars_list = p.get("stars_list")
    if not stars_list:
        return err("missing stars list")

    stars = []
    name, nomencl = None, None
    for star in stars_list:
        if isinstance(star, (tuple, list)):
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
        except swe.Error as e:
            log.error(
                f"stars calculation error : {e}",
                extra={"source": source, "route": route},
            )
        except Exception as e:
            log.error(
                f"stars calculation exception : {e}",
                extra={"source": source, "route": route},
            )
    return ok(stars)
