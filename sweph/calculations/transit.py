# sweph/calculations/transit.py
# ruff: noqa: E402, E701
# import swisseph as swe
import logging as log
from sweph.helpers import ok, err
from ui.helpers import _object_name_to_code as objcode

source = "transit"
route = ["terminal"]


# do we need transit as e2 already is calculated
def calculate_transit(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    # gather transit data
    # check against lumies since e1_sweph can have 0 objects (user-selectable)
    # jd_ut not needed as we already have e2 calculations
    # if jd_ut is None:
    #     return err("invalid jd_ut")
    # p = params or {}
    # use_mean_node = p.get("use_mean_node", False)
    # pos = p.get("positions")
    # houses = p.get("houses")
    # if isinstance(pos, dict):
    return err("transit = e2 : already exists")
