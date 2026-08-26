# sweph/calculations/p3.py
# ruff: noqa: E402
# tertiary progression (day for a month - earth-moon) (houck)
# 13.369 ratio
import logging as log
from sweph.helpers import ok, err
import swisseph as swe
from ui.helpers import _object_name_to_code as objcode, _decimal_to_hms as dectohms

source = "p3"
route = ["terminal"]


def tuple_to_iso(jd):
    date = swe.revjul(jd, swe.GREG_CAL)
    y, m, d, h = date
    H, M, S = dectohms(h)
    return f"{y}-{m:02}-{d:02} {H:02}:{M:02}:{S:02}"


def calculate_p3(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    # calculate lunar returns before and after e2 (gives exact lunar month)
    if jd_ut is None:
        return err("invalid jd_ut")
    p = params or {}
    e2_jd = p.get("e1_jd")
    if e2_jd is None:
        return err("missing e2_jd")
    e1_jd = jd_ut
    e1_su = p.get("e1_su")
    e2_mo = p.get("e2_mo")
    e1_asc = p.get("e1_asc", 0.0)
    e1_mc = p.get("e1_mc", 0.0)
    exact_lunar_month = p.get("exact_lunar_month", False)
    month_length = p.get("month_length", 27.321661)
    hsys = p.get("hsys", "P")
    use_mean_node = p.get("use_mean_node", False)
    if e1_su is None:
        return err("missing natal sun position")
    try:
        # period elapsed from birth in years : needs event 2 datetime
        period = e2_jd - e1_jd
        if exact_lunar_month and e2_mo is not None:
            # lunar returns : search x days range
            lr_prev_jd = swe.mooncross_ut(e2_mo, e2_jd - 27.5, flag)
            lr_next_jd = swe.mooncross_ut(e2_mo, e2_jd + 0.1, flag)
            # calculate lunar month length
            lr_month = lr_next_jd - lr_prev_jd
            # completed returns for mark pottenger / houck exact calculation
            # last lunar return before e2 - birth jd
            completed_returns = round((lr_prev_jd - e1_jd) / month_length)
            cycle_fraction = (e2_jd - lr_prev_jd) / lr_month
            p3_diff = completed_returns + cycle_fraction
        else:
            # print("p3 : using average lunar month length")
            p3_diff = period / month_length
        # main calculation of progress in days
        p3_jd = e1_jd + p3_diff
        p3_date = tuple_to_iso(p3_jd)
        # msg += p3_date
        p3 = [
            {"p3jdut": p3_jd},
            {"p3date": p3_date},
        ]
        res, e = swe.calc_ut(p3_jd, swe.SUN, flag)  # su lon
        p3_su = res[0]
        if len(geo) >= 2:
            lat, lon = geo[0], geo[1]
            try:
                _, ascmc = swe.houses_ex(
                    p3_jd,
                    lat,
                    lon,
                    hsys.encode("ascii"),
                    flag,
                )
                p3.append({"name": "tas", "lon": ascmc[0]})
                p3.append({"name": "tmc", "lon": ascmc[1]})
            except swe.Error as e:
                log.error(
                    f"p3 sweph houses calculation error : {e}",
                    extra={"source": source, "route": route},
                )
        e1_mc_arc = (e1_mc - e1_su) % 360.0 if e1_mc else 0.0
        e1_asc_arc = (e1_asc - e1_su) % 360.0 if e1_asc else 0.0
        p3_asc = (p3_su + e1_asc_arc) % 360.0
        p3_mc = (p3_su + e1_mc_arc) % 360.0
        p3.append({"name": "asc", "lon": p3_asc})
        p3.append({"name": "mc", "lon": p3_mc})
        for obj in objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            res = swe.calculate(p3_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            p3.append({
                "name": name,
                "lon": data[0],
                "lon speed": data[3],
            })
        return ok(p3)
    except swe.Error as e:
        return err(e)
    except Exception as e:
        return err(e)


# tertiary progression
# as per richard houck (astrology of death)
# divide year by sidereal month & use blocks of 13-14 days as representing
# a year in life
# use tertiary planets & tertiary solar arc'd mc (and derived asc) as they hit
# the natal chart
# a day in life (or ephemeris) is equal to a lunar month in the life
# p3 MC by amount of tertiary solar arc, ie roughly 1 degree per month
# p3 ASC just a slight variation on this : derived normally per Table of Houses
# tertiary angles for rectification : every week of event error (p3 angles) will
# correlate to about 1 minute of birthtime error ; tertiary angles will pass
# about 2 1/2 years in each sign and house : correlates to transiting Saturn
# and the p2 progressed Moon

# Dasa / Bhukti planets with p3 planets, 3 rules that apply (subject of death)
# 1. p3 planetary stations intensify amplitude to symbolic message in the chart
# quality of amplitude related directly to fundamental nature of planet
# 2. an approximate correlation between current Dasa (or Bhukti) planet and a
# p3 planetary station : often signal death if subsidiary factors confirm
# 3. expect apx p3 angle & planet hits in exact 4th harmonic to current maraka
# chart sensible to prenatal and p3 eclipses : any point in a chart (planet or
# angle) becomes extremely sensitized if hit directly by one of these eclipses
# ancient astrologers considered eclipses evil : interrupted luminaries
# 1 degree exact ; jyotisa rules for aspects : ma 4/8 ju 5/9 sa 3/10

# calculate lunar returns before and after e2 (gives exact lunar month)
# mc progressed by solar arc with all other cusps calculated from that
# p3 su & mc move around chart at about 1 ° per month, with p3 asc typically
# at a very slight variation > p3 angles in signs about 2 & ½ years (about as
# long as Tsa spends in a sign, p3 su circles chart same as Tsa. p3 mo moves
# ½ a ° per day > 2 months in sign, 2 years to circle entire chart
