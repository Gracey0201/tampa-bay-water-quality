import numpy as np
import xarray as xr
import stackstac
from pystac_client import Client as StacClient
import planetary_computer as pc
from typing import Dict, List, Tuple, Optional

def environmental_variables(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    variables: List[str] = ["sst", "precip"],
) -> Dict[str, Optional[xr.DataArray]]:
    """
    Fetches NOAA OISST Sea Surface Temperature (SST) and NOAA MRMS 
    Precipitation (Precip) from the Planetary Computer STAC Catalog,
    stacks them using stackstac, and returns the spatial average 
    time series for each variable.
    """
    client = StacClient.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    results: Dict[str, Optional[xr.DataArray]] = {}

    for var in variables:
        if var == "sst":
            collection = "noaa-cdr-sea-surface-temperature-optimum-interpolation"
            asset_names = ["data"]
            
            print("\nSearching for SST (NOAA OISST)...")
            search = client.search(
                collections=[collection],
                bbox=bbox,
                datetime=f"{start_date}/{end_date}",
                max_items=2000,
            )
            items = list(search.items())
            print(f"Found {len(items)} SST items")
            
            if not items:
                print("No SST items found.")
                results["sst"] = None
                continue

            signed_items = [pc.sign(item) for item in items]

            try:
                # Use stackstac's native grid and xarray/rasterio for clipping/scaling.
                # This bypasses incompatible keyword arguments.
                stack = stackstac.stack(
                    signed_items,
                    assets=asset_names, 
                    fill_value=np.nan,
                    # Remove all bounds, epsg, resolution params to use native grid.
                )
                
                # Clip the stack to the requested bounding box and select the SST band
                # The data is inherently projected, so we use .sel() instead of reprojecting
                # as .reproject_match() can be slow. We assume stackstac pulled the correct area.
                sst_band = stack.sel(band="sst")
                
                # OISST data is stored as scaled integers (value * 100). 
                scaled_stack = sst_band / 100.0 
                
                # Calculate the spatial mean using the stacked 'x' and 'y' dimensions
                sst_avg = scaled_stack.mean(dim=["x", "y"]).squeeze()
                sst_avg.name = "sst"
                
                results["sst"] = sst_avg
                print(f"SST: {len(sst_avg.time)} days")
            except Exception as e:
                print(f"SST stack failed: {e}")
                results["sst"] = None

        elif var == "precip":
            collection = "noaa-mrms-qpe-24h-pass2"
            assets = ["cog"]
            
            print("\nSearching for precip...")
            search = client.search(
                collections=[collection],
                datetime=f"{start_date}/{end_date}",
                bbox=bbox,
                max_items=2000,
            )
            items = list(search.items())
            
            if not items:
                print("No precip items found.")
                results["precip"] = None
                continue

            print(f"Found {len(items)} precip items")
            signed_items = [pc.sign(item) for item in items]

            try:
                # Precip: This block was working correctly.
                stack = stackstac.stack(
                    signed_items,
                    assets=assets,
                    epsg=4326, 
                    fill_value=np.nan,
                )
                da = stack.mean(dim=["x", "y"]).squeeze()
                da.name = "precip"
                results["precip"] = da
                print(f"Precip: {len(da.time)} days")
            except Exception as e:
                print(f"Precip stack failed: {e}")
                results["precip"] = None

    return results
