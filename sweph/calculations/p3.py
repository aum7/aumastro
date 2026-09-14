# sweph/calculations/p3.py
# ruff: noqa: E402
# tertiary progression (day for a month - earth-moon) (houck)
# 13.369 ratio
import logging

LOG = logging.getLogger(__name__)
source = "p3"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import (
    _object_name_to_code as objcode,
    _decimal_to_hms as dectohms,
    ok,
    err,
)
from sweph.calculations.stations import get_retro_phases


def tuple_to_iso(jd):
    Y, M, D, dec_h = swe.revjul(jd, swe.GREG_CAL)
    h, m, s = dectohms(dec_h)

    return f"{Y:04d}-{M:02d}-{D:02d} {h:02d}:{m:02d}:{s:02d}"


def calculate_p3(
    e1_jd,
    e2_jd,
    lat,
    lon,
    e1_su,
    e1_asc,
    e1_mc,
    e2_mo,
    objs,
    month_length,
    exact_lunar_month,
    hsys,
    mean_node,
    flag,
):
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
        p3 = [{"p3 jdut": p3_jd}, {"p3 date": p3_date}]
        # todo for error do we need returned swe error ???
        res, _ = swe.calc_ut(p3_jd, swe.SUN, flag)  # su lon
        p3_su = res[0]
        try:
            _, ascmc = swe.houses_ex(
                p3_jd,
                lat,
                lon,
                hsys,
                flag,
            )
            p3.append({"name": "tas", "lon": ascmc[0]})
            p3.append({"name": "tmc", "lon": ascmc[1]})
        except swe.Error as e:
            LOG.error(
                f"p3 sweph houses calculation error : {e}",
                extra=routing,
            )
            return err(e)

        e1_mc_arc = (e1_mc - e1_su) % 360.0 if e1_mc else 0.0
        e1_asc_arc = (e1_asc - e1_su) % 360.0 if e1_asc else 0.0
        p3_asc = (p3_su + e1_asc_arc) % 360.0
        p3_mc = (p3_su + e1_mc_arc) % 360.0
        p3.append({"name": "pas", "lon": p3_asc})
        p3.append({"name": "pmc", "lon": p3_mc})
        for obj in objs:
            code, name = objcode(obj, mean_node)
            if code is None:
                return err(f"unknown object name : {obj}")

            res = swe.calc_ut(p3_jd, code, flag)
            data = res[0]
            p3.append({
                "name": name,
                "lon": data[0],
                "lon speed": data[3],
                "retro": get_retro_phases(
                    code,
                    p3_jd,
                    flag,
                    curr_speed=data[3],
                ),
            })
        return ok(p3)

    except (swe.Error, Exception) as e:
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
