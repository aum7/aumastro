# user/data/ejpt/simple_to_ohlc.py
# plotting simple format - single values as bars - using existing ohlc logic
# simple to ohlc : datetime, value > datetime, 0, value, 0, value
# useful for analysing large datasents - plot them then graph-click to obtain
# datetime & sync astrochart output - format :
# datetime,value         > datetime,value,0,value,0
# 2012.05.11 21:00:00,19 > 2012.05.11 21:00,19.0,0.0,19.0,0.0
import csv


def simple_to_ohlc(input_file, output_file):
    """convert datetime, value to ohlc candle"""
    with open(input_file) as f_in, open(output_file, "w") as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(
            f_out, fieldnames=["datetime", "open", "high", "low", "close"]
        )
        writer.writeheader()
        for row in reader:
            val = float(row["value"])
            writer.writerow({
                "datetime": row["datetime"][:16],
                "open": val,
                "high": 0,
                "low": val,
                "close": 0,
            })


# change ejpt.csv for your input file, ejpt_bar.csv for output file
simple_to_ohlc("ejpt.csv", "ejpt_bar.csv")
