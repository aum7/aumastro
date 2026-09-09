# sweph/calculations/lunarreturn.py
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "returnlunar"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import _object_name_to_code as objcode, ok, err


def calculate_lunar_return(
    e2_jd, lat, lon, e1_mo, objs, month_length, hsys, mean_node, flag
):
    # calculate lunar return
    try:
        lr_jd = swe.mooncross_ut(e1_mo, e2_jd - month_length, flag)
        if lr_jd > e2_jd:
            lr_jd = swe.mooncross_ut(e1_mo, e2_jd - month_length - 2.0, flag)
        lun_ret = [{"lr jdut": lr_jd}]
        for obj in objs:
            code, name = objcode(obj, mean_node)
            if code is None:
                return err(f"unknow object name  {obj}")

            res = swe.calc_ut(lr_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            lun_ret.append({
                "name": name,
                "lon": data[0],
            })
        try:
            cusps, ascmc = swe.houses_ex(
                lr_jd,
                lat,
                lon,
                hsys,
                flag,
            )
            lun_ret.append({"cusps": cusps})
            lun_ret.append({"name": "asc", "lon": ascmc[0]})
            lun_ret.append({"name": "mc", "lon": ascmc[1]})
        except swe.Error as e:
            LOG.error(
                f"lunar return houses calculation error : {e}",
                extra=routing,
            )
        return ok(lun_ret)

    except (swe.Error, Exception) as e:
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
