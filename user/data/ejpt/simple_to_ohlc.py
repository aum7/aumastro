# user/data/ejpt/simple_to_ohlc.py
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
                "datetime": row["datetime"],
                "open": 0,
                "high": val,
                "low": 0,
                "close": val,
            })


simple_to_ohlc("ejpt.csv", "ejpt_bar.csv")
