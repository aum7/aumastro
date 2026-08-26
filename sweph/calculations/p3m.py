# sweph/calculations/p3m.py
# ruff: noqa: E402
# minor progression (month for a year - sun-moon) (blaschke)
# 13.369 ratio
import logging as log
from sweph.helpers import ok, err
import swisseph as swe
from ui.helpers import _object_name_to_code as objcode, _decimal_to_hms as dectohms


source = "p3m"
route = ["terminal"]


def tuple_to_iso(jd):
    date = swe.revjul(jd, swe.GREG_CAL)
    y, m, d, h = date
    H, M, S = dectohms(h)
    return f"{y}-{m:02}-{d:02} {H:02}:{M:02}:{S:02}"


def calculate_p3m(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    # calculate lunar returns before and after e2 (gives exact lunar month)
    # check against lumies since e1_sweph can have 0 objects (user-selectable)
    if jd_ut is None:
        return err("invalid jd_ut")

    p = params or {}
    e2_jd = p.get("e2_jd")
    if e2_jd is None:
        return err("missing e2_jd")
    e1_jd = jd_ut
    e1_su = p.get("e1_su")
    e1_mo = p.get("e1_mo")
    e1_asc = p.get("e1_asc", 0.0)
    e1_mc = p.get("e1_mc", 0.0)
    exact_lunar_month = p.get("exact_lunar_month", False)
    year_length = p.get("year_length", 365.2425)
    month_length = p.get("month_length", 27.321661)
    hsys = p.get("hsys", "P")
    use_mean_node = p.get("use_mean_node", False)
    if e1_su is None:
        return err("missing natal sun position")

    try:
        period = e2_jd - e1_jd
        age_years = period(year_length)
        if exact_lunar_month and e1_mo is not None:
            # weird calculation logic - why e1_mo - why mo at all
            full_years = int(age_years)
            fract_year = age_years - full_years
            search_jd = e1_jd + (full_years * month_length) - 15
            # find prev lunar return after birth
            lr_prev_jd = swe.mooncross_ut(e1_mo, search_jd, flag)
            # find next lunar return
            lr_next_jd = swe.mooncross_ut(e1_mo, lr_prev_jd + 0.1, flag)
            cycle_length = lr_next_jd - lr_prev_jd
            p3m_jd = lr_prev_jd + (fract_year * cycle_length)
            p3m_diff = p3m_jd - e1_jd
        else:
            # print("p3m : using average lunar month length")
            p3m_diff = age_years * month_length
        p3m_jd = e1_jd + p3m_diff
        p3m_date = tuple_to_iso(p3m_jd)
        p3m = [{"p3mjdut": p3m_jd}, {"p3mdate": p3m_date}]
        res, _ = swe.calc_ut(p3m_jd, swe.SUN, flag)  # su lon
        # true asc mc positions on progressed day
        p3m_su = res[0]
        if len(geo) >= 2:
            lat, lon = geo[0], geo[1]
            try:
                _, ascmc = swe.houses_ex(
                    p3m_jd,
                    lat,
                    lon,
                    hsys.encode("ascii"),
                    flag,
                )
                p3m.append({"name": "tas", "lon": ascmc[0]})
                p3m.append({"name": "tmc", "lon": ascmc[1]})
            except swe.Error as e:
                log.error(
                    f"p3m true asc mc calculation error : {e}",
                    extra={"source": source, "route": route},
                )
        e1_mc_arc = (e1_mc - e1_su) % 360.0 if e1_mc else 0.0
        e1_asc_arc = (e1_asc - e1_su) % 360.0 if e1_asc else 0.0
        p3m_asc = (p3m_su + e1_asc_arc) % 360.0
        p3m_mc = (p3m_su + e1_mc_arc) % 360.0
        p3m.append({"name": "asc", "lon": p3m_asc})
        p3m.append({"name": "mc", "lon": p3m_mc})
        for obj in objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            res = swe.calc_ut(p3m_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            p3m.append({
                "name": name,
                "lon": data[0],
                "lon speed": data[3],
            })
        return ok(p3m)
    except swe.Error as e:
        return err(e)
    except Exception as e:
        return err(e)
