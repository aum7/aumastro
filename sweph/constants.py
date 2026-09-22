# sweph/constants.py
# sign lord (own rasi) — 7-planet classical rulership, no rahu/ketu lordship
# dict order doubles as sign order ar-pi (py3.7+ preserves insertion order)
SIGN_LORDS = {
    "ar": "ma",
    "ta": "ve",
    "ge": "me",
    "cn": "mo",
    "le": "su",
    "vi": "me",
    "li": "ve",
    "sc": "ma",
    "sg": "ju",
    "cp": "sa",
    "aq": "sa",
    "pi": "ju",
}
SIGNS_ORDER = tuple(SIGN_LORDS.keys())
# exaltation : (sign, exact degree within sign) — bphs 3.50
# debilitation = 7th sign from exaltation sign, same degree
EXALTATION = {
    "su": ("ar", 10.0),
    "mo": ("ta", 3.0),
    "ma": ("cp", 28.0),
    "me": ("vi", 15.0),
    "ju": ("cn", 5.0),
    "ve": ("pi", 27.0),
    "sa": ("li", 20.0),
}
# moolatrikona : (sign, deg_start, deg_end)
# remaining degrees of that sign (outside this range, up to 30) are own-sign
MOOLATRIKONA = {
    "su": ("le", 0.0, 20.0),
    "mo": ("ta", 3.0, 30.0),  # after its own 0-3 exaltation span
    "ma": ("ar", 0.0, 12.0),
    "me": ("vi", 15.0, 25.0),  # after its own 0-15 exaltation span
    "ju": ("sg", 0.0, 20.0),
    "ve": ("li", 0.0, 20.0),
    "sa": ("aq", 0.0, 20.0),
}
# planetary gender — bphs classical assignment
GENDER = {  # drekkana bala : male / female / neuter
    "su": "m",
    "ma": "m",
    "ju": "m",
    "mo": "f",
    "ve": "f",
    "me": "n",
    "sa": "n",
}
# trimsamsa (D30) : sign-parity dependent, unequal degree spans, lord per span
TRIMSAMSA_ODD = [(5.0, "ma"), (10.0, "sa"), (18.0, "ju"), (25.0, "me"), (30.0, "ve")]
TRIMSAMSA_EVEN = [(5.0, "ve"), (12.0, "me"), (20.0, "ju"), (25.0, "sa"), (30.0, "ma")]
# naisargika maitri (natural friendship)
NATURAL_FRIENDS = {  # unlisted planet-pairs default to neutral
    "su": {"friend": ("mo", "ma", "ju"), "enemy": ("ve", "sa")},
    "mo": {"friend": ("su", "me"), "enemy": ()},
    "ma": {"friend": ("su", "mo", "ju"), "enemy": ("me",)},
    "me": {"friend": ("su", "ve"), "enemy": ("mo",)},
    "ju": {"friend": ("su", "mo", "ma"), "enemy": ("me", "ve")},
    "ve": {"friend": ("me", "sa"), "enemy": ("su", "mo")},
    "sa": {"friend": ("me", "ve"), "enemy": ("su", "mo", "ma")},
}
# dig bala reference cusp per planet
DIG_BALA_REF_CUSP = {
    "su": 3,
    "ma": 3,  # bandhu bhava, 4th house
    "ju": 6,
    "me": 6,  # yuvati bhava, 7th house
    "ve": 9,
    "mo": 9,  # karma bhava, 10th house
    "sa": 0,  # lagna, 1st house
}
# saptavargaja bala : virupas per dignity tier, per division
SAPTAVARGA_SCALE = {
    "moolatrikona": 45.0,
    "own": 30.0,  # svastha
    "great friend": 20.0,  # pramudita
    "friend": 15.0,  # santa
    "neutral": 10.0,  # dina
    "enemy": 4.0,  # duhkhita
    "great enemy": 2.0,  # khala
}
# ahargana : days elapsed since creation epoch, per burgess/surya siddhanta anchor
# anchor : 714,404,108,573 days at 1860-01-01 00:00 ut (jd 2400410.5)
AHARGANA_ANCHOR_JD = 2400410.5
AHARGANA_ANCHOR_DAYS = 714404108573.0
WEEKDAY_LORDS = (  # remainder 1..7, 0 treated as 7
    "su",
    "mo",
    "ma",
    "me",
    "ju",
    "ve",
    "sa",
)
# rasi dristi : sign-to-sign aspect
MOVABLE = ("ar", "cn", "li", "cp")
FIXED = ("ta", "le", "sc", "aq")
DUAL = ("ge", "vi", "sg", "pi")
BHAVA_DIG_REF = {  # sagittarius and capricorn split at 15°
    "ge": 6,
    "vi": 6,
    "li": 6,
    "aq": 6,  # yuvati bhava, 7th cusp (idx 6)
    "ar": 3,
    "ta": 3,
    "le": 3,  # bandhu bhava, 4th cusp (idx 3)
    "cn": 0,
    "sc": 0,  # lagna, 1st cusp (idx 0)
    "pi": 9,  # karma bhava, 10th cusp (idx 9)
}
SIRSHODAYA = ("ge", "le", "vi", "li", "sc", "aq")  # day-birth bonus signs
PRISHTHODAYA = ("ar", "ta", "cn", "sg", "cp")  # night-birth bonus signs
# twilight bonus reuses existing DUAL = ("ge","vi","sg","pi")
#  vimsottari - 9 maha dasa year lengths
DASA_YEARS = {
    "ke": 7,
    "ve": 20,
    "su": 6,
    "mo": 10,
    "ma": 7,
    "ra": 18,
    "ju": 16,
    "sa": 19,
    "me": 17,
}
# order of planetary hours
HORAS_ORDER = ["sa", "ju", "ma", "su", "ve", "me", "mo"]
# standard planetary order
PLANETARY_ORDER = (
    "mo",
    "me",
    "ve",
    "su",
    "ma",
    "ju",
    "sa",
    "ur",
    "ne",
    "pl",
    "ra",
)
# retro periods
# legend :
#     Rl - average length of retro period
#     f - (yearly) frequency
#     as - average speed
#     ms - max speed
# obj : Rl     : f                   : as    : ms
# me : 21 d    : 3 times a year      : 1.607 : 1.6667  # (6') 5' / d : 24 h
# ve : 40-44 d : every 18 months     : 1.174 : 1.25  # 3' / d : 3 d 4 h
# ma : 60-80 d : every 26 months     : 0.524 : 0.7833  # 90" / d : 6 d 12 h
# ju : 4 m     : every 13 months     : 0.083 : 0.2333  # 60" / d : 7 d
# sa : 4.5 m   : every 12 1/2 months : 0.033 : 0.12472  # 60" /  : 7 d
# ur : 5 m     : every 12 months     : 0.012 : 0.05722  # 20" / d : 6 d 12 h
# ne : 5 m 6 d : every 12 months     : 0.006 : 0.038055556  # 10" / d
# pl : 5-6 m   : every 12 months     : 0.004 : 0.036388889  # 10" / d
RETRO_DAYS = {  # average length of retro period
    # su mo never retro
    2: 21.0,  # "me"
    3: 42.0,  # "ve"
    4: 70.0,  # "ma"
    5: 120.0,  # "ju"
    6: 135.0,  # "sa"
    7: 150.0,  # "ur"
    8: 156.0,  # "ne"
    9: 168.0,  # "pl"
}
STATION_SPEED = {  # stationary speed
    # su mo never stationary
    2: 0.08333,  # "me"
    3: 0.05,  # "ve"
    4: 0.025,  # "ma"
    5: 0.016666667,  # "ju"
    6: 0.016666667,  # "sa"
    7: 0.005555556,  # "ur"
    8: 0.002777778,  # "ne"
    9: 0.002777778,  # "pl"
}
# average planet speeds
AVG_SPEEDS = {
    0: 0.9856,  # sun
    1: 13.1764,  # moon
    2: 1.607,  # mercury
    3: 1.174,  # venus
    4: 0.524,  # mars
    5: 0.0831,  # jupiter
    6: 0.0335,  # saturn
    7: 0.0117,  # uranus
    8: 0.0060,  # neptune
    9: 0.0039,  # pluto
    10: 0.0529,  # mean node (retrograde)
    11: 0.0529,  # true node (retrograde)
}
TERMS = {  # egyptian terms table
    # starting degree : ruler
    0: "ju",
    6: "ve",
    12: "me",
    20: "ma",
    25: "sa",
    30: "ve",
    38: "me",
    44: "ju",
    52: "sa",
    57: "ma",
    60: "me",
    66: "ju",
    72: "ve",
    77: "ma",
    84: "sa",
    90: "ma",
    97: "ve",
    103: "me",
    109: "ju",
    116: "sa",
    120: "ju",
    126: "ve",
    131: "sa",
    138: "me",
    144: "ma",
    150: "me",
    157: "ve",
    167: "ju",
    171: "ma",
    178: "sa",
    # 180: "sa",  # extends previous term = same ruler
    186: "me",
    194: "ju",
    201: "ve",
    208: "ma",
    # 210: "ma",  # extends previous term = same ruler
    217: "ve",
    221: "me",
    229: "ju",
    234: "sa",
    240: "ju",
    252: "ve",
    257: "me",
    261: "sa",
    266: "ma",
    270: "me",
    277: "ju",
    284: "ve",
    292: "sa",
    296: "ma",
    300: "me",
    307: "ve",
    313: "ju",
    320: "ma",
    325: "sa",
    330: "ve",
    342: "ju",
    346: "me",
    349: "ma",
    358: "sa",
}
NAKSATRAS27 = {
    # ruler - name
    1: ("ke", "asv"),  #  00-00 - 13-20 ari
    2: ("ve", "bha"),  #  13-20 - 26-40 ari
    3: ("su", "krt"),  #  26-40 - 10-00 tau
    4: ("mo", "roh"),  #  10-00 - 23-20 tau
    5: ("ma", "mrg"),  #  23-20 - 06-40 gem
    6: ("ra", "ard"),  #  06-40 - 20-00 gem
    7: ("ju", "pun"),  #  20-00 - 03-20 can
    8: ("sa", "pus"),  #  03-20 - 16-40 can
    9: ("me", "asl"),  #  16-40 - 30-00 can
    10: ("ke", "mag"),  # 00-00 - 13-20 leo
    11: ("ve", "ppa"),  # 13-20 - 26-40 leo
    12: ("su", "upa"),  # 26-40 - 10-00 vir
    13: ("mo", "has"),  # 10-00 - 23-20 vir
    14: ("ma", "cit"),  # 23-20 - 06-40 lib
    15: ("ra", "sva"),  # 06-40 - 20-00 lib
    16: ("ju", "vis"),  # 20-00 - 03-20 sco
    17: ("sa", "anu"),  # 03-20 - 16-40 sco
    18: ("me", "jye"),  # 16-40 - 30-00 sco
    19: ("ke", "mul"),  # 00-00 - 13-20 sag
    20: ("ve", "pas"),  # 13-20 - 26-40 sag
    21: ("su", "uas"),  # 26-40 - 10-00 cap
    22: ("mo", "sra"),  # 10-00 - 23-20 cap
    23: ("ma", "dha"),  # 23-20 - 06-40 aqu
    24: ("ra", "sat"),  # 06-40 - 20-00 aqu
    25: ("ju", "pba"),  # 20-00 - 03-20 pis
    26: ("sa", "uba"),  # 03-20 - 16-40 pis
    27: ("me", "rev"),  # 16-40 - 30-00 pis
}
MANSIONS28 = {  # 12-51-25
    # source : vivian robson - fixed stars & constellations in astrology
    # ruler - chinese - arabic name
    1: ("ve", "leu", "al thurayya"),  #    00-00-00 - 12-51-25 ari
    2: ("sa", "oei", "al dabaran"),  #    12-51-25 - 25-42-51 ari
    3: ("su", "mao", "al hak'ah"),  #    25-42-51 - 08-34-17 tau (krt)
    4: ("mo", "pi", "al han'ah"),  #     08-34-17 - 21-25-43 tau
    5: ("ma", "tsee", "al dhira"),  #   21-25-43 - 04-17-09 gem
    6: ("me", "shen", "al nathrah"),  #   04-17-09 - 17-08-34 gem
    7: ("ju", "tsing", "al tarf"),  #  17-08-34 - 30-00-00 gem
    8: ("ve", "kwei", "al jabhah"),  #   00-00-00 - 12-51-25 can
    9: ("sa", "lieu", "al zubrah"),  #   12-51-25 - 25-42-51 can
    10: ("su", "sing", "al sarfah"),  #  25-42-51 - 08-34-17 leo
    11: ("mo", "chang", "al awwa"),  # 08-34-17 - 21-25-43 leo
    12: ("ma", "yen", "al simak"),  #   21-25-43 - 04-17-09 vir
    13: ("me", "tchin", "al ghafr"),  # 04-17-09 - 17-08-34 vir
    14: ("ju", "kio", "al jubana"),  #   17-08-34 - 30-00-00 vir
    15: ("ve", "kang", "iklil al jabhah"),  #  00-00-00 - 12-51-25 lib
    16: ("sa", "ti", "al kalb"),  #    12-51-25 - 25-42-51 lib
    17: ("su", "fang", "al shaulah"),  #  25-42-51 - 08-34-17 sco
    18: ("mo", "sin", "al na'am"),  #   08-34-17 - 21-25-43 sco
    19: ("ma", "wei", "al baldah"),  #   21-25-43 - 04-17-09 sag
    20: ("me", "ki", "al sa'd al dhabih"),  #    04-17-09 - 17-08-34 sag
    21: ("ju", "tow", "al sa'd al bula"),  #   17-08-34 - 30-00-00 sag
    22: ("ve", "nieu", "al sa'd al su'ud"),  #  00-00-00 - 12-51-25 cap
    23: ("sa", "mo", "al sa'd al ahbiyah"),  #    12-51-25 - 25-42-51 cap
    24: ("su", "heu", "al fargh al mukdim"),  #   25-42-51 - 08-34-17 aqu
    25: ("mo", "gui", "al fargh al thani"),  #   08-34-17 - 21-25-43 aqu
    26: ("ma", "shih", "al batn al hut"),  #  21-25-43 - 04-17-09 pis
    27: ("me", "peih", "al sharatain"),  #  04-17-09 - 17-08-34 pis
    28: ("ju", "goei", "al butain"),  #  17-08-34 - 30-00-00 pis
}
TOKENS = (
    "in",
    "max",
    "min",
    "decl",
    "zero",
    "ingr",
    "speed",
    "next",
    "prev",
    "asc",
    "mc",
    "varg",
)
