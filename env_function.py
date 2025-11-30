import numpy as np
import xarray as xr
from pystac_client import Client as StacClient
import stackstac
from typing import Dict

def environmental_variables(
    bbox: tuple,
    start_date: str,
    end_date: str,
    variables: list = ["sst", "precipitation"]
) -> Dict[str, xr.DataArray]:
    """
    Retrieve and process environmental variables (SST, Precipitation)
    over a bounding box and time range.

    Returns:
        dict: Keys are variable names, values are xarray.DataArray of mean values over time.
    """
    
    stacks = {}
    
    for var in variables:
        if var == "sst":
            collection = "noaa-cdr-sea-surface-temperature-optimum-interpolation"
            assets = ["sst"]
            res = 25000  # 25km

        elif var == "precipitation":
            collection = "noaa-mrms-qpe-1h-pass2"  #  738 items!
            assets = ["precipitation"]
            res = 1000   # 1km radar
            
        else:
            raise ValueError(f"Variable {var} not supported.")
        
        stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
        epsg = 32617  # Tampa Bay UTM zone 17N
        
        # Connect to STAC
        client = StacClient.open(stac_url)
        items = client.search(
            collections=[collection],
            bbox=bbox,
            datetime=f"{start_date}/{end_date}",
            max_items=5000  # Increased for hourly MRMS
        ).item_collection()
        
        if len(items) == 0:
            print(f"No items found for {var}.")
            stacks[var] = None
            continue
        
        print(f"Found {len(items)} items for {var}")
        
        # Stack into xarray
        stack = stackstac.stack(
            items,
            assets=assets,
            bounds_latlon=bbox,
            epsg=epsg,
            resolution=res,
            chunksize=4096,
            rescale=False,
            fill_value=np.nan
        )
        
        # Compute spatial mean
        stacks[var] = stack.mean(dim=["x", "y"])
    
    return stacks
