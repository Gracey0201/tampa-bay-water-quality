import numpy as np
import xarray as xr
import fsspec 
import s3fs 
from pystac_client import Client
import planetary_computer as pc
import stackstac
from typing import Dict, List, Tuple, Optional
import pandas as pd

# AWS S3 Path for ESA CCI SST Daily Analysis (Cloud-optimized Zarr store)
AWS_SST_ZARR_URL = "s3://surftemp-sst/data/sst.zarr"


def environmental_variables(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    variables: List[str] = ["sst", "precip"],
    # --- MODULAR FIX: New optional argument for the item limit! ---
    max_items: int = 500  # Default value, but can be overridden in the notebook
) -> Dict[str, Optional[xr.DataArray]]:
    """
    Fetches Sea Surface Temperature (SST) from AWS S3 (Zarr) and Total Precipitation 
    (precip) from the Planetary Computer (STAC).
    
    The Precipitation search is capped by the 'max_items' argument for stability.
    """
    results: Dict[str, Optional[xr.DataArray]] = {}
    
    # Use the passed argument for the item limit
    MAX_STAC_ITEMS = max_items
    
    # --------------------------------------------------------------
    # 1. SST FROM AWS S3 ZARR (DASK-OPTIMIZED)
    # --------------------------------------------------------------
    if "sst" in variables:
        print(f"\nAccessing SST Zarr store on AWS S3: {AWS_SST_ZARR_URL}")
        
        try:
            # Open the Zarr store lazily (Dask array created implicitly)
            ds = xr.open_zarr(
                AWS_SST_ZARR_URL,
                storage_options={"anon": True}
            )
            
            lat_slice = slice(bbox[1], bbox[3]) 
            lon_slice = slice(bbox[0], bbox[2])
            
            # Select the subset and variable lazily
            sst_data = ds["analysed_sst"].sel(
                time=slice(start_date, end_date), 
                lat=lat_slice, 
                lon=lon_slice
            ).chunk({'time': 'auto', 'lat': -1, 'lon': -1}) 
            
            # Convert Kelvin to Celsius and calculate the daily spatial mean
            sst_c = sst_data - 273.15
            sst_avg_daily = sst_c.mean(dim=["lat", "lon"])
            
            # Resample to monthly mean, then compute and load
            sst_monthly_mean = sst_avg_daily.resample(time="1ME").mean()
            
            results["sst"] = sst_monthly_mean.compute() 
            results["sst"].name = "sst"
            print(f"✔ SST months loaded: {results['sst'].time.size}")

        except Exception as e:
            print(f"SST Zarr access failed. Error: {e}")
            results["sst"] = None

    # --------------------------------------------------------------
    # 2. PRECIP (Daily NOAA MRMS from Planetary Computer STAC) - MODULAR LIMIT
    # --------------------------------------------------------------
    if "precip" in variables:
        print(f"\nFetching Precipitation (NOAA MRMS QPE 24h) via Batched STAC Search (Strict Limit: {MAX_STAC_ITEMS} items)...")
        all_items = []
        total_items_found = 0
        
        start_year = pd.to_datetime(start_date).year
        end_year = pd.to_datetime(end_date).year
        
        try:
            client = Client.open(
                "https://planetarycomputer.microsoft.com/api/stac/v1",
                modifier=pc.sign_inplace
            )
            
            # --- LOOPING THROUGH YEARS FOR STABILITY (2019 to 2024) ---
            for year in range(start_year, end_year + 1):
                year_start = f"{year}-01-01"
                year_end = f"{year}-12-31"
                
                if year == start_year: year_start = start_date
                if year == end_year: year_end = end_date
                
                # Check if the limit has been reached before starting the search
                if total_items_found >= MAX_STAC_ITEMS:
                    print("  Strict item limit reached. Skipping remaining years.")
                    break 

                # Request up to the API limit (1000) for this year's search
                items_to_request = 1000

                search = client.search(
                    collections=["noaa-mrms-qpe-24h-pass2"],
                    datetime=f"{year_start}/{year_end}",
                    bbox=bbox,
                    limit=items_to_request
                )
                
                yearly_items = list(search.items())
                
                # --- Manually enforce the modular item limit ---
                remaining_slots = MAX_STAC_ITEMS - total_items_found
                items_to_add = yearly_items[:remaining_slots] 

                all_items.extend(items_to_add)
                total_items_found += len(items_to_add)
                
                print(f"  Found {len(yearly_items)} items for {year}. Added {len(items_to_add)}. Total: {total_items_found}")

            print(f"Total precip items used for computation: {total_items_found}")
            
            if total_items_found == 0:
                results["precip"] = None
            else:
                # Stack all daily items (Dask array created here)
                precip_stack = stackstac.stack(
                    all_items,
                    assets=["cog"],
                    epsg=4326,
                    fill_value=np.nan
                )
                
                precip_mean_daily = precip_stack.mean(dim=["x", "y"]).squeeze(drop=True)
                precip_mean_daily.name = "precip"

                if "time" in precip_mean_daily.dims:
                    precip_mean_daily = precip_mean_daily.dropna("time", how="all")
                
                # Resample daily precipitation to monthly SUM
                precip_monthly_sum = precip_mean_daily.resample(time="1ME").sum(min_count=1)
                
                # Trigger computation
                results["precip"] = precip_monthly_sum.compute()
                
                print(f"✔ Precip loaded: {results['precip'].time.size} months")

        except Exception as e:
            print(f" Precip load failed: {e}")
            results["precip"] = None
    
    # --------------------------------------------------------------
    # 3. Align and Merge for final output 
    # --------------------------------------------------------------
    if results.get("sst") is not None and results.get("precip") is not None:
        print("\nAligning and merging datasets...")
        
        # This will align SST and Precip on the limited time dimension of the Precipitation data
        aligned_sst, aligned_precip = xr.align(results["sst"], results["precip"], join="inner")
        
        merged_ds = xr.Dataset({"sst": aligned_sst, "precip": aligned_precip})
        
        results["sst"] = merged_ds["sst"]
        results["precip"] = merged_ds["precip"]
        print(f"✔ Merged months: {merged_ds.time.size}")
    
    return results