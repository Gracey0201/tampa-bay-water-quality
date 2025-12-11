import numpy as np
import pandas as pd
import warnings
from pystac_client import Client as StacClient
import stackstac
import calendar
import xarray as xr

# Tampa Bay extents (WGS84 lon/lat)
TBEP_BBOX = (-82.8, 27.5, -82.2, 28.1)
TBEP_TRIAL_BBOX = (-82.55, 27.75, -82.45, 27.85)

def normalized_diff(b1, b2):
    """Compute normalized difference (b1-b2)/(b1+b2)."""
    return (b1 - b2) / (b1 + b2 + 1e-10)

def compute_wqi_indices(
    bbox=TBEP_TRIAL_BBOX,
    start_date="2019-01-01",
    end_date="2024-12-31",
    max_items=500,
    epsg=32617,
    filter_clouds=True,
    export_csv=False,
    output_path="wqi_results.csv",
    anomaly_detection=False,
    rolling_window=3
):
    """
    Compute NDWI, NDTI, NDCI mean & median for a bounding box and date range.
    bbox must be (min_lon, min_lat, max_lon, max_lat) in WGS84.
    """

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

    assets = ["green", "red", "nir", "rededge1", "scl"]
    stack = stackstac.stack(
        items,
        assets=assets,
        bounds_latlon=bbox,  # geographic bbox
        epsg=epsg,           # output CRS (UTM 17N)
        chunksize=(1, 1, -1, "auto"),
        dtype="float32",
        fill_value=np.float32(np.nan),
        rescale=False
    )

    stats_list = []

    for item in items:
        dt = pd.to_datetime(item.properties["datetime"], utc=True).tz_localize(None)

        try:
            scene = stack.sel(time=dt)
        except KeyError:
            scene = stack.sel(time=dt, method="nearest")

        green = scene.sel(band="green")
        red = scene.sel(band="red")
        nir = scene.sel(band="nir")
        rededge1 = scene.sel(band="rededge1")

        ndwi = normalized_diff(green, nir)
        ndti = normalized_diff(red, green)
        ndci = normalized_diff(rededge1, red)

        # Cloud mask
        if filter_clouds and "scl" in scene.band.values:
            scl = scene.sel(band="scl")
            cloud_mask = ~scl.isin([3, 8, 9, 10])
            ndwi = ndwi.where(cloud_mask)
            ndti = ndti.where(cloud_mask)
            ndci = ndci.where(cloud_mask)

        # Only drop non-finite values
        ndwi = ndwi.where(np.isfinite(ndwi))
        ndti = ndti.where(np.isfinite(ndti))
        ndci = ndci.where(np.isfinite(ndci))

        try:
            # Compute once per index, then stats in memory
            idx_ds = xr.Dataset(
                {"ndwi": ndwi, "ndti": ndti, "ndci": ndci}
            ).compute()

            row = {"date": dt}
            for name in ["ndwi", "ndti", "ndci"]:
                arr = idx_ds[name]
                row[f"{name}_mean"] = float(arr.mean().item())
                row[f"{name}_median"] = float(arr.median().item())

        except Exception as e:
            warnings.warn(f"Reduction failed for {item.id} ({dt}): {e}")
            row = {"date": dt}
            for name in ["ndwi", "ndti", "ndci"]:
                row[f"{name}_mean"] = np.nan
                row[f"{name}_median"] = np.nan

        stats_list.append(row)

    df_results = pd.DataFrame(stats_list)
    df_results["date"] = pd.to_datetime(df_results["date"], utc=True)
    df_results.set_index("date", inplace=True)
    df_results.sort_index(inplace=True)

    df_rolling = df_results.rolling(window=rolling_window, min_periods=1).mean()

    if not df_results.empty:
        df_results["month"] = df_results.index.month
        monthly_avg = df_results.groupby("month")[
            [c for c in df_results.columns if c.startswith(("ndwi", "ndti", "ndci"))]
        ].mean()
        monthly_avg.index = [calendar.month_name[m] for m in monthly_avg.index]
    else:
        monthly_avg = pd.DataFrame()

    if anomaly_detection and not df_results.empty:
        for col in ["ndwi_mean", "ndti_mean", "ndci_mean"]:
            z = (df_results[col] - df_results[col].mean()) / df_results[col].std()
            df_results[f"{col}_zscore"] = z
            df_results[f"{col}_anomaly"] = z.abs() > 3

    if export_csv and not df_results.empty:
        df_results.to_csv(output_path)
        print(f"WQI statistics exported to {output_path}")

    return df_results, df_rolling, monthly_avg
