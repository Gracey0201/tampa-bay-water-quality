import numpy as np
import xarray as xr
from pystac_client import Client as StacClient
import stackstac

def wqi(
    bbox: tuple,
    start_date: str,
    end_date: str,
    filter_clouds: bool = True,
) -> dict:
    """
    Compute NDWI, NDTI, and NDCI time series from Sentinel-2 data.
    Fully lazy (Dask-friendly) and no plotting inside.
    """

    # -------------------- Query STAC API --------------------
    def search_stac_items(bbox, start_date, end_date):
        client = StacClient.open("https://earth-search.aws.element84.com/v1")
        search = client.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date}/{end_date}",
            max_items=20,
        )
        return search.item_collection()

    # -------------------- Stack STAC assets --------------------
    def stack_assets(items, assets, bbox):
        return stackstac.stack(
            items,
            assets=assets,
            bounds_latlon=bbox,
            epsg=32618,
            chunksize=256,
            rescale=False,
            fill_value=np.float32(np.nan),
        )

    # -------------------- Compute NDWI, NDTI, NDCI --------------------
    def calc_indices(stack, filter_clouds):

        green = stack.sel(band="green")
        red = stack.sel(band="red")
        nir = stack.sel(band="nir")
        rededge3 = stack.sel(band="rededge3")

        # Core formulas
        ndwi = (green - nir) / (green + nir)
        ndti = (red - green) / (red + green)
        ndci = (rededge3 - red) / (rededge3 + red)

        # Cloud mask (optional)
        if filter_clouds and "scl" in stack.band.values:
            scl = stack.sel(band="scl")
            mask = ~scl.isin([3, 8, 9, 10])   # cloud classes
            ndwi = ndwi.where(mask)
            ndti = ndti.where(mask)
            ndci = ndci.where(mask)

        # Return *lazy* time series (mean over space)
        return {
            "NDWI": ndwi.mean(dim=["x", "y"]),
            "NDTI": ndti.mean(dim=["x", "y"]),
            "NDCI": ndci.mean(dim=["x", "y"]),
        }

    items = search_stac_items(bbox, start_date, end_date)

    print(f"Found {len(items)} Sentinel-2 scenes.")

    if not items:
        return None

    # Sentinel-2 bands needed
    assets = ["green", "red", "nir", "scl", "rededge3"]

    # Lazy stacked DataArray
    stack = stack_assets(items, assets, bbox)

    print("Bands loaded:", list(stack.band.values))

    # Compute indices lazily
    indices = calc_indices(stack, filter_clouds)

    return {
        "stack": stack,       # full lazy cube
        "indices": indices    # dict of lazy DataArrays
    }
