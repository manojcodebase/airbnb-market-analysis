import os
import pandas as pd
import matplotlib.pyplot as plt

CLEAN = os.getenv("OUT_PARQUET_PATH", "data/clean_airbnb_listings.parquet")
FIG_DIR = "notebooks/figures"
OUT_DIR = "data"

def ensure_dirs():
    os.makedirs(FIG_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

def load_clean() -> pd.DataFrame:
    try:
        df = pd.read_parquet(CLEAN)
        print(f"[load] {CLEAN} -> {df.shape}")
        return df
    except Exception as e:
        # Fallback to CSV with same basename
        csv_path = CLEAN.replace(".parquet", ".csv")
        print(f"[warn] parquet read failed ({e}); trying {csv_path}")
        df = pd.read_csv(csv_path, low_memory=False)
        print(f"[load] {csv_path} -> {df.shape}")
        return df

def kpis(df: pd.DataFrame):
    print("=== KPIs ===")
    print(f"Rows: {len(df):,} | Cols: {len(df.columns)}")
    if "price" in df.columns:
        print(f"Avg price: {df['price'].mean():.2f}")
        print(f"Median price: {df['price'].median():.2f}")
        print(f"P95 price: {df['price'].quantile(0.95):.2f}")
    if "room_type" in df.columns:
        print("\nRoom type counts:")
        print(df["room_type"].value_counts())

def avg_price_by_neighbourhood_group(df: pd.DataFrame) -> pd.Series:
    if {"neighbourhood_group","price"}.issubset(df.columns):
        g = (df.groupby("neighbourhood_group")["price"]
               .mean()
               .sort_values(ascending=False)
               .round(2))
        print("\nAverage price by neighbourhood group:\n", g)
        g.to_csv(os.path.join(OUT_DIR, "avg_price_by_group.csv"))
        return g
    return pd.Series(dtype=float)

def top_hosts(df: pd.DataFrame, n=10) -> pd.Series:
    need = {"host_id","host_name","id"}
    if need.issubset(df.columns):
        t = (df.groupby(["host_id","host_name"])["id"]
               .count()
               .sort_values(ascending=False)
               .head(n))
        print(f"\nTop {n} hosts by listing count:\n", t)
        t.to_csv(os.path.join(OUT_DIR, "top_hosts.csv"))
        return t
    return pd.Series(dtype=int)

def availability_stats(df: pd.DataFrame):
    if "availability_365" in df.columns:
        stats = df["availability_365"].describe()
        print("\nAvailability 365 describe:\n", stats)
        stats.to_csv(os.path.join(OUT_DIR, "availability_365_describe.csv"))
        return stats

def correlations(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["price","number_of_reviews","reviews_per_month","availability_365"] if c in df.columns]
    if cols:
        corr = df[cols].corr(numeric_only=True)
        print("\nCorrelation matrix:\n", corr)
        corr.to_csv(os.path.join(OUT_DIR, "correlations.csv"))
        return corr
    return pd.DataFrame()

def chart_price_hist(df: pd.DataFrame):
    if "price" in df.columns:
        plt.figure()
        df["price"].dropna().clip(upper=df["price"].quantile(0.99)).hist(bins=50)
        plt.title("Price Distribution (clipped at 99th percentile)")
        plt.xlabel("Price")
        plt.ylabel("Count")
        plt.tight_layout()
        out = os.path.join(FIG_DIR, "price_hist.png")
        plt.savefig(out)
        plt.close()
        print(f"[chart] {out}")

def chart_avg_price_by_group(series: pd.Series):
    if not series.empty:
        plt.figure()
        series.plot(kind="bar")
        plt.title("Average Price by Neighbourhood Group")
        plt.xlabel("Neighbourhood Group")
        plt.ylabel("Average Price")
        plt.tight_layout()
        out = os.path.join(FIG_DIR, "avg_price_by_group.png")
        plt.savefig(out)
        plt.close()
        print(f"[chart] {out}")

def chart_room_type_pie(df: pd.DataFrame):
    if "room_type" in df.columns:
        plt.figure()
        df["room_type"].value_counts().plot(kind="pie", autopct="%1.1f%%")
        plt.title("Room Type Distribution")
        plt.ylabel("")
        plt.tight_layout()
        out = os.path.join(FIG_DIR, "room_type_pie.png")
        plt.savefig(out)
        plt.close()
        print(f"[chart] {out}")

def chart_availability_hist(df: pd.DataFrame):
    if "availability_365" in df.columns:
        plt.figure()
        df["availability_365"].dropna().hist(bins=50)
        plt.title("Availability (365) Distribution")
        plt.xlabel("Days available")
        plt.ylabel("Count")
        plt.tight_layout()
        out = os.path.join(FIG_DIR, "availability_hist.png")
        plt.savefig(out)
        plt.close()
        print(f"[chart] {out}")

def chart_map_sample(df: pd.DataFrame, sample_n=5000):
    if {"lat","long","price"}.issubset(df.columns) and len(df) > 0:
        s = df.sample(min(sample_n, len(df)), random_state=42)
        plt.figure()
        plt.scatter(s["long"], s["lat"], s=6, alpha=0.4)
        plt.title("Listing Locations (sample)")
        plt.xlabel("Longitude")
        plt.ylabel("Latitude")
        plt.tight_layout()
        out = os.path.join(FIG_DIR, "map_scatter_sample.png")
        plt.savefig(out)
        plt.close()
        print(f"[chart] {out}")

def main():
    ensure_dirs()
    df = load_clean()
    kpis(df)
    avg_series = avg_price_by_neighbourhood_group(df)
    top_hosts(df, n=10)
    availability_stats(df)
    correlations(df)

    # Charts
    chart_price_hist(df)
    chart_avg_price_by_group(avg_series)
    chart_room_type_pie(df)
    chart_availability_hist(df)
    chart_map_sample(df)

    print(f"\n[done] Figures in {FIG_DIR} | CSV summaries in {OUT_DIR}")

if __name__ == "__main__":
    main()
