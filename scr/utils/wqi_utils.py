import numpy as np
import pandas as pd
import xarray as xr
from pystac_client import Client as StacClient
import stackstac
import matplotlib.pyplot as plt

def qwi(
    bbox: tuple,
    start_date: str,
    end_date: str,
    filter_clouds: bool = True,
) -> None:
    """
    Generate a time series plot of NDWI, NDTI, and NDCI from Sentinel-2 data within a specified bounding box and date range.

    Args:
        bbox (tuple): Coordinates as (minx, miny, maxx, maxy).
        start_date (str): Start of analysis period, 'YYYY-MM-DD'.
        end_date (str): End of analysis period, 'YYYY-MM-DD'.
        filter_clouds (bool): Remove cloudy pixels if True using the SCL band.

    Returns:
        None. Produces a plot of NDWI, NDTI, and NDCI over time.
    """

    ## Query STAC API for Sentinel-2 images within the bbox and date range
    def search_stac_items(bbox: tuple, start_date: str, end_date: str) -> list:
        api_url = "https://earth-search.aws.element84.com/v1"
        client = StacClient.open(api_url)
        items = client.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date}/{end_date}",
            max_items=500,
        ).item_collection()
        return items

    ## Stack chosen STAC assets into xarray and clip to the bounding box
    def stack_and_clip(items: list, assets: list, bbox: tuple) -> xr.DataArray:
        stack = stackstac.stack(
            items,
            assets=assets,
            bounds_latlon=bbox,
            epsg=32618,
            chunksize=4096,
            rescale=False,
            fill_value=np.float32(np.nan),
        )
        return stack

    ## Calculate mean NDWI, NDTI, NDCI from xarray stack
    def calculate_indices(stack: xr.DataArray, filter_clouds: bool) -> dict:
        green = stack.sel(band="green")
        red = stack.sel(band="red")
        nir = stack.sel(band="nir")

        ndwi = (green - nir) / (green + nir)
        ndti = (red - green) / (red + green)
        
        # NDCI only if rededge5 exists
        if "rededge5" in stack.band.values:
            rededge5 = stack.sel(band="rededge5")
            ndci = (rededge5 - red) / (rededge5 + red)
        else:
            print("rededge5 not available; skipping NDCI")
            ndci = None

        if filter_clouds:
            scl = stack.sel(band="scl")
            valid_mask = ~scl.isin([3, 8, 9, 10])
            ndwi = ndwi.where(valid_mask)
            ndti = ndti.where(valid_mask)
            if ndci is not None:
                ndci = ndci.where(valid_mask)

        return {
            "NDWI": ndwi.mean(dim=["x", "y"]),
            "NDTI": ndti.mean(dim=["x", "y"]),
            "NDCI": ndci.mean(dim=["x", "y"]) if ndci is not None else None,
        }

    ## Plot NDWI, NDTI, NDCI time series
    def plot_indices(indices: dict) -> None:
        plt.figure(figsize=(12, 6))
        for key, da in indices.items():
            if da is not None:
                da.name = key.lower()
                df = da.to_dataframe().reset_index()
                plt.plot(df["time"], df[da.name], marker="o", linestyle="--", label=key)
        plt.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)
        plt.xlabel("Time", fontsize=12)
        plt.ylabel("Mean Index Value", fontsize=12)
        plt.title("NDWI, NDTI, NDCI Time Series", fontsize=14, fontweight="bold")
        plt.xticks(rotation=45, fontsize=10)
        plt.yticks(fontsize=10)
        plt.legend(loc="upper right", fontsize=10)
        plt.tight_layout()
        plt.show()

    ## Run pipeline
    items = search_stac_items(bbox, start_date, end_date)
    print(f"Number of Sentinel-2 scenes processed: {len(items)}")

    if not items:
        print("No items found for given parameters.")
        return

    assets = ["green", "red", "rededge5", "nir", "scl"]
    stack = stack_and_clip(items, assets, bbox)
    indices = calculate_indices(stack, filter_clouds)
    plot_indices(indices)
