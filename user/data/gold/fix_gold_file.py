# fix_gold_file.py
# robust line-by-line csv normalizer for gold ohlc data
# produces: datetime,open,high,low,close with datetime = yyyy-mm-dd hh:mm
from pathlib import Path
import argparse
import shutil
import re
from typing import List, Optional

import pandas as pd

FILE_PATH = "./gold_d.csv"

DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(:\d{2})?$")
TIME_ONLY_RE = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")


def try_parse_datetime(s: str) -> Optional[pd.Timestamp]:
    """try to parse datetime string, return timestamp or None"""
    try:
        ts = pd.to_datetime(s.strip(), errors="coerce")
        if pd.isna(ts):
            return None
        return ts.tz_localize(None) if getattr(ts, "tzinfo", None) else ts
    except Exception:
        return None


def clean_line_tokens(tokens: List[str]) -> List[str]:
    """strip tokens and remove empty tokens produced by trailing commas"""
    return [t.strip() for t in tokens if t is not None and t.strip() != ""]


def parse_line(line: str) -> Optional[tuple]:
    """parse one csv line into (datetime, open, high, low, close)
    supports two common row shapes:
    - date, hour, open, high, low, close
    - datetime, open, high, low, close
    returns None for header / invalid lines
    """
    # quick skip
    if not line:
        return None
    s = line.strip()
    if not s or s.startswith("#"):
        return None

    parts = [p.strip() for p in s.split(",")]
    if not parts:
        return None

    # header detection: if any non-numeric text present in first row
    first = parts[0].lower()
    if "datetime" in first or "date" in first and "open" in s.lower():
        return None

    # case: date + hour + ohlc  (6 tokens)
    if (
        len(parts) >= 6
        and DATE_ONLY_RE.match(parts[0])
        and TIME_ONLY_RE.match(parts[1])
    ):
        dt_str = parts[0] + " " + parts[1]
        dt = try_parse_datetime(dt_str)
        if dt is None:
            return None
        # open, high, low, close are next four tokens
        try:
            op = float(parts[2].replace(",", ""))
            hi = float(parts[3].replace(",", ""))
            lo = float(parts[4].replace(",", ""))
            cl = float(parts[5].replace(",", ""))
            return dt, op, hi, lo, cl
        except Exception:
            return None

    # case: full datetime in first token + ohlc (5 tokens)
    if DATETIME_RE.match(parts[0]) and len(parts) >= 5:
        dt = try_parse_datetime(parts[0])
        if dt is None:
            return None
        try:
            op = float(parts[1].replace(",", ""))
            hi = float(parts[2].replace(",", ""))
            lo = float(parts[3].replace(",", ""))
            cl = float(parts[4].replace(",", ""))
            return dt, op, hi, lo, cl
        except Exception:
            return None

    # fallback: try to find a token that parses as datetime and then take four
    # numeric tokens after it
    for i, tok in enumerate(parts):
        dt = try_parse_datetime(tok)
        if dt is not None and i + 4 < len(parts):
            try:
                op = float(parts[i + 1].replace(",", ""))
                hi = float(parts[i + 2].replace(",", ""))
                lo = float(parts[i + 3].replace(",", ""))
                cl = float(parts[i + 4].replace(",", ""))
                return dt, op, hi, lo, cl
            except Exception:
                continue

    # nothing matched
    return None


def clean_gold_csv(path: Path, backup: bool = True) -> None:
    """read file line-by-line and build a cleaned dataframe"""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} not found")

    # backup original
    if backup:
        backup_path = csv_path.with_suffix(csv_path.suffix + ".backup")
        shutil.copy2(csv_path, backup_path)
        print(f"backup created: {backup_path}")

    parsed_rows = []
    line_no = 0
    with csv_path.open("r", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line_no += 1
            parsed = parse_line(raw)
            if parsed is None:
                continue
            dt, op, hi, lo, cl = parsed
            parsed_rows.append({
                "datetime": dt,
                "open": op,
                "high": hi,
                "low": lo,
                "close": cl,
            })

    if not parsed_rows:
        raise RuntimeError("no valid rows parsed from input file")

    df = pd.DataFrame(parsed_rows)
    # drop rows with any missing numeric values
    before = len(df)
    df = df.dropna(subset=["open", "high", "low", "close", "datetime"])
    dropped = before - len(df)
    if dropped:
        print(f"dropped {dropped} invalid rows after parsing")

    # sort, dedupe by datetime
    df = df.sort_values("datetime")
    df = df.drop_duplicates(subset=["datetime"], keep="first")

    # format datetime to minute precision (no seconds)
    df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%d %H:%M")

    # reorder and save
    out = df[["datetime", "open", "high", "low", "close"]]
    out.to_csv(csv_path, index=False)
    print(f"cleaned csv saved: {csv_path}")
    print(f"total entries: {len(out)}")
    if len(out):
        print("date range:")
        print(f"  {out['datetime'].iloc[0]}")
        print(f"  {out['datetime'].iloc[-1]}")
        print("\nfirst 3 entries:")
        print(out.head(3).to_string(index=False))
        print("\nlast 3 entries:")
        print(out.tail(3).to_string(index=False))


def main():
    p = argparse.ArgumentParser(description="clean ohlc data file for aumastro")
    p.add_argument(
        "csv",
        nargs="?",
        default=FILE_PATH,
        help=f"path to ohlc csv data file (ie {FILE_PATH})",
    )
    p.add_argument("--nobackup", action="store_true", help="do not create backup")
    args = p.parse_args()
    clean_gold_csv(Path(args.csv), backup=not args.nobackup)


if __name__ == "__main__":
    main()
