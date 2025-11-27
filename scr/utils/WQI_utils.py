import json
from shapely.geometry import shape
import numpy as np
import pandas as pd
import xarray as xr
from dask.distributed import Client, LocalCluster
from pystac_client import Client as StacClient
import stackstac
import matplotlib.pyplot as plt
from typing import Dict

def normalized_diff(b1, b2):
    """
    Compute normalized difference (b1 - b2) / (b1 + b2).
    """
    if b1.shape != b2.shape:
        raise ValueError("Input arrays must have the same shape.")
    return (b1 - b2) / (b1 + b2)

# -------------------------------
# WQI function for NDWI, NDTI, NDCI
# -------------------------------
def wqi(
    bbox: tuple,
    start_date: str,
    end_date: str,
    filter_clouds: bool = True,
) -> dict:
    """
    Compute mean NDWI, NDTI, and NDCI for a bounding box and date range.

    Parameters
    ----------
    bbox : tuple
        Bounding box coordinates (minx, miny, maxx, maxy)
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    filter_clouds : bool, optional
        Mask clouds using SCL band if True (default is True)

    Returns
    -------
    dict
        Dictionary with keys 'NDWI', 'NDTI', 'NDCI', each containing
        an xarray.DataArray of mean values over time
    """

    # ---- Search STAC
    api_url = "https://earth-search.aws.element84.com/v1"
    client = StacClient.open(api_url)
    items = client.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        max_items=500
    ).item_collection()

    if len(items) == 0:
        raise RuntimeError("No Sentinel-2 items found for given bbox/date.")

    # ---- Stack selected bands
    assets = ["B03", "B04", "B05", "B08", "SCL"]
    stack = stackstac.stack(
        items,
        assets=assets,
        bounds_latlon=bbox,
        epsg=32617,  # Tampa Bay
        resolution=10,
        chunksize=4096,
        rescale=False,
        fill_value=np.nan
    )

    # Rename bands for easier indexing
    band_map = {"B03":"green","B04":"red","B05":"rededge5","B08":"nir","SCL":"scl"}
    stack = stack.assign_coords(band=[band_map.get(b, b) for b in stack.band.values])

    # ---- Compute indices
    green = stack.sel(band="green")
    red = stack.sel(band="red")
    rededge5 = stack.sel(band="rededge5")
    nir = stack.sel(band="nir")
    scl = stack.sel(band="scl")

    if filter_clouds:
        valid_mask = ~scl.isin([3,8,9,10])
        green = green.where(valid_mask)
        red = red.where(valid_mask)
        rededge5 = rededge5.where(valid_mask)
        nir = nir.where(valid_mask)

    ndwi = normalized_diff(green, nir)
    ndti = normalized_diff(red, green)
    ndci = normalized_diff(rededge5, red)

    # ---- Take mean over spatial dimensions
    mean_ndwi = ndwi.mean(dim=["x","y"])
    mean_ndti = ndti.mean(dim=["x","y"])
    mean_ndci = ndci.mean(dim=["x","y"])

    # Return as dictionary
    return {"NDWI": mean_ndwi, "NDTI": mean_ndti, "NDCI": mean_ndci}
