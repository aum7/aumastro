# clean_gold_csv.py
import pandas as pd
from pathlib import Path

def clean_gold_csv():
    csv_path = Path("/home/mua/dev/venaumastro/aumastro/user/data/gold/gold_d_utc.csv")
    backup_path = csv_path.with_suffix(".csv. backup")
    
    # backup original
    import shutil
    shutil.copy(csv_path, backup_path)
    print(f"backup created: {backup_path}")
    
    # read csv
    df = pd.read_csv(csv_path)
    
    # normalize datetime column (handles both formats)
    df["datetime"] = pd.to_datetime(
        df["datetime"],
        format="mixed",
        errors="coerce"
    )
    
    # check for parsing failures
    null_count = df["datetime"].isna().sum()
    if null_count > 0:
        print(f"warning: {null_count} datetimes failed to parse")
        print(df[df["datetime"].isna()])
        # drop failed rows
        df = df.dropna(subset=["datetime"])
    
    # keep only ohlc columns
    df = df[["datetime", "open", "high", "low", "close"]]
    
    # sort by datetime
    df = df.sort_values("datetime")
    
    # remove duplicates
    df = df.drop_duplicates(subset=["datetime"], keep="first")
    
    # standardize datetime format:  YYYY-MM-DD HH:MM: SS
    df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # save cleaned csv
    df.to_csv(csv_path, index=False)
    
    print(f"cleaned csv saved:  {csv_path}")
    print(f"total entries: {len(df)}")
    print(f"columns: {list(df.columns)}")
    print(f"date range:\n  {df['datetime'].iloc[0]}\n  {df['datetime']. iloc[-1]}")
    
    # show sample
    print("\nfirst 3 entries:")
    print(df.head(3).to_string(index=False))
    print("\nlast 3 entries:")
    print(df.tail(3).to_string(index=False))

if __name__ == "__main__":
    clean_gold_csv()
