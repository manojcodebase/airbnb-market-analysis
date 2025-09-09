import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Use your real file name by default; override via .env if you want
DATA_PATH = os.getenv("DATA_PATH", "data/Airbnb_Open_Data.csv")
OUT_PARQUET_PATH = os.getenv("OUT_PARQUET_PATH", "data/clean_airbnb_listings.parquet")

def load_raw(path: str) -> pd.DataFrame:
    """Load raw Airbnb listings data from a CSV file."""
    print(f"[load] {path}")
    return pd.read_csv(path, low_memory=False)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize headers to snake_case so we can use consistent names:
    'number of reviews' -> 'number_of_reviews', 'service fee' -> 'service_fee', etc.
    """
    df = df.copy()
    df.columns = (
        df.columns
          .str.strip()
          .str.lower()
          .str.replace(r"\s+", "_", regex=True)
    )
    return df

def clean_currency_cols(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Clean currency-like columns: strip $, commas, to float; ignore missing columns."""
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[\$,]", "", regex=True)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def parse_date_cols(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Parse date columns to datetime format if present."""
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def fill_missing_values(df: pd.DataFrame, cols_with_defaults: dict) -> pd.DataFrame:
    """Fill missing values only for columns that exist."""
    df = df.copy()
    for col, default in cols_with_defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)
    return df

def remove_outliers_bounds(df: pd.DataFrame, col: str, lower: float, upper: float) -> pd.DataFrame:
    """Remove outliers using simple hard bounds if the column exists."""
    if col not in df.columns:
        return df
    return df[(df[col].isna()) | ((df[col] >= lower) & (df[col] <= upper))]

def remove_outliers_quantile(df: pd.DataFrame, col: str, lo_q=0.01, hi_q=0.99) -> pd.DataFrame:
    """Alternative: remove rows outside quantile range."""
    if col not in df.columns:
        return df
    lo = df[col].quantile(lo_q)
    hi = df[col].quantile(hi_q)
    return df[(df[col].isna()) | ((df[col] >= lo) & (df[col] <= hi))]

def sanity_checks(df: pd.DataFrame) -> None:
    """Perform simple sanity checks (skip if columns missing)."""
    if "price" in df.columns:
        assert df["price"].dropna().min() >= 0, "Price column has negative values"
    if "number_of_reviews" in df.columns:
        assert df["number_of_reviews"].dropna().min() >= 0, "Number of reviews has negative values"
    if "reviews_per_month" in df.columns:
        assert df["reviews_per_month"].dropna().min() >= 0, "Reviews per month has negative values"
    if "availability_365" in df.columns:
        s = df["availability_365"].dropna()
        assert s.min() >= 0, "Availability 365 has negative values"
        assert s.max() <= 365, "Availability 365 exceeds 365"

def main():
    df = load_raw(DATA_PATH)
    print(f"[debug] Loaded DataFrame shape: {df.shape}")
    print(f"[debug] Output path: {OUT_PARQUET_PATH}")

    # 1) Normalize headers once so we can use snake_case everywhere
    df = normalize_columns(df)

    # Heads-up: after normalization, your actual dataset columns are like:
    # 'service_fee', 'number_of_reviews', 'reviews_per_month', 'availability_365', 'last_review'
    # (from original: 'service fee', 'number of reviews', 'reviews per month', 'availability 365', 'last review')

    # 2) Currency columns that exist in THIS dataset (adjust if you later add more)
    currency_cols_present = [c for c in ["price", "service_fee"] if c in df.columns]
    df = clean_currency_cols(df, currency_cols_present)

    # 3) Date columns that exist in THIS dataset
    df = parse_date_cols(df, ["last_review"])

    # 4) Fill sensible defaults (only if the column exists)
    cols_with_defaults = {
        "reviews_per_month": 0.0,
        "host_identity_verified": "unknown",  # this is text in your dataset
    }
    df = fill_missing_values(df, cols_with_defaults)

    # 5) Remove obvious outliers
    # Option A: hard bounds
    df = remove_outliers_bounds(df, "price", 0, 10000)
    df = remove_outliers_bounds(df, "availability_365", 0, 365)

    # Option B (alternative): quantile-based trims for heavy-tailed cols
    # df = remove_outliers_quantile(df, "price", 0.01, 0.99)

    # 6) Sanity checks (skip for columns not present)
    sanity_checks(df)

    # 7) Save
    try:
        df.to_parquet(OUT_PARQUET_PATH, index=False)
        print(f"[save] Cleaned data saved to {OUT_PARQUET_PATH}")
    except Exception as e:
        out_csv = OUT_PARQUET_PATH.replace(".parquet", ".csv")
        print(f"[warn] parquet failed ({e}); saving CSV -> {out_csv}")
        df.to_csv(out_csv, index=False)

    # Peek
    print(df.info())
    print(df.head(3))

if __name__ == "__main__":
    main()
