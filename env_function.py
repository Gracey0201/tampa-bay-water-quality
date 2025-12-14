from typing import Dict, List, Tuple, Union
import xarray as xr
import pandas as pd
from pystac_client import Client as STACClient
import planetary_computer as pc
from pystac.item import Item

# Define the comprehensive MUR SST URL globally
MUR_SST_URL = "s3://mur-sst/zarr-v1"

def environmental_variables(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    variables: List[str] = ["sst", "precip"],
    # Original SST URL is kept as default, but logic will fall back to MUR if needed.
    sst_zarr_url: str = "s3://surftemp-sst/data/sst.zarr",  
    precip_collection: str = "noaa-mrms-qpe-24h-pass2",
    stac_api_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
) -> Dict[str, Union[xr.DataArray, List[Item], None]]:
    """
    Modular environmental data fetcher for SST and Precipitation with SST fallback logic.
    
    Includes fixes for:
    1. Truncated SST data (by falling back to MUR).
    2. Cloud credential errors (by using storage_options={"anon": True}).
    3. MUR variable name error (by using 'analysed_sst' for both sources).
    4. FIX: Universal Kelvin to Celsius conversion (Fixes the SST = 300 K issue).
    """

    results = {}
    
    # We check if the data goes up to the requested end date.
    target_end_dt = pd.to_datetime(end_date)
    
    # ======================
    # SST (Zarr) - Fully Modular and Adaptive with Fallback
    # ======================
    if "sst" in variables:
        # Use a list of URLs to try, starting with the provided one and falling back to MUR
        urls_to_try = [sst_zarr_url, MUR_SST_URL]
        
        for url in urls_to_try:
            try:
                is_mur_data = "mur-sst" in url.lower()
                
                # FIX 1: Set SST variable name uniformly to 'analysed_sst'
                sst_var_name = "analysed_sst" 

                # 1. Open Zarr store - FIX 2: Added storage_options={"anon": True}
                ds = xr.open_zarr(
                    pc.sign(url),
                    consolidated=True,
                    storage_options={"anon": True}
                )
                
                # 2. Check Truncation (if using the primary URL and it doesn't cover the time range)
                last_dt_in_data = ds.time.max().values
                if not is_mur_data and pd.to_datetime(last_dt_in_data) < target_end_dt:
                    print(f"SST data from {url} is truncated (stops at {last_dt_in_data}). Trying fallback...")
                    continue # Skip the rest of this try block and move to the next URL (MUR)
                
                print(f"SST data successfully fetched from: {url}")

                # 3. Apply spatial and temporal slicing
                sst = (
                    ds[sst_var_name]
                    .sel(
                        time=slice(start_date, end_date),
                        lat=slice(bbox[1], bbox[3]),
                        lon=slice(bbox[0], bbox[2])
                    )
                    .chunk({"time": "auto", "lat": -1, "lon": -1})
                )

                # 4. Apply Kelvin conversion (FIX 4: Now applied universally)
                print("Applying Kelvin to Celsius conversion.")
                sst = sst - 273.15
                sst.attrs["units"] = "C"
                    
                # 5. Final aggregation logic
                sst = sst.mean(dim=["lat", "lon"])
                sst = sst.resample(time="1ME").mean()
                sst.name = "sst"

                results["sst"] = sst
                break # Success! Exit the loop

            except Exception as e:
                print(f"Error processing SST from {url}: {e}")
                
        if "sst" not in results:
            print("ERROR: Could not fetch SST from any available source.")
            results["sst"] = None

    # ======================
    # Precipitation (STAC) - Robust Item Retrieval 
    # ======================
    if "precip" in variables:
        all_items: List[Item] = []

        client = STACClient.open(
            stac_api_url,
            modifier=pc.sign_inplace
        )

        # Loop through years to guarantee finding all items (pagination safety)
        for year in range(
            pd.to_datetime(start_date).year,
            pd.to_datetime(end_date).year + 1
        ):
            y_start = f"{year}-01-01"
            y_end = f"{year}-12-31"

            if year == pd.to_datetime(start_date).year:
                y_start = start_date
            if year == pd.to_datetime(end_date).year:
                y_end = end_date

            search = client.search(
                collections=[precip_collection],
                datetime=f"{y_start}/{y_end}",
                bbox=bbox,
            )

            # search.get_all_items() handles the pagination logic
            all_items.extend(list(search.get_all_items()))

        results["precip"] = all_items if all_items else None

    return results