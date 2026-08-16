# sweph/calculations/d1.py
# gansten calculations
# ruff: noqa: E402, E701
import math
import swisseph as swe  # type:ignore
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from ui.helpers import _object_name_to_code as objcode


def calculate_d1(event: str):
    # grab application data & calculate vimsottari for event 1
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"event {event}\n"
    # event 1 & 2 data is mandatory : natal / event & progression chart
    # check against lumies since e1_sweph can have 0 objects (user-selectable)
    if not app.e1_sweph.get("jd_ut") or not app.e2_sweph.get("jd_ut"):
        notify.error(
            "missing event 1 or 2 data needed for d1 : exiting ...",
            source="d1",
            route=[""],
        )
        return
    h_sys = (
        app.selected_house_sys.encode("ascii")
        if hasattr(app, "selected_house_sys")
        else "B".encode("ascii")  # alcabitus : gansten todo correct ???
    )
    # gather e1 data
    # msg += "running e1 data collection\n"
    e1_sweph = app.e1_sweph if hasattr(app, "e1_sweph") else None
    if e1_sweph:
        e1_jd = e1_sweph.get("jd_ut")
        e1_lat = e1_sweph.get("lat")
        e1_lon = e1_sweph.get("lon")
    # need tropical houses for d1
    e1_houses_ra = swe.houses(e1_jd, e1_lat, e1_lon, h_sys)
    e1_asc = e1_houses_ra[1][0]  # ascmc[0]
    e1_mc = e1_houses_ra[1][1]  # ascmc[1]
    e1_armc = e1_houses_ra[1][2]  # ascmc[2]
    # get true obliquity of ecliptic
    # flagret = swe_calc_ut(tjd_ut, swe.ECL_NUT)[x] > returns :
    # x[0] = true obliquity of the Ecliptic (includes nutation)
    # x[1] = mean obliquity of the Ecliptic
    # x[2] = nutation in longitude
    # x[3] = nutation in obliquity
    # e1_ecl = swe.calc_ut(e1_jd, swe.ECL_NUT)[0]
    # e1_obliquity0 = e1_ecl[0]
    # todo leave it
    # e1_obliquity1 = e1_ecl[1]
    # msg += (
    #     # f"e1housesra : {e1_houses_ra}\n"
    #     f"e1armc : {e1_armc}\n"
    #     # f"e1ecl(nut) : {e1_ecl}\n"
    #     f"e1obliquity0 [true] : {e1_obliquity0}\n"
    #     # f"e1obliquity1 [mean] : {e1_obliquity1}\n"
    # )
    # calculate tropical positions : valid for both zodiacs : prepare custom flag
    flag = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_EQUATORIAL
    is_topocentric = getattr(app, "is_topocentric", False)
    use_true_pos = getattr(app, "use_true_pos", False)
    # add flag if topocentric positions are wanted
    if is_topocentric:
        flag |= swe.FLG_TOPOCTR
    if use_true_pos:
        flag |= swe.FLG_TRUEPOS
    use_mean_node = (
        app.chart_settings["mean node"] if hasattr(app, "chart_settings") else False
    )
    msg += (
        f"topocentric : {is_topocentric}\nusetruepos : {use_true_pos}\nflag : {flag}\n"
    )
    e1_lat_rad = math.radians(e1_lat)
    # natal objects positions
    e1_pos_d1 = {}
    e1_sel_objs = getattr(app, "selected_objects_e1", None)
    if e1_jd and e1_sel_objs:
        for obj in e1_sel_objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            try:
                result = swe.calc_ut(e1_jd, code, flag)
                data = result[0] if isinstance(result, tuple) else result
                ra = data[0]
                decl = data[1]
                md = swe.difdeg2n(ra, e1_armc)
                decl_rad = math.radians(decl)
                ad_rad = math.asin(math.tan(decl_rad) * math.tan(e1_lat_rad))
                ad = math.degrees(ad_rad)
                pole = math.degrees(
                    math.atan(math.tan(decl_rad) / math.sin(math.radians(md)))
                )
                zpp = swe.degnorm(
                    e1_mc
                    + math.degrees(
                        math.atan(
                            math.cos(math.radians(pole)) * math.tan(math.radians(md))
                        )
                    )
                )
                e1_pos_d1[code] = {
                    "name": name,
                    "pole": pole,
                    "zpp": zpp,
                }
            except (swe.Error, ValueError) as e:
                notify.error(
                    f"tropical positions calculation failed for [e1] : {event}\n\tdata {name}\n\tswe error :\n\t{e}",
                    source="d1",
                    route=["terminal"],
                )
        # msg += f"e1posd1 :\n\t{e1_pos_d1}\n"
    if event == "e2":
        msg += "e2 detected\n"
        # msg += f"{e2_cleared(event)}"
        # gather e2 data
        e2_jd = app.e2_lumies.get("jd_ut")
        # objects list from sidepane > settings > objects panel
        e2_sel_objs = getattr(app, "selected_objects_e2", None)
        # msg += f"e2jd : {e2_jd}\ne2selobjs : {e2_sel_objs}\n"
        e2_pos_d1 = {}
        if e2_jd and e2_sel_objs and flag:
            for obj in e2_sel_objs:
                code, name = objcode(obj, use_mean_node)
                if code is None:
                    continue
                # calc_ut() returns array of 6 floats [0] + error string [1]:
                # longitude, latitude, distance, lon speed, lat speed, dist speed
                try:
                    result = swe.calc_ut(e2_jd, code, flag)
                    # msg += f"ra positions with speeds & flag used : {result}"
                    data = result[0] if isinstance(result, tuple) else result
                    # meridian distance from midheaven todo ???
                    # md_orig = data[0] - e1_armc
                    # md = swe.degnorm(data[0] - e1_armc)
                    md = swe.difdeg2n(data[0], e1_armc)
                    # ascensional difference (ad)
                    decl_rad = math.radians(data[1])
                    lat_rad = math.radians(e1_lat)
                    ad_rad = math.asin(math.tan(decl_rad) * math.tan(lat_rad))
                    ad = math.degrees(ad_rad)
                    # oblique ascension / descension
                    oa = swe.degnorm(data[0] - ad)
                    od = swe.degnorm(data[0] + ad)
                    # direction arc to ascendant
                    arc_asc = swe.difdeg2n(oa, e1_asc)
                    # arc to descendant
                    arc_dsc = swe.difdeg2n(od, e1_asc)
                    # zodiacal ptolemaic positon (zpp)
                    pole = math.degrees(
                        math.atan(math.tan(decl_rad) / math.sin(math.radians(md)))
                    )
                    zpp = swe.degnorm(
                        e1_mc
                        + math.degrees(
                            math.atan(
                                math.cos(math.radians(pole))
                                * math.tan(math.radians(md))
                            )
                        )
                    )
                    e2_pos_d1[code] = {
                        "name": name,
                        "ra": data[0],
                        "decl": data[1],
                        "md": md,
                        "ad": ad,
                        "oa": oa,
                        "od": od,
                        "arc_asc": arc_asc,
                        "arc_dsc": arc_dsc,
                        "pole": pole,
                        "zpp": zpp,
                        # "dist": data[2],
                        # "ra speed": data[3], # might be needed
                        # "decl speed": data[4],
                        # "dist speed": data[5],
                    }
                    # msg += f"{name} md [original] : {md_orig}\n"
                    # msg += (
                    #     f"{name}\n   md [mod] : {md}\n"
                    #     # f"   ascdiff : {ad}\n"
                    #     # f"   oblasc : {oa}\n   obldsc : {od}\n"
                    #     # f"   arcasc : {arc_asc}\n   arcdsc : {arc_dsc}\n"
                    #     f"   pole : {pole}\n   zpp : {zpp}\n"
                    # )
                except swe.Error as e:
                    notify.error(
                        f"tropical positions calculation failed for : {event}\n\tdata {name}\n\tswe error :\n\t{e}",
                        source="d1",
                        route=["terminal"],
                    )
            msg += f"e2posd1 :\n\t{e2_pos_d1}\n"
        # calculate final direction arcs between event 1 & 2
        directions = {}
        for e2_code, e2_obj in e2_pos_d1.items():
            e2_name = e2_obj["name"]
            directions[e2_name] = {}
            # mundane directions
            directions[e2_name]["mc"] = {
                "direct": e2_obj["md"],
            }
            directions[e2_name]["asc"] = {
                "direct": e2_obj["arc_asc"],
            }
            directions[e2_name]["dsc"] = {
                "direct": e2_obj["arc_dsc"],
            }
            # directions[e2_code] = {}
            for e1_code, e1_obj in e1_pos_d1.items():
                if e2_code == e1_code:
                    continue  # skip same object
                # pole_e2 = e2_obj["pole"]
                # pole_e1 = e1_obj["pole"]
                e1_name = e1_obj["name"]
                zpp_e2 = e2_obj["zpp"]
                zpp_e1 = e1_obj["zpp"]
                # direct zodiacal direction
                arc_dire = swe.difdeg2n(zpp_e2, zpp_e1)
                # converse direction
                # arc_conv = swe.difdeg2n(zpp_e1, zpp_e2)
                directions[e2_name][e1_name] = {
                    "direct": arc_dire,
                }
        # msg += f"directions :\n\t{directions}\n"
        # global store todo need ???
        app.d1_directions = directions
        # store zpp positions for chart drawing
        app.d1_positions = e2_pos_d1
        # sidereal flag is detected on settings change & stored application-wide
        # FLG_SIDEREAL vs FLG_TROPICAL (default)
        if getattr(app, "is_sidereal", False) and e2_jd:
            # apply ayanamsa to tropical positions
            cur_ayanamsa = swe.get_ayanamsa_ut(e2_jd)
            # cur_ayanamsa = swe.get_ayanamsa_ex_ut(e2_jd, flag)[1] if e2_jd else None
            # msg += f"curayan : {cur_ayanamsa}\n"
            # convert tropical to sidereal
            app.d1_positions = ra_to_sidereal(e2_pos_d1, cur_ayanamsa)
            # msg += f"possidereal :\n\t{app.d1_positions}\n"
        msg += f"d1pos :\n\t{app.d1_positions}\n"
        # make table
        # table = d1_table(directions)
        # msg += f"d1 table\n{table}"
    app.signal_manager._emit("d1_changed", event)
    notify.debug(
        msg,
        source="d1",
        route=["terminal"],
    )


