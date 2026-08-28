# sweph/calculations/lunarreturn.py
# ruff: noqa: E402, E701
import logging as log
import swisseph as swe
from helpers import _object_name_to_code as objcode, ok, err
# from sweph.swetime import jd_to_custom_iso as jdtoiso

source = "returnlunar"
route = ["terminal"]
routing = {"source": source, "route": route}


def calculate_lr(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    # calculate lunar return
    # check against lumies since e1_sweph can have 0 objects (user-selectable)
    # e1 positions for su / mo longitude crosscheck only
    if jd_ut is None:
        return err("invalid jd_ut")
    p = params or {}
    e2_jd = p.get("e2_jd")
    if e2_jd is None:
        return err("missing e2_jd")
    e1_mo = p.get("e1_mo")
    if e1_mo is None:
        return err("missing natal moon position")
    month_length = p.get("month_length", 27.321661)
    hsys = p.get("hsys", "P")
    use_mean_node = p.get("use_mean_node", False)
    try:
        lr_jd = swe.mooncross_ut(e1_mo, e2_jd - month_length, flag)
        if lr_jd > e2_jd:
            lr_jd = swe.mooncross_ut(e1_mo, e2_jd - month_length - 2.0, flag)
        lun_ret = [{"lrjdut": lr_jd}]
        for obj in objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            res = swe.calc_ut(lr_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            lun_ret.append({
                "name": name,
                "lon": data[0],
            })
        if len(geo) >= 2:
            lat, lon = geo[0], geo[1]
            try:
                cusps, ascmc = swe.houses_ex(
                    lr_jd,
                    lat,
                    lon,
                    hsys.encode("ascii"),
                    flag,
                )
                lun_ret.append({"cusps": cusps})
                lun_ret.append({"name": "asc", "lon": ascmc[0]})
                lun_ret.append({"name": "mc", "lon": ascmc[1]})
            except swe.Error as e:
                log.error(
                    f"lunar return houses calculation error : {e}",
                    extra=routing,
                )
        return ok(lun_ret)
    except swe.Error as e:
        return err(e)
    except Exception as e:
        return err(e)

    # DONT DELETE logic might be needed
    # # previous lunar return : search x days back range
    # prev_jd = e2_jd - MONTHLENGTH
    # lr_prev_jd = swe.mooncross_ut(e1_mo, prev_jd, app.sweph_flag)
    # # next lunar return
    # next_jd = e2_jd
    # lr_next_jd = swe.mooncross_ut(e1_mo, next_jd, app.sweph_flag)
    # lr_month = lr_next_jd - lr_prev_jd
    # # store values for checking while lr month is proper
    # if (MONTHLENGTH - 1) < lr_month < (MONTHLENGTH + 1):
    #     app.lr_prev_jd = lr_prev_jd
    #     app.lr_next_jd = lr_next_jd
    # else:
    #     # recalculate values only inside problematic time window
    #     if e1_mo and e2_mo and app.lr_prev_jd and app.lr_next_jd:
    #         # we are in smaller lr cycle
    #         if lr_month == 0.0:
    #             # transit time is before next lr jd > keep old values
    #             if e2_jd <= app.lr_next_jd:
    #                 lr_prev_jd = app.lr_prev_jd
    #                 lr_next_jd = app.lr_next_jd
    #             # transit time is before prev lr jd > should be in prev lr cycle
    #             # which could be bigger lr cycle > extend range by 1 day back
    #             if e2_jd <= app.lr_prev_jd:
    #                 new_prev_jd = e2_jd - MONTHLENGTH - 1
    #                 lr_prev_jd = swe.mooncross_ut(e1_mo, new_prev_jd, app.sweph_flag)
    #                 # new_next_jd = e2_jd - 1
    #                 lr_next_jd = swe.mooncross_ut(e1_mo, e2_jd, app.sweph_flag)
    #                 # lr_next_jd = swe.mooncross_ut(e1_mo, new_next_jd, app.sweph_flag)
    #         # we are in bigger lr cycle
    #         if lr_month > 53.0:
    #             if e2_jd < app.lr_next_jd:
    #                 new_prev_jd = e2_jd - 1
    #                 lr_prev_jd = swe.mooncross_ut(e1_mo, new_prev_jd, app.sweph_flag)
    #     # update stored values
    #     app.lr_prev_jd = lr_prev_jd
    #     app.lr_next_jd = lr_next_jd
    # # current lunar return on chart
    # lr_curr_jd = lr_prev_jd
    # # debug data
    # if lr_month < MONTHLENGTH:
    #     this = "smaller"
    #     diff = round(MONTHLENGTH - lr_month, 5)
    # elif lr_month > MONTHLENGTH:
    #     this = "bigger"
    #     diff = round(lr_month - MONTHLENGTH, 5)
    # msg += (
    #     f"lrmonth : {lr_month} |-| {this} by {diff}\n"
    #     f"e2jd :     {jdtoiso(e2_jd)} < current datetime\n"
    #     f"lrprevjd : {jdtoiso(lr_prev_jd)} < current lr cycle\n"
    #     # f"appprev :  {jdtoiso(app.lr_prev_jd)}\n"
    #     f"lrnextjd : {jdtoiso(lr_next_jd)}\n"
    #     # f"appnext :  {jdtoiso(app.lr_next_jd)}"
    #     # f"lrcurrjd : {jdtoiso(lr_curr_jd)}\n"
    # )
