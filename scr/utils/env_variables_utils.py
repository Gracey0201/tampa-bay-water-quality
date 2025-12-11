import numpy as np
import pandas as pd
import warnings
import calendar
from pystac_client import Client as StacClient
import stackstac

# --------------------------------
# Normalized difference helper
# --------------------------------
def normalized_diff(b1, b2):
    """Compute normalized difference (b1-b2)/(b1+b2). Works with Dask/xarray."""
    return (b1 - b2) / (b1 + b2 + 1e-10)

# --------------------------------
# compute_wqi_indices (safe)
# --------------------------------
def compute_wqi_indices(
    bbox,
    start_date,
    end_date,
    max_items=5,
    epsg=32617,
    filter_clouds=True,
    export_csv=False,
    output_path="wqi_results.csv",
    anomaly_detection=False,
    rolling_window=3
):
    """
    Compute WQI indices (NDWI, NDTI, NDCI) for a bounding box and date range.
    Returns:
        - df_results: raw indices per scene
        - df_rolling: rolling mean for smoothing
        - monthly_avg: seasonal cycle aggregated by month
    """
    # ----------------------------
    # STAC search
    # ----------------------------
    client = StacClient.open("https://earth-search.aws.element84.com/v1")
    items = client.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        max_items=max_items
    ).item_collection()

    if not items:
        print("No scenes found.")
        return None, None, None

    # ----------------------------
    # Lazy stack
    # ----------------------------
    assets = ["green", "red", "nir", "rededge1", "scl"]
    stack = stackstac.stack(
        items,
        assets=assets,
        bounds_latlon=bbox,
        epsg=epsg,
        chunksize=(1, 1, -1, "auto"),
        dtype="float32",
        fill_value=np.float32(np.nan),
        rescale=False
    )

    stats_list = []

    for item in items:
        # Parse scene datetime and remove timezone
        dt = pd.to_datetime(item.properties["datetime"], utc=True).tz_localize(None)

        # Select scene (lazy)
        try:
            scene = stack.sel(time=dt)
        except KeyError:
            scene = stack.sel(time=dt, method="nearest")

        # Extract bands
        green = scene.sel(band="green")
        red = scene.sel(band="red")
        nir = scene.sel(band="nir")
        rededge1 = scene.sel(band="rededge1")

        # Compute indices
        ndwi = normalized_diff(green, nir)
        ndti = normalized_diff(red, green)
        ndci = normalized_diff(rededge1, red)

        # Apply cloud mask if requested and SCL exists
        if filter_clouds and "scl" in scene.band.values:
            scl = scene.sel(band="scl")
            cloud_mask = ~scl.isin([3, 8, 9, 10])  # shadow + clouds
            ndwi = ndwi.where(cloud_mask)
            ndti = ndti.where(cloud_mask)
            ndci = ndci.where(cloud_mask)

        # Mask invalid values only (allow negative values)
        ndwi = ndwi.where(np.isfinite(ndwi))
        ndti = ndti.where(np.isfinite(ndti))
        ndci = ndci.where(np.isfinite(ndci))

        # Compute scalar reductions safely
        try:
            row = {
                "date": dt,
                "ndwi_mean": float(ndwi.mean().compute()),
                "ndwi_median": float(ndwi.median().compute()),
                "ndwi_max": float(ndwi.max().compute()),
                "ndwi_min": float(ndwi.min().compute()),
                "ndwi_std": float(ndwi.std().compute()),

                "ndti_mean": float(ndti.mean().compute()),
                "ndti_median": float(ndti.median().compute()),
                "ndti_max": float(ndti.max().compute()),
                "ndti_min": float(ndti.min().compute()),
                "ndti_std": float(ndti.std().compute()),

                "ndci_mean": float(ndci.mean().compute()),
                "ndci_median": float(ndci.median().compute()),
                "ndci_max": float(ndci.max().compute()),
                "ndci_min": float(ndci.min().compute()),
                "ndci_std": float(ndci.std().compute())
            }
        except Exception as e:
            warnings.warn(f"Reduction failed for {item.id} ({dt}): {e}")
            row = {"date": dt}
            for col in ["ndwi", "ndti", "ndci"]:
                for stat in ["mean", "median", "max", "min", "std"]:
                    row[f"{col}_{stat}"] = np.nan

        stats_list.append(row)

    # ----------------------------
    # Build DataFrame
    # ----------------------------
    df_results = pd.DataFrame(stats_list)
    df_results['date'] = pd.to_datetime(df_results['date'], utc=True)
    df_results.set_index('date', inplace=True)
    df_results.sort_index(inplace=True)

    # Rolling mean
    df_rolling = df_results.rolling(window=rolling_window, min_periods=1).mean()

    # Monthly seasonal cycle
    if not df_results.empty:
        df_results['month'] = df_results.index.month
        monthly_avg = df_results.groupby('month')[[c for c in df_results.columns if c.startswith(("ndwi","ndti","ndci"))]].mean()
        monthly_avg.index = [calendar.month_name[m] for m in monthly_avg.index]
    else:
        monthly_avg = pd.DataFrame()

    # Optional anomaly detection
    if anomaly_detection and not df_results.empty:
        for col in ["ndwi_mean", "ndti_mean", "ndci_mean"]:
            z = (df_results[col] - df_results[col].mean()) / df_results[col].std()
            df_results[f"{col}_zscore"] = z
            df_results[f"{col}_anomaly"] = z.abs() > 3

    # Optional CSV export
    if export_csv and not df_results.empty:
        df_results.to_csv(output_path)
        print(f"WQI statistics exported to {output_path}")

    return df_results, df_rolling, monthly_avg

