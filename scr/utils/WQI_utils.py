import numpy as np
import pandas as pd
import warnings
from pystac_client import Client as StacClient
import stackstac
import calendar
import xarray as xr

TAMPA_BAY = (-82.7167, 27.5833, -82.3833, 28.0333)

def normalized_diff(b1, b2):
    """Compute normalized difference (b1-b2)/(b1+b2)."""
    return (b1 - b2) / (b1 + b2 + 1e-10)

def compute_wqi_indices(
    bbox=TAMPA_BAY,
    start_date="2019-01-01",
    end_date="2024-12-31",
    max_items=500,
    epsg=32617,
    filter_clouds=True,
    max_cloud_cover=20.0,  
    export_csv=False,
    output_path="wqi_results.csv",
    anomaly_detection=False,
    rolling_window=3,
    diagnostics=True
):
    """
    Compute NDWI, NDTI, NDCI with full diagnostics for professor review.
    """

    client = StacClient.open("https://earth-search.aws.element84.com/v1")
    search = client.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        max_items=max_items
    )
    items = search.item_collection()

    if not items:
        print("No scenes found.")
        return None, None, None, None

    # CLOUD FILTER (before stacking!)
    if filter_clouds:
        original_count = len(items)
        items = [item for item in items if item.properties.get('eo:cloud_cover', 100) < max_cloud_cover]
        print(f"Cloud filtered: {original_count} → {len(items)} scenes (<{max_cloud_cover}% cloud cover)")

    if not items:
        print("No low-cloud scenes found.")
        return None, None, None, None

    # FULL DIAGNOSTICS FOR FIRST 5 SCENES
    if diagnostics:
        print("\n=== FULL DATA QUALITY DIAGNOSTICS (First 5 Scenes) ===")
        print("="*80)

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

    # DIAGNOSTIC LOOP
    for i, item in enumerate(items[:5]):
        if diagnostics:
            dt = pd.to_datetime(item.properties["datetime"], utc=True).tz_localize(None)
            print(f"\nSCENE {i+1}: {dt.date()} | ID: {item.id[:8]}...")
            
            # THUMBNAIL
            thumb_url = 'No thumbnail'
            if 'thumbnail' in item.assets:
                thumb_asset = item.assets['thumbnail']
                if hasattr(thumb_asset, 'href'):
                    thumb_url = thumb_asset.href
            print(f"Thumbnail: {thumb_url}")
            
            # CLOUD METADATA
            cloud_pct = item.properties.get('eo:cloud_cover', 'N/A')
            print(f"Cloud cover (metadata): {cloud_pct}%")
            
            # SCL ANALYSIS
            try:
                scene = stack.sel(time=dt, method="nearest")
                if "scl" in scene.band.values:
                    scl = scene.sel(band="scl").compute()
                    cloud_pixels = ((scl == 3) | (scl == 8) | (scl == 9) | (scl == 10)).sum().item()
                    water_pixels = (scl == 6).sum().item()
                    total_valid = np.isfinite(scl).sum().item()
                    
                    cloud_ratio = cloud_pixels / total_valid if total_valid > 0 else 0
                    water_ratio = water_pixels / total_valid if total_valid > 0 else 0
                    
                    print(f"SCL breakdown: Clouds={cloud_ratio:.1%} | Water={water_ratio:.1%} | Valid={total_valid:,}px")
                else:
                    print("No SCL band available")
            except Exception as e:
                print(f"SCL analysis failed: {e}")
            
            # NDWI SANITY CHECK
            try:
                green = scene.sel(band="green").mean().compute()
                nir = scene.sel(band="nir").mean().compute()
                raw_ndwi = (green - nir) / (green + nir + 1e-10)
                print(f"Raw NDWI: {raw_ndwi:.3f} | Green: {green:.3f} | NIR: {nir:.3f}")
                
                if raw_ndwi > 0.1:
                    print("ALERT: Positive NDWI → Likely land/cloud contamination!")
                elif raw_ndwi < -0.5:
                    print("CLEAN water signal")
                    
            except Exception as e:
                print(f"NDWI check failed: {e}")
            
            print("-" * 80)

    print("\nDiagnostics complete. Computing indices...\n")

    # MAIN PROCESSING (lazy)
    green = stack.sel(band="green")
    red = stack.sel(band="red")
    nir = stack.sel(band="nir")
    rededge1 = stack.sel(band="rededge1")

    ndwi = normalized_diff(green, nir)
    ndti = normalized_diff(red, green)
    ndci = normalized_diff(rededge1, red)

    # STRENGTHENED WATER MASK
    if filter_clouds and "scl" in stack.band.values:
        scl = stack.sel(band="scl")
        water_mask = (scl == 6) | (scl == 5)
        ndwi = ndwi.where(water_mask)
        ndti = ndti.where(water_mask)
        ndci = ndci.where(water_mask)

    # Clean NaNs
    ndwi = ndwi.where(np.isfinite(ndwi))
    ndti = ndti.where(np.isfinite(ndti))
    ndci = ndci.where(np.isfinite(ndci))

    # 1D TIME SERIES
    ndwi_mean_t = ndwi.mean(dim=("x", "y"))
    ndwi_med_t = ndwi.median(dim=("x", "y"))
    ndti_mean_t = ndti.mean(dim=("x", "y"))
    ndti_med_t = ndti.median(dim=("x", "y"))
    ndci_mean_t = ndci.mean(dim=("x", "y"))
    ndci_med_t = ndci.median(dim=("x", "y"))

    ds_ts = xr.Dataset({
        "ndwi_mean": ndwi_mean_t, "ndwi_median": ndwi_med_t,
        "ndti_mean": ndti_mean_t, "ndti_median": ndti_med_t,
        "ndci_mean": ndci_mean_t, "ndci_median": ndci_med_t,
    })

    ds_ts = ds_ts.compute()