def d1_table(directions):
    # prints a plain text table of primary directions
    col1_width = 3
    col2_width = 3
    col3_width = 8
    header = f" {'mov':<{col1_width}} | {'fix':<{col2_width}} | {'arc':<{col3_width}}"
    separ = "-" * len(header)
    table_lines = [header, separ]
    # data rows
    for e2_name, e1_objects in sorted(directions.items()):
        for e1_name, arcs in sorted(e1_objects.items()):
            arc_str = f"{arcs['direct']:.2f}"
            row = (
                f" {e2_name:<{col1_width}} > "
                f"{e1_name:<{col2_width}} | "
                f"{arc_str:<{col3_width}}"
            )
            table_lines.append(row)
    return "\n".join(table_lines)


def ra_to_sidereal(positions, ayanamsa):
    # convert zpp tropical positions to sidereal
    sid_pos = {}
    for code, data in positions.items():
        # avoid modifying original dict
        sid_data = data.copy()
        # subtract ayanamsa & normalize
        sid_data["zpp"] = swe.degnorm(data["zpp"] - ayanamsa)
        sid_pos[code] = sid_data
    # print(f"ratosid : {sid_pos}")
    return sid_pos


def e2_cleared(event):
    # todo clear all event 2 data
    if event == "e2":
        return "e2 was cleared : todo\n"


def connect_signals_d1(signal_manager):
    # update progressions when data used changes
    signal_manager._connect("event_changed", calculate_d1)
    signal_manager._connect("e2_cleared", e2_cleared)
