# user/settings.py
# set default preferences : for sweph calculations & app settings
# recommended to setup before application start : usually once per user
# do not modify while application is running : results unknown
# settings can be changed in application > sidepane > settings panel
# some info / description is provided below as comments, details are in
# original sweph documentation, ie swephprg.pdf & swisseph.pdf at
# https://github.com/aloistr/swisseph/tree/master/doc
# for glyph explanation see ui/fonts/victor/...pdf
# main application panes orientation : horizontal vs vertical
# see uisetup.py > setup_paned_widgets
# todo not fully implemented : mainwindow.py > panes_x all need love
# app has 4 panes that can be resized - 2 (top/bottom) x 2  (left/right) -
# orientation can be top/bottom as main & left/right as children or vice-versa
# run app > grab left pane border & drag right ->, similar for top/bottom
APP_ORIENTATION = "vertical"
# change objects color & names below
OBJECTS = {  # one-but-last = color ; last = size scale = drawing order
    0: ("su", "sun", "sy", "surya", (1.0, 0.898, 0.0, 1), 0.82),
    1: ("mo", "moon", "ca", "candra", (0.95, 0.95, 0.95, 1), 0.73),
    2: ("me", "mercury", "bu", "budha", (0.2, 0.5, 0.2, 1), 0.76),
    3: ("ve", "venus", "sk", "sukra", (0.98, 0.45, 0.75, 1), 0.79),
    4: ("ma", "mars", "ma", "mangala", (0.7, 0.1, 0.1, 1), 0.85),
    5: ("ju", "jupiter", "gu", "guru", (0.7, 0.4, 0.0, 1), 0.88),
    6: ("sa", "saturn", "sa", "sani", (0.1176, 0.5647, 1.0, 1), 0.91),
    7: ("ur", "uranus", "ur", "uranus", (0.4, 0.4, 0.4, 1), 0.94),
    8: ("ne", "neptune", "ne", "neptune", (0, 0.2539, 0.4931, 1), 0.97),
    9: ("pl", "pluto", "pl", "pluto", (0.1784, 0.1784, 0.1784, 1), 1.0),
    11: ("ra", "true node", "ra", "rahu", (0.4, 0.3, 0.3, 1), 1.1),
    # 10: rahu mean handled in positions.py by usersettings.CHART_SETTINGS.usermeannode
    # heliocentric view
    # not implemented (deleted as some stubborn issue was persistent)
    # 14: ("ea", "earth", "ea", "earth"), ke color (0.3, 0.3, 0.3, 1)
}
# selected objects for event 2
OBJECTS_2 = {
    "su",
    "mo",
    "me",
    "ve",
    "ma",
    "ju",
    "sa",
    "ur",
    "ne",
    "pl",
    "ra",
}
LOTS = {  # 7 hermetic lots : many different definitions for lots exist
    # add your definitions & also update calculations in
    # sweph/calculations/lots.py (example given there) : example :
    # https://sarahsastrology.com/arabic-parts
    # LEGAL AFFAIRS   9th house cusp + 3rd house cusp - Venus :
    # "affairs+": {"day": "9th + 3rd - ve"},
    # day = diurnal birth calculation formula, ie sun is above horizon (asc-dsc)
    "fortuna": {
        "enable": True,  # todo False
        "day": "asc + (mo - su)",
        "tooltip": "body",
    },
    "spirit": {
        "enable": False,
        "day": "asc + (su - mo)",
        "tooltip": "soul & intelect",
    },
    "necessity": {
        "enable": False,
        "day": "(asc + (mo - su)) - me",
        "tooltip": "fortuna - me\nconstraints, war, enmity",
    },
    "eros": {
        "enable": False,
        "day": "ve - (asc + (su - mo))",
        "tooltip": "ve - spirit\napetite, desire",
    },
    "courage": {
        "enable": False,
        "day": "(asc + (mo - su)) - ma",
        "tooltip": "fortuna - ma\nboldness, treachery, strength, all evildoings",
    },
    "victory": {
        "enable": False,
        "day": "ju - (asc + (su - mo))",
        "tooltip": "ju - spirit\nfaith, contests, generosity, success",
    },
    "nemesis": {
        "enable": False,
        "day": "(asc + (mo - su)) - sa",  # vs night formula used for calculation
        "tooltip": "fortuna - sa\nunderworld, concealed, exposure, destruction",
    },
}
# prenatal events : syzygy & eclipses
PRENATAL = {
    "syzygy": {
        "enable": True,
        "tooltip": (
            "syzygy - last full or new moon before event 1"
            "\nnote : syzygy might overlap with eclipses (below)"
        ),
    },
    "eclipses": {
        "enable": True,
        "tooltip": (
            "last solar & lunar eclipse before event 1"
            "\nnote : eclipses might overlap with syzygy (above)"
        ),
    },
}
SWE_FLAGS = {
    # default flags for sweph calculations
    # all flags are duplicated & commented as backup ; user can toggle them in
    # settings panel which will update uncommented flags / values (this file)
    # --- use sidereal (jyotisa) zodiac : else use tropical (western) zodiac
    # FLG_SIDEREAL vs FLG_TROPICAL (default)
    "sidereal zodiac": (
        True,
        """use sidereal (vs tropical) zodiac
if checked also select ayanamsa below""",
    ),
    # --- calculate true, not apparent (visible from earth) positions
    # journey of the light from a planet to the earth takes some time
    # FLG_TRUEPOS
    "true positions": (True, "calculate true (vs apparent) positions"),
    # --- calculate topocentric positions, viewed from latitude & longitude of
    # event ; else calculate geocentric positions (default, used traditionally
    # in astrology), viewed from center of the earth
    # FLG_TOPOCTR
    "topocentric": (True, "calculate topocentric (vs geocentric) positions"),
    # --- calculate heliocentric positions : astrology uses geocentric positions
    # FLG_HELCTR
    # "heliocentric": (False, "calculate heliocentric (vs geocentric) positions"),
    # --- use default sweph ephemeris & speed calculations
    "default flag": (True, "use default (swiss ephemeris & speed) calculations"),
    # --- do NOT use nutation : small irregularity in the precession of the equinoxes
    # use mean equinox of date
    # FLG_NONUT
    "no nutation": (
        True,
        "do NOT use nutation if checked (small irregularity in equinoxes precession)",
    ),
    # --- astrometric (not used = FLG_NOABERR | FLG_NOGDEFL > both below)
    # the light-time correction is computed, but annual aberration and
    # light-deflection by the sun neglected
    # FLG_ASTROMETRIC
    # --- no abberation : small irregularity in the motion of the moons
    # FLG_NOABERR
    # "no abberation": (
    #     False,
    #     "do NOT use aberration if checked (small irregularity of moon)",
    # ),
    # --- no gravity deflection
    # FLG_NOGDEFL
    # "no deflection": (False, "do NOT use gravitational deflection if checked"),
    # --- return equatorial positions (right ascension & declination)
    # else return ecliptic (default, latitude & longitude) positions
    # FLG_EQUATORIAL
    # "equatorial": (False, "return equatorial (vs ecliptic) positions"),
    # --- return cartesian (x, y, z) else polar (default) coordinates
    # FLG_XYZ
    # "cartesian": (False, "return cartesian (x, y, z vs polar degrees) coordinates"),
    # --- return radian else degree (default) units
    # FLG_RADIANS
    # "radians": (False, "return radian (vs degree) units"),
}
# add or remove houses as you please
# https://astrorigin.com/pyswisseph/sphinx/programmers_manual/house_cusp_calculation.html?highlight=houses#swisseph.houses
# below are most popular 7 out of 24+; arrange line up or down as you please
# dropdown - top line is default choice
HOUSE_SYSTEMS = [
    ("O", "prp : porphyry", "prp"),
    ("W", "whs : whole sign", "whs"),  # jyotisa & houck
    ("E", "eqa : equal asc", "eqa"),
    ("B", "alc : alcabitus", "alc"),  # gansten : close to porphyry
    ("D", "eqm : equal mc", "eqm"),
    ("P", "plc : placidus", "plc"),
    ("R", "rgm : regiomontanus", "rgm"),
    ("C", "cmp : campanus", "cmp"),
    ("K", "kch : koch", "kch"),
]
# --- time constants ---
# dropdown : top is default
SOLAR_YEARS = [  # (solar) year lengths in days
    ("sid", 365.256363, "sidereal"),
    ("gre", 365.2425, "gregorian"),
    ("jul", 365.25, "julian"),
    ("trp", 365.24219, "tropical"),
    ("lun", 354.37, "lunar"),  # 12 * synodic lunar month
]
# dropdown : top is default
LUNAR_MONTHS = [  # lunar month lengths
    ("sid", 27.321661, "sidereal\t\tfixed star"),
    ("syn", 29.53059, "synodic\t\tnew moons"),
    ("trp", 27.321582, "tropical\t\t0 ari"),  # houck
    ("anm", 27.554551, "anomalistic\tperigee-apogee"),
    ("drc", 27.21222, "draconic\tlunar nodes"),
]
# !!! UNCOMMENT ANY AYANAMSA THAT YOU NEED !!!
# uncomment > delete '# ', indent properly, and save file
# also arrange order as you please > move line up / down & save file
# dropdown : top is default
AYANAMSAS = [
    (45, "Krishnamurti-Senthilathiban", "kms (45)"),  # SIDM_KRISHNAMURTI_VP291
    (17, "Galact. Center 0 Sag", "glc (17)"),  # SIDM_GALCENT_0SAG j2000 = 26°50'31.8335
    (255, "user-defined (below)", "usr"),  # SIDM_USER
    # 0: ("Fagan/Bradley", "fbr (00)"),  # SIDM_FAGAN_BRADLEY
    # 1: ("Lahiri 1", "lhr (01)"),  # SIDM_LAHIRI
    # 2: ("De Luce", "dlc (02)"),  # SIDM_DELUCE
    # 3: ("Raman", "rmn (03)"),  # SIDM_RAMAN
    # 4: ("Usha/Shashi", "uss (04)"),  # SIDM_USHASHASHI
    # 5: ("Krishnamurti", "kmr (05)"),  # SIDM_KRISHNAMURTI
    # 6: ("Djwhal Khul", "dwk (06)"),  # SIDM_DJWHAL_KHUL
    # 7: ("Yukteshwar", "ykt (07)"),  # SIDM_YUKTESHWAR
    # 8: ("J.N. Bhasin", "jnb (08)"),  # SIDM_JN_BHASIN
    # 9: ("Babylonian/Kugler 1", "bk1 (09)"),  # SIDM_BABYL_KUGLER1
    # 10: ("Babylonian/Kugler 2", "bk2 (10)"),  # SIDM_BABYL_KUGLER2
    # 11: ("Babylonian/Kugler 3", "bk3 (11)"),  # SIDM_BABYL_KUGLER3
    # 12: ("Babylonian/Huber", "bhb (12)"),  # SIDM_BABYL_HUBER
    # 13: ("Babylonian/Eta Piscium", "bep (13)"),  # SIDM_BABYL_ETPSC
    # 14: ("Babylonian/Aldebaran 15 Tau", "bat (14)"),  # SIDM_ALDEBARAN_15TAU
    # 15: ("Hipparchos", "hpc (15)"),  # SIDM_HIPPARCHOS
    # 16: ("Sassanian", "snn (16)"),  # SIDM_SASSANIAN
    # 18: ("J2000", "j20 (18)"),  # SIDM_J2000
    # 19: ("J1900", "j19 (19)"),  # SIDM_J1900
    # 20: ("B1950", "b50 (20)"),  # SIDM_B1950
    # 21: ("Suryasiddhanta", "ssd (21)"),  # SIDM_SURYASIDDHANTA
    # 22: ("Suryasiddhanta, mean Sun", "ssm (22)"),  # SIDM_SURYASIDDHANTA_MSUN
    # 23: ("Aryabhata", "ary (23)"),  # SIDM_ARYABHATA
    # 24: ("Aryabhata, mean Sun", "arm (24)"),  # SIDM_ARYABHATA_MSUN
    # 25: ("SS Revati", "ssr (25)"),  # SIDM_SS_REVATI
    # 26: ("SS Citra", "ssc (26)"),  # SIDM_SS_CITRA
    # 27: ("True Citra", "tct (27)"),  # SIDM_TRUE_CITRA
    # 28: ("True Revati", "trv (28)"),  # SIDM_TRUE_REVATI
    # 29: ("True Pushya (PVRN Rao)", "tps (29)"),  # SIDM_TRUE_PUSHYA
    # 30: ("Galactic Center (Gil Brand)", "gcb (30)"),  # SIDM_GALCENT_RGBRAND
    # 31: ("Galactic Equator (IAU1958)", "gei (31)"),  # SIDM_GALEQU_IAU1958
    # 32: ("Galactic Equator", "geq (32)"),  # SIDM_GALEQU_TRUE
    # 33: ("Galactic Equator mid-Mula", "gem (33)"),  # SIDM_GALEQU_MULA
    # 34: ("Skydram (Mardyks)", "skm (34)"),  # SIDM_GALALIGN_MARDYKS
    # 35: ("True Mula (Chandra Hari)", "tmh (35)"),  # SIDM_TRUE_MULA
    # 36: ("Dhruva/GC/Mula (Wilhelm)", "gcw (36)"),  # SIDM_GALCENT_MULA_WILHELM
    # 37: ("Aryabhata 522", "ary (37)"),  # SIDM_ARYABHATA_522
    # 38: ("Babylonian/Britton", "bbb (38)"),  # SIDM_BABYL_BRITTON
    # 39: ("Vedic Sheoran", "vsh (39)"),  # SIDM_TRUE_SHEORAN
    # 40: ("Cochrane (Gal.Center 0 Cap)", "gcc (40)"),  # SIDM_GALCENT_COCHRANE
    # 41: ("Galactic Equator (Fiorenza)", "gef (41)"),  # SIDM_GALEQU_FIORENZA
    # 42: ("Vettius Valens", "vvl (42)"),  # SIDM_VALENS_MOON
    # 43: ("Lahiri 1940", "lh2 (43)"),  # SIDM_LAHIRI_1940
    # 44: ("Lahiri VP285", "lh3 (44)"),  # SIDM_LAHIRI_VP285
    # 46: ("Lahiri ICRC", "lh4 (46)"),  # SIDM_LAHIRI_ICRC
]
CUSTOM_AYANAMSA = {
    # custom user-defined ayanamsa properties
    # julian day utc > reference date for custom ayanamsa calculation
    # default is for 2000-01-01 12:00 utc (julian day starts at noon)
    # if needed, get julian day utc online, then copy-paste the number here
    "custom julian day utc": 2451545.00000,
    # user-defined custom ayanamsa : must be decimal degrees
    # default is 23.76694445 (23° 46' 01"), as per richard houck's book
    # 'astrology of death', for 2000-01-01
    "custom ayanamsa": 23.76694444,
}
CHART_SETTINGS = {
    # --- use mean node else true node
    "use mean node": (
        False,
        "calculate mean node (vs default true node)",
    ),
    # ---
    "exact lunar month": (
        False,
        "calculate exact (vs average) lunar month length for progressions",
    ),
    # --- toggle glyphs visibility (shortcut)
    "enable glyphs": (True, "toggle glyphs visibility"),
    # --- show true midheaven & imum coeli when equal or whole house system is
    # selected : true mc / ic can differ by upto 2 signs in those cases
    # "true mc & ic": (
    #     True,
    #     "show true mc & ic when equal or whole house system is selected",
    # ),
    # --- rotate whole chart so ascendant is fixed at left (east)
    # else aries (mesha) 0° is fixed at left
    "fixed asc": (
        True,
        "rotate chart so ascendant is fixed at left (east)\nelse aries 0° is fixed at left (default)",
    ),
    # --- naksatras ring
    "naksatras ring": (
        False,
        """show 27 naksatras ring
1  asv\t2  bha\t3  krt
4  roh\t5  mrg\t6  ard
7  pun\t8  pus\t9  asl
10 mag\t11 pph\t12 uph
13 has\t14 cit\t15 sva
16 vis\t17 anu\t18 jye
19 mul\t20 pas\t21 uas
22 sra\t23 dha\t24 sat
25 pbh\t26 ubh\t27 rev""",
    ),
    # --- use 28 lunar mansions
    # rulership as per chinese astrology / vivian e robson - fixed stars ...
    "use 28 mansions": (
        True,
        """use 28 lunar mansions with chinese / arabian name
rulership changes to weekday order !
can be changed in
sweph / constants.py""",
    ),
    # --- start naksatras ring with which naksatra
    "first naksatra": (
        1,
        "start naksatras ring with any naksatra / lunar mansion\nrotate relative to 0° aries\n1 = asvini (standard)\n19 = mula\n22 = abhijit if 28 naksatras etc",
    ),
    # --- harmonics division ring : 0 hide | 1 egypt. terms (bounds) |
    # 1+ simple divisions, similar but NOT all equal to varga
    "harmonic ring": (
        "9",
        "harmonic (aka varga) ring\nempty : do NOT show | 1 : egypt. terms (bounds)\n2+ : simple harmonic for event 1 *similar* to varga\nterms can be changed in\nsweph / constants.py",
    ),
    # --- event 2 astro chart circles : draw progressions (p1 & p3) | returns | transit
    # calculated in sweph / calculations / ...
    "event 2 rings": {
        "transit": (False, "show transit for event 2\nhk : ctrl+1"),
        "transit varga": (
            False,
            "show (simple) transit varga / harmonic ring for event 2\nset varga in above harmonic ring\nhk : ctrl+2",
        ),
        "p2 progress": (
            False,
            "show secondary progression (p2) for event 2\nhk : ctrl+3\nchange in sweph / calculations / ...",
        ),
        "p3 progress": (
            False,
            "show tertiary progression (p3) for event 2\nhk : ctrl+4\ncalculations as per richard houck\nchange in sweph / calculations / ...",
        ),
        "p3m progress": (
            False,
            "show minor (tertiary) progression (p3m) for event 2\nhk : ctrl+5\nchange in sweph / calculations / ...",
        ),
        "d1 direction": (
            False,
            "show traditional primary direction (d1) for event 2\nhk : ctrl+6\ncalculations as per martin gansten / ptolemy\n[todo needs verification : current is simple calculation]\nchange in sweph / calculations / ...",
        ),
        "lunar return": (False, "show lunar return for event 2\nhk : ctrl+7"),
        "solar return": (
            False,
            "show solar return for event 2\nhk : ctrl+8",
        ),
    },
    # --- use varga positions for aspects
    # ctrl+v hotkey was 1st choice, but that defaults now for text paste
    # todo change to use harmonic aspect : also
    "use varga aspects": (
        True,
        "use *simple* varga / harmonic positions for aspects matrix calculation\nsort of 'harmonic aspectarian', in tables window\nhk : ctrl+h (toggle h1 <> hX)",
    ),
    # --- draw fixed stars
    # in user/fixedstars.py are categories of stars :
    # custom ; naksatras28 ; behenian15 ; robson118 ; alphabetical521
    # if you want stars different as they are in predefined categories,
    # add stars of interest into custom category
    # empty value = do not draw stars
    # for additional info see user/fixedstars.txt
    "fixed stars": (
        "custom",
        (
            "draw fixed stars inside signs circle"
            "\navailable categories :"
            "\n\tcustom | naksatras [28] | behenian [15]"
            "\nset empty to draw no stars"
            "\nmodify user/fixedstars.py > add / remove from custom"
        ),
    ),
    # --- astro chart angle ruler & hover info snapping distance (or angle)
    "snap tolerance": (
        "9.9",
        (
            "snap distance for angle ruler\nhk : shift+r (toggle measuring on / off)"
            "\nsnapping works :"
            "\n\trings : middle of rings for objects & signs & houses"
            "\n\tradix : at center of planets for natal objects"
            "\n\t\t& at house cusps & signs ring"
            "\nrecommended 10-15"
        ),
    ),
    # --- event data to be presented in chart info
    # construct your own 'chart info' format
    "chart info string": (
        r"{name}\n{date}\n{wday} {time_short} {hora}\n{city} @ {iso3}\n{lat}\n{lon}",
        r"""construct your own 'chart info' format : allowed fields :
    1: event {name} | 2: {datetime} | 3: {date} | 4: {time}
    5: {time_short} no seconds | 6: {hora} glyph
    7: {wday} weekday 8: {country} | 9: {iso3} country code
    10: {city} 11: {location} | 12: {lat}itude
    13: {lon}gitude 14: {timezone} | 15: timezone {offset}
    16: moon {nak}satra 17: {nakvar} moon varga naksatra
    chars: @ | - :
\n = new line
example : {name}\n{date}\n{wday} {time_short}\n{city} @ {country}\n{lat}\n{lon}""",
    ),
    # - data same for both charts
    # additional 'chart info' format: allowed fields: 1: house system {hsys} |
    # 2: {zod}iac | 3: ayanamsa name {aynm} | 4: ayanamsa value {ayvl}
    "chart info extra": (
        r"{hsys} | {zod}\n{aynm}",
        r"""additional 'chart info' format : allowed fields :
    1: {hsys} house system
    2: {zod}iac
    3: {aynm} ayanamsa name & number
    chars: @ | - :
\n = new line
example : {hsys} | {zod}\n{aynm}""",
    ),
}
FILES = {
    # --- path to ephemerides folder, with min semo_18.se1 & sepl_18.se1 files, or
    # a complete ephe folder https://github.com/aloistr/swisseph/tree/master/ephe
    # todo separate path for linux & mswindows : do we need to ?
    "ephe path": (
        "sweph/ephe/",
        "path to ephemeride folder, with min semo_18.se1 & sepl_18.se1 files, "
        "or a complete ephe folder https://github.com/aloistr/swisseph/tree/master/ephe ",
    ),
    # --- fonts for glyphs = astro_font & for ie tables = mono_font
    "astro font": (
        "ui/fonts/osla/opensanslightastro.ttf",
        "font with glyphs for astro chart etc",
    ),
    "mono font": (
        "ui/fonts/victor/victormonolightastro.ttf",
        "mono-spaced font for pretty tables etc",
    ),
    # --- path to events / birth charts database folder; inside go saved charts
    "events db": (
        "user/eventsdb/",
        "path to event / birth charts database folder : inside go saved charts",
    ),
    # --- path to data folder & file ; data to be plotted on graph
    "data": (
        "user/data/gold/gold_h_utc.csv",
        # "user/data/gold/gold_d.csv",
        "path to data folder & file name : data for plotting on graph",
    ),
    # --- construct your own 'filename' format: allowed fields
    # 1: event {name} | 2: event {date} | 3: {time}
    # separate fields with '_' underscore ; for short time format (no seconds)
    # use {time_short} ; see default value as example
    # todo unused
    "filename": (
        r"{name}_{date}_{time_short}",
        "construct your own 'save filename' format : allowed fields"
        "\n\t1: event {name} | 2: event {date} | 3: {time}"
        "\nseparate fields with '_' underscore ; for short time format "
        "(no seconds) use {time_short}"
        "\nexample : {name}_{date}_{time_short}",
    ),
}
