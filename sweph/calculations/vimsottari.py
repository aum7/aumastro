# sweph/calculations/vimsottari.py
# output line num : lvl1-18 lvl2-91 lvl3-763 lvl4-6764 lvl5-61198
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "vimsottari"
routing = {"source": source, "route": ["terminal"]}
routingtimeout5 = {"source": source, "route": ["terminal", "user"], "timeout": "5"}
# import swisseph as swe
from helpers import _decimal_to_ymd as decytoymd, ok, err
from sweph.constants import NAKSATRAS27, DASA_YEARS
from sweph.swetime import jd_to_local_time as jdtoloc


PARAMAYUS = 120  # sum of all maha dasa years
# output line prefix per level
INDENT = {1: "", 2: " 2 ", 3: "  3  ", 4: "   4   ", 5: "    5    "}


def find_naksatra(anchor_lon):
    # naksatra index & fraction from anchor longitude
    part = 360 / 27
    idx = int(anchor_lon // part) + 1
    frac = (anchor_lon % part) / part

    return idx, frac


def get_lord_seq(start_lord):
    # 9 dasa lords in vimsottari order starting from start lord
    seq = [NAKSATRAS27[i][0] for i in range(1, 10)]
    idx = seq.index(start_lord)

    return seq[idx:] + seq[:idx]


def tuple_to_iso(jd, tz_name=None):
    # utc julian day to event local year, month, day, hour, minute, second
    # Y, M, D, dec_h = swe.revjul(jd, swe.GREG_CAL)
    # h, m, s = dectohms(dec_h)

    # return f"{Y:04d}-{M:02d}-{D:02d} {h:02d}:{m:02d}:{s:02d}"
    return jdtoloc(jd, tz_name).strftime("%Y-%m-%d %H:%M:%S")


def walk(lord, start, years, level, e1_jd, e2_jd, curr_lvl, year_length):
    # yield level lord startjd years in display order : true (full) periods
    # subperiods are always sized from full parent : proportional to lord years
    end = start + years * year_length
    if end <= e1_jd:
        # ended before birth
        return
    # levels 3-5 : only periods containing e2 datetime
    if curr_lvl >= level + 2 and not start <= e2_jd < end:
        return

    yield level, lord, start, years
    if level == curr_lvl:
        return

    for sub in get_lord_seq(lord):
        sub_years = years * DASA_YEARS[sub] / PARAMAYUS
        yield from walk(
            sub, start, sub_years, level + 1, e1_jd, e2_jd, curr_lvl, year_length
        )
        start += sub_years * year_length


def vimsottari_table(
    e1_jd, anchor_lon, e2_jd, curr_lvl, year_length, tz_name=None, anchor="mo"
):
    # prepare table as plain text
    idx, frac = find_naksatra(anchor_lon)
    nak_lord, nak_name = NAKSATRAS27[idx]
    separ = f"{'-' * 42}\n"
    header = (
        f"\n hk : shift+v : toggle vimso dasas level\n"
        " level 1 & 2 : complete dasas\n"
        " levels 3-5 : >event 2 datetime< maha dasa only\n"
        f" anchor : {anchor}\n"
        f"{separ}"
        f" nak {idx:02} {nak_name} {nak_lord} | traversed "
        f"{frac * 100:.2f} % | lvl {curr_lvl}\n{separ}"
    )
    # true start of birth maha dasa : elapsed part is before birth
    start = e1_jd - frac * DASA_YEARS[nak_lord] * year_length
    out = []
    for lord in get_lord_seq(nak_lord):
        years = DASA_YEARS[lord]
        for lvl, lrd, st, yrs in walk(
            lord, start, years, 1, e1_jd, e2_jd, curr_lvl, year_length
        ):
            dur = decytoymd(yrs, year_length)
            out.append(f"{INDENT[lvl]} {lrd:<2} {tuple_to_iso(st, tz_name)} {dur}")
        start += years * year_length

    return header + "\n".join(out)


def calculate_vimsottari(
    e1_jd, anchor_lon, e2_jd, curr_level, year_length, tz_name=None, anchor="mo"
):
    # event 1 is mandatory and only source
    # on missing event 2 julian day notify user & cap table levels
    if e2_jd is None and curr_level >= 3:
        msg = "event 2 datetime required for levels 3-5 : level > 1"
        LOG.warning(
            msg,
            extra=routingtimeout5,
        )
        return err(msg)

    try:
        return ok(
            vimsottari_table(
                e1_jd, anchor_lon, e2_jd, curr_level, year_length, tz_name, anchor
            )
        )

    except Exception as e:
        LOG.error(f"vimsottari calculation error : {e}")
        return err(e)
    # LOG.debug(
    #     "vimsottari finished",
    #     extra=routing,
    # )
