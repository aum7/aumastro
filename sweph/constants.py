# sweph/constants.py
SIGNS = {  # lord, element (fire earth water air), mode (movable fixed dual)
    "ari": ("ma", "fir", "mov"),  # 01 f m
    "tau": ("ve", "ear", "fix"),  # 02 e f
    "gem": ("me", "air", "dua"),  # 03 a d
    "can": ("mo", "wat", "mov"),  # 04 w m
    "leo": ("su", "fir", "fix"),  # 05 f f
    "vir": ("me", "ear", "dua"),  # 06 e d
    "lib": ("ve", "air", "mov"),  # 07 a m
    "sco": ("ma", "wat", "fix"),  # 08 w f
    "sag": ("ju", "fir", "dua"),  # 09 f d
    "cap": ("sa", "ear", "mov"),  # 10 e m
    "aqu": ("sa", "air", "fix"),  # 11 a f
    "pis": ("ju", "wat", "dua"),  # 12 w d
}
TERMS = {  # egyptian terms table: starting degree : ruler
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
    # 180: "sa",  # extends
    186: "me",
    194: "ju",
    201: "ve",
    208: "ma",
    # 210: "ma",  # extends
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
    1: ("ve", "leu"),  #    00-00-00 - 12-51-25 ari
    2: ("sa", "oei"),  #    12-51-25 - 25-42-51 ari
    3: ("su", "mao"),  #    25-42-51 - 08-34-17 tau (krt)
    4: ("mo", "pi"),  #     08-34-17 - 21-25-43 tau
    5: ("ma", "tsee"),  #   21-25-43 - 04-17-09 gem
    6: ("me", "shen"),  #   04-17-09 - 17-08-34 gem
    7: ("ju", "tsing"),  #  17-08-34 - 30-00-00 gem
    8: ("ve", "kwei"),  #   00-00-00 - 12-51-25 can
    9: ("sa", "lieu"),  #   12-51-25 - 25-42-51 can
    10: ("su", "sing"),  #  25-42-51 - 08-34-17 leo
    11: ("mo", "chang"),  # 08-34-17 - 21-25-43 leo
    12: ("ma", "yen"),  #   21-25-43 - 04-17-09 vir
    13: ("me", "tchin"),  # 04-17-09 - 17-08-34 vir
    14: ("ju", "kio"),  #   17-08-34 - 30-00-00 vir
    15: ("ve", "kang"),  #  00-00-00 - 12-51-25 lib
    16: ("sa", "ti"),  #    12-51-25 - 25-42-51 lib
    17: ("su", "fang"),  #  25-42-51 - 08-34-17 sco
    18: ("mo", "sin"),  #   08-34-17 - 21-25-43 sco
    19: ("ma", "wei"),  #   21-25-43 - 04-17-09 sag
    20: ("me", "ki"),  #    04-17-09 - 17-08-34 sag
    21: ("ju", "tow"),  #   17-08-34 - 30-00-00 sag
    22: ("ve", "nieu"),  #  00-00-00 - 12-51-25 cap
    23: ("sa", "mo"),  #    12-51-25 - 25-42-51 cap
    24: ("su", "heu"),  #   25-42-51 - 08-34-17 aqu
    25: ("mo", "gui"),  #   08-34-17 - 21-25-43 aqu
    26: ("ma", "shih"),  #  21-25-43 - 04-17-09 pis
    27: ("me", "peih"),  #  04-17-09 - 17-08-34 pis
    28: ("ju", "goei"),  #  17-08-34 - 30-00-00 pis
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
