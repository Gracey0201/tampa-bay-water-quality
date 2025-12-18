import numpy as np
import stackstac
from pystac_client import Client as StacClient

def load_wqi_stack(
    bbox,
    start_date,
    end_date,
    epsg=32617,
    max_items=100,
    filter_clouds=True,
    max_cloud_cover=20
):
    """
    Load a Sentinel-2 stack for WQI calculation from STAC.

    Parameters
    ----------
    bbox : tuple
        Bounding box for spatial subsetting (minx, miny, maxx, maxy).
    start_date : str
        Start date in "YYYY-MM-DD" format.
    end_date : str
        End date in "YYYY-MM-DD" format.
    epsg : int, default 32617
        EPSG code for the output projection.
    max_items : int, default 100
        Maximum number of items to retrieve from the STAC search.
    filter_clouds : bool, default True
        If True, filter images with cloud cover above max_cloud_cover.
    max_cloud_cover : float, default 20
        Maximum cloud cover (%) allowed if filter_clouds is True.

    Returns
    -------
    xarray.Dataset
        Dask-backed stack of Sentinel-2 bands ('green', 'red', 'nir', 'rededge1', 'scl') ready for WQI processing.
    """
    client = StacClient.open("https://earth-search.aws.element84.com/v1")
    search = client.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        max_items=max_items
    )

    items = search.item_collection()

    if filter_clouds:
        items = [
            i for i in items
            if i.properties.get("eo:cloud_cover", 100) < max_cloud_cover
        ]

    stack = stackstac.stack(
        items,
        assets=["green", "red", "nir", "rededge1", "scl"],
        bounds_latlon=bbox,
        epsg=epsg,
        chunksize=(1, 1, -1, "auto"),
        dtype="float32",
        fill_value=np.float32(np.nan),
        rescale=False
    )
    print("Stack loaded with shape:", stack.shape)
    return stack
