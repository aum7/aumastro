# user/eventsdb/db.py
# add your event data here, i will be used as default event
# default data (state, city, location, name, date-time) for event 1 & 2
# IMPORTANT ! default country must be enabled in countries.py
# locations :
# "51 30 54 n 000 05 56 w" : lse
# "40 42 25 n 74 0 41 w 10 m" : nyse
# "datetime": "2025-03-29 10:47:34",  # last solecl
# "datetime": "2025 8 1 17 1", # trading start
DEFAULT_E1 = {
    "country": "UK",
    "city": "london",
    "location": "51 30 54 n 000 05 56 w 10 m",
    "name": "solecl ",  # next solecl
    "datetime": "2006-03-29 11:11:276",
    # "datetime": "2000 3 21 12 00",
}
DEFAULT_E2 = {
    "datetime": "2007-03-09 14:00:00",
}
# --- solar eclipses -----------------------------------------------------------
# 1999-08-11  11:04:09  145  -total  1999-08-11 12:03:15
# 2000-02-05  12:50:27  150  partial
# 2000-07-01  19:33:33  117  partial
# 2000-07-31  02:14:07  155  partial
# 2000-12-25  17:35:57  122  partial
# 2001-06-21  12:04:46  127  -total
# 2001-12-14  20:53:01  132  annular
# 2002-06-10  23:45:22  137  annular
# 2002-12-04  07:32:16  142  -total  2002-12-04 07:31:21
# 2003-05-31  04:09:22  147  annular
# 2003-11-23  22:50:22  152  -total  2003-11-23 22:49:27
# 2004-04-19  13:35:05  119  partial
# 2004-10-14  03:00:23  124  partial
# 2005-04-08  20:36:51  129  hybrid
# 2005-10-03  10:32:47  134  annular
# 2006-03-29  10:12:23  139  -total  2006-03-29 11:11:276
# 2006-09-22  11:41:16  144  annular
# 2007-03-19  02:32:57  149  partial
# 2007-09-11  12:32:24  154  partial
# 2008-02-07  03:56:10  121  annular
# 2008-08-01  10:22:12  126  -total
# 2009-01-26  07:59:45  131  annular
# 2009-07-22  02:36:25  136  -total
# 2010-01-15  07:07:39  141  annular
# 2010-07-11  19:34:38  146  -total
# 2011-01-04  08:51:42  151  partial
# 2011-06-01  21:17:18  118  partial
# 2011-07-01  08:39:30  156  partial
# 2011-11-25  06:21:24  123  partial
# 2012-05-20  23:53:54  128  annular
# 2012-11-13  22:12:55  133  -total
# 2013-05-10  00:26:20  138  annular
# 2013-11-03  12:47:36  143  hybrid
# 2014-04-29  06:04:33  148  annular (non-central)
# 2014-10-23  21:45:39  153  partial
# 2015-03-20  09:46:47  120  -total
# 2015-09-13  06:55:19  125  partial
# 2016-03-09  01:58:19  130  -total
# 2016-09-01  09:08:02  135  annular
# 2017-02-26  14:54:33  140  annular
# 2017-08-21  18:26:40  145  -total
# 2018-02-15  20:52:33  150  partial
# 2018-07-13  03:02:16  117  partial
# 2018-08-11  09:47:28  155  partial
# 2019-01-06  01:42:38  122  partial
# 2019-07-02  19:24:08  127  -total
# 2019-12-26  05:18:53  132  annular
# 2020-06-21  06:41:15  137  annular
# 2020-12-14  16:14:39  142  -total
# 2021-06-10  10:43:07  147  annular
# 2021-12-04  07:34:38  152  -total
# 2022-04-30  20:42:36 -119- partial 2022-04-30 21:41:41
# 2022-10-25  11:01:20  124  partial 2022-10-25 12:00:16
# 2023-04-20  04:17:56  129  hybrid
# 2023-10-14  18:00:41  134  annular 2023-10-14 18:59:40
# 2024-04-08  18:18:29  139  -total  2024-04-08 19:17:29
# 2024-10-02  18:46:13  144  annular
# 2025-03-29  10:48:36  149  partial 2025-03-29 10:47:34
# 2025-09-21  19:43:04  154  partial
# 2026-02-17  12:13:06  121  annular
# 2026-08-12  17:47:06  126  -total
# ------------------------------------------------------------------------------
# "country": "finland",
# "city": "vantaa",  # helsinki
# "location": "60 17 36 n 25 02 17 e 0038 m",
# "name":"ejpt",
# "datetime": "2012 03 23 21 00",
# ---
# "country": "usa",
# "city": "memphis",
# "location": "35 08 58 n 090 02 56 w 0085 m",
# "name":"lisa presley",
# "datetime": "1968 2 1 17 1",
# ---
# "country": "Slo",
# "city": "ljubljana",
# "location": "46 03 03 n 014 30 18 e 0294 m",
# "name": "simon",
# "datetime": "1975 2 8 14 10",
# --- houck p59
# "country": "USA",
# "city": "Garden City",  # ny
# "location": "40 44 00 n 073 58 00 w 0032 m",
# "name": "telly savalas",  # kojak actor
# "datetime": "1924-1-20 5:00:00",
# --- houck p59
# "country": "USA",
# "city": "cobleskill",  # ny
# "location": "42 40 40 n 074 29 07 w 0281 m",
# "name": "chart # 4",
# "datetime": "1946-5-30 16:33:00",
# --- houck p62
# "country": "USA",
# "city": "tupelo",  # mississippi
# "location": "34 15 29 n 088 42 16 w 0089 m",
# "name": "elvis presley",
# "datetime": "1935-1-8 16:35:00",  # died 1977-08-16
# --- houck p65
# "country": "USA",
# "city": "milton",  # ma
# "location": "42 14 58 n 071 03 58 w 0043 m",
# "name": "george bush",
# "datetime": "1924-6-12 15:45:30",  # died
# ---
# "country": "USA",
# "city": "Rahway",
# "location": "40 36 29 n 074 16 39 w 0007 m",
# "name": "houck # 3",
# "datetime": "1964-12-13 15:00:00",
# ---
# "country": "USA",
# "city": "philadelphia, pa",
# "location": "39 57 08 n 075 09 49 w 0046 m",
# "name": "usa 4.jul birth", # houck
# "datetime": "1776-6-19 11:53:00",
# ---
# "country": "Morocco",
# "city": "Agadir",
# "location": "30 25 12 n 009 35 53 w 0 m",
# "name": "solitaire",
# "datetime": "2024-6-19 11:53:00",