# Time conversion
    df_results = ds_ts.to_dataframe().reset_index()
    df_results["time"] = pd.to_datetime(df_results["time"], utc=True).dt.tz_localize(None)
    df_results = df_results.rename(columns={"time": "date"})
    df_results.set_index("date", inplace=True)
    df_results.sort_index(inplace=True)

# DROP NON-NUMERIC COLUMNS (including scene IDs!)
    wqi_cols = [col for col in df_results.columns if col.startswith(('ndwi', 'ndti', 'ndci'))]
    df_results = df_results[wqi_cols]  # KEEP ONLY WQI columns
    df_results = df_results.astype(float)  # Now safe

    print("Shape:", df_results.shape)
    print("Columns:", df_results.columns.tolist())

    # FORCE NUMERIC DTYPE FOR WQI COLUMNS
    wqi_cols = [col for col in df_results.columns if col.startswith(('ndwi_', 'ndti_', 'ndci_'))]
    df_results[wqi_cols] = df_results[wqi_cols].astype(float)

    print("Shape:", df_results.shape)

    # Rolling + monthly
    df_rolling = df_results.rolling(window=rolling_window, min_periods=1).mean()
    
    if not df_results.empty:
        df_results["month"] = df_results.index.month
        monthly_cols = [col for col in df_results.columns if col.startswith(('ndwi', 'ndti', 'ndci'))]
        monthly_avg = df_results.groupby("month")[monthly_cols].mean()
        monthly_avg.index = [calendar.month_name[m] for m in monthly_avg.index]
    else:
        monthly_avg = pd.DataFrame()

    if anomaly_detection and not df_results.empty:
        for col in ["ndwi_mean", "ndti_mean", "ndci_mean"]:
            if col in df_results.columns:
                z = (df_results[col] - df_results[col].mean()) / df_results[col].std()
                df_results[f"{col}_zscore"] = z
                df_results[f"{col}_anomaly"] = z.abs() > 3

    if export_csv and not df_results.empty:
        df_results.to_csv(output_path)
        print(f"WQI statistics exported to {output_path}")

    print(f"Analysis complete: {len(df_results)} scenes processed")
    if not df_results.empty:
        print(f"NDWI range: {df_results['ndwi_mean'].min():.3f} to {df_results['ndwi_mean'].max():.3f}")
        if df_results['ndwi_mean'].max() > 0.1:
            print("WARNING: Positive NDWI detected - check diagnostics!")

    return df_results, df_rolling, monthly_avg
