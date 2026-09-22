# sweph/calculations/positions.py
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "positions"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import (
    _object_name_to_code as objcode,
    get_harmonic_lon as harmlon,
    _relative_speed,
    ok,
    err,
)
from sweph.calculations.naksatras import get_naksatra
from sweph.calculations.stations import get_retro_phases as retrphas


def calculate_positions(
    jd_ut,
    objs,
    division,
    mans_28,
    first_nak,
    mean_node,
    flag,
):
    # let dispatcher worry about delivering proper data
    # LOG.debug(f"calculatepositions : division={division} type={type(division)}")
    positions = {}
    for obj in objs:
        code, name = objcode(obj, mean_node)
        if code is None:
            msg = f"unknown object name : {obj}"
            LOG.debug(
                msg,
                extra=routing,
            )
            return err(msg)
        try:
            result = swe.calc_ut(jd_ut, code, flag)
            pos = result[0]  # pos[0] = lon
            naksatra = get_naksatra(pos[0], mans_28, first_nak)
            harmonic = harmlon(pos[0], division) if division else None
            harmonic_nak = (
                get_naksatra(harmonic, mans_28, first_nak)
                if harmonic is not None
                else None
            )
            result_equat = swe.calc_ut(jd_ut, code, flag | swe.FLG_EQUATORIAL)
            ra, decl = result_equat[0], result_equat[1]
            jd_et = jd_ut + swe.deltat(jd_ut)
            mean_lon = swe.get_orbital_elements(jd_et, code, flag)[0][9]
            # LOG.debug(f"equatorial : {result_equat}")
            positions[code] = {
                "name": name,
                "lon": pos[0],
                "lat": pos[1],
                "lon speed": pos[3],
                "ra": ra,
                "declination": decl,
                "mean lon": mean_lon,
                "retro": retrphas(code, jd_ut, flag, curr_speed=pos[3]),
                "naksatra": naksatra,
                "harmonic": harmonic,
                "harmonic naksatra": harmonic_nak,
                "speed relative": _relative_speed(code, pos[3]),
            }
        except swe.Error as e:
            LOG.error(
                f"positions calculations error : {e}",
                extra=routing,
            )
            return err(e)

    return ok(positions)
