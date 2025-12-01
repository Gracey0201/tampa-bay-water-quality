import stackstac
import xarray as xr
from pystac_client import Client
from typing import Dict

def environmental_variables(
    bbox: tuple,
    start_year: int,
    end_year: int,
    variables: list = ["sst", "precipitation"]
) -> Dict[str, xr.DataArray]:
    """
    Retrieve and process environmental variables (SST, Precipitation)
    over a bounding box and time range.

    Returns:
        dict: Keys are variable names, values are xarray.DataArray of mean values over time.
    """
    
    min_lon, min_lat, max_lon, max_lat = bbox
    stacks = {}

    for var in variables:
        if var == "sst":
            stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
            collection = "noaa-cdr-sea-surface-temperature-whoi"
            assets = ["analysed_sst"]
            resolution = 0.25  # degrees (~28 km)
        elif var == "precipitation":
            stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
            collection = "gpm-3imerg"
            assets = ["precipitation"]
            resolution = 0.1  # degrees (~11 km)
        else:
            raise ValueError(f"Variable {var} not supported.")

        # Connect to STAC
        client = Client.open(stac_url)
        items = []

        # Fetch items year by year to avoid server limits
        for year in range(start_year, end_year + 1):
            search = client.search(
                collections=[collection],
                bbox=bbox,
                datetime=f"{year}-01-01/{year}-12-31",
                max_items=100  # safe limit per year
            )
            items.extend(list(search.get_items()))

        if len(items) == 0:
            print(f"No items found for {var}.")
            stacks[var] = None
            continue

        # Stack into xarray
        stack = stackstac.stack(
            items,
            assets=assets,
            bounds_latlon=bbox,
            resolution=resolution,
            epsg=4326,  # geographic coordinates
            chunksize=256,
            rescale=False,
            fill_value=float("nan"),
            errors_as_nodata=True  # instead of assert
        )

        # Compute spatial mean
        stacks[var] = stack.mean(dim=["x", "y"])
        print(f"{var}: {len(stack.time)} time steps loaded.")

    return stacks
