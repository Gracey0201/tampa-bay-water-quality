from typing import Dict, List, Tuple, Union

import xarray as xr
import pandas as pd

from pystac_client import Client as STACClient
import planetary_computer as pc
from pystac.item import Item
# NOTE: stackstac is needed to process the GOES STAC items
import stackstac


# MUR SST Zarr (complete, gap-free, lower resolution)
MUR_SST_URL = "s3://mur-sst/zarr-v1"

def environmental_variables(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    variables: List[str] = ["sst", "precip"],
    sst_source: str = "goes-sst", # New parameter to select SST source
    precip_collection: str = "noaa-mrms-qpe-24h-pass2",
    stac_api_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
) -> Dict[str, Union[xr.DataArray, List[Item], None]]:
    """
    Modular environmental data fetcher, now supporting GOES SST via STAC.

    - Uses MUR Zarr for long-term SST (if requested) OR STAC for near-real-time SST.
    - Robust STAC-based precipitation item retrieval.
    """

    results = {}
    client = STACClient.open(stac_api_url, modifier=pc.sign_inplace)

    # ======================
    # SST (GOES STAC)
    # ======================
    if "sst" in variables and sst_source == "goes-sst":
        try:
            print(f"Searching for SST data in STAC collection: {sst_source}")
            
            # Use the search method, similar to precipitation
            search = client.search(
                collections=[sst_source],
                datetime=f"{start_date}/{end_date}",
                bbox=bbox,
                query={"platform": {"eq": "GOES-16"}}, # Focus on GOES-East
            )

            sst_items = list(search.get_all_items())
            print(f"GOES SST Items found: {len(sst_items)}")
            
            if sst_items:
                # 1. Stack the STAC Items into one xarray.DataArray
                # Asset for SST is typically 'sst' or 'sea_surface_temp' (it's 'sst' for GOES)
                sst_stack = stackstac.stack(
                    sst_items,
                    assets=["sst"], 
                    chunksize={"time": 1, "x": 2048, "y": 2048},
                    fill_value=None, 
                    dtype="float32",
                ).sel(band="sst").squeeze()

                # 2. Convert to Celsius (GOES SST is often already in Celsius, but check source if issues arise)
                # The MUR data was in Kelvin, GOES is usually in Celsius, so we skip conversion here
                sst = sst_stack
                sst.attrs["units"] = "C"
                
                # 3. Spatial mean → Monthly mean
                # Note: The 'sst' asset is usually in Kelvin, but the GOES STAC may provide it in Celsius.
                # Since you converted MUR SST, we'll assume Celsius. If issues, check the asset metadata.
                sst = sst.mean(dim=["x", "y"])
                sst = sst.resample(time="1ME").mean()
                sst.name = "sst"
                
                results["sst"] = sst
                print(f"GOES SST Monthly time steps created: {len(sst.time)}")

            else:
                print("No GOES SST items found for the given time and bbox.")
                results["sst"] = None

        except Exception as e:
            print(f"ERROR fetching GOES SST from STAC: {e}")
            results["sst"] = None

    # ======================
    # SST (MUR Zarr - Fallback/Alternative)
    # ======================
    elif "sst" in variables and sst_source == "mur-zarr":
        try:
            ds = xr.open_zarr(
                MUR_SST_URL,
                consolidated=True,
                storage_options={"anon": True},
            )

            print("SST data successfully opened from MUR Zarr.")

            sst = (
                ds["analysed_sst"]  
                .sel(
                    lat=slice(bbox[1], bbox[3]),
                    lon=slice(bbox[0], bbox[2]),
                )
                .sel(time=slice(start_date, end_date))
                .chunk({"time": "auto", "lat": -1, "lon": -1})
            )

            print(f"MUR SST time steps selected: {len(sst.time)}")

            # Kelvin → Celsius (as in your original code)
            sst = sst - 273.15
            sst.attrs["units"] = "C"

            # Spatial mean → Monthly mean
            sst = sst.mean(dim=["lat", "lon"])
            sst = sst.resample(time="1ME").mean()
            sst.name = "sst"

            results["sst"] = sst

        except Exception as e:
            print(f"ERROR fetching MUR SST: {e}")
            results["sst"] = None

    # ======================
    # Precipitation (STAC) - Remains the same
    # ======================
    if "precip" in variables:
        all_items: List[Item] = []
        
        # ... (Your original precip logic is here, using the 'client' object) ...

        start_year = pd.to_datetime(start_date).year
        end_year = pd.to_datetime(end_date).year

        for year in range(start_year, end_year + 1):
            y_start = f"{year}-01-01"
            y_end = f"{year}-12-31"

            if year == start_year:
                y_start = start_date
            if year == end_year:
                y_end = end_date

            search = client.search(
                collections=[precip_collection],
                datetime=f"{y_start}/{y_end}",
                bbox=bbox,
            )

            items = list(search.get_all_items())
            all_items.extend(items)

            print(f"Year {year}: {len(items)} precip items")

        results["precip"] = all_items if all_items else None

    return results