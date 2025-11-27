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
            stac_url = "https://cmr.earthdata.nasa.gov/stac/LANCEMODIS"
            collection = "MODIS_Aqua_L3SM_SST"
            assets = ["sst"]
            res = 4000  # 4 km
        elif var == "precipitation":
            stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
            collection = "GPM_3IMERG"
            assets = ["precipitation"]
            res = 10000  # 10 km
        else:
            raise ValueError(f"Variable {var} not supported.")
        
        epsg = 32617  # Tampa Bay UTM zone 17N
        
        # Connect to STAC
        client = StacClient.open(stac_url)
        items = client.search(
            collections=[collection],
            bbox=bbox,
            datetime=f"{start_date}/{end_date}",
            max_items=500
        ).item_collection()
        
        if len(items) == 0:
            print(f"No items found for {var}.")
            stacks[var] = None
            continue
        
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
s[var] = stack.mean(dim=["x", "y"])  # average over spatial domain
    
    return stacks
