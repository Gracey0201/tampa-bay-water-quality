### Task 1 - Develop Function(s) to Plot NDWI Time Series

## import libraries
import json
from shapely.geometry import shape
import numpy as np
import pandas as pd
import xarray as xr
from dask.distributed import Client, LocalCluster
from pystac_client import Client as StacClient
import stackstac
import matplotlib.pyplot as plt

def main(
    bbox: tuple,
    start_date: str,
    end_date: str,
    filter_clouds: bool = True,
) -> None:

    """
Generate a time series plot of NDWI from Sentinel-2 data within a specified bounding box and date range.

Args:
    bbox (tuple): Coordinates as (minx, miny, maxx, maxy).
    start_date (str): Start of analysis period, 'YYYY-MM-DD'.
    end_date (str): End of analysis period, 'YYYY-MM-DD'.
    filter_clouds (bool): Remove cloudy pixels if True using the SCL band.

Returns:
    None. Produces a plot of NDWI over time.
   """


    ## Query STAC API for Sentinel-2 images within the bbox and date range
    def search_stac_items(
        bbox: tuple,
        start_date: str,
        end_date: str,
    ) -> list:
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

    def stack_and_clip(
        items: list,
        assets: list,
        bbox: tuple,
    ) -> xr.DataArray:
        stack = stackstac.stack(
            items,
            assets=assets,
            bounds_latlon=bbox,
            epsg=32618,
            chunksize=4096,
            rescale=False,
            fill_value=np.float32(np.nan),  # fix for can_cast issue
        )
        return stack


    ## Calculate mean NDWI from xarray stack
    def calculate_mean_ndwi(
        stack: xr.DataArray,
        filter_clouds: bool,
    ) -> xr.DataArray:
        ## Calculate NDWI = (green - nir) / (green + nir)
        green = stack.sel(band="green")
        nir = stack.sel(band="nir")
        ndwi = (green - nir) / (green + nir)

        if filter_clouds:
            ## Filter cloudy pixels using SCL bands
            scl = stack.sel(band="scl")
            valid_mask = ~scl.isin([3, 8, 9, 10])
            ndwi = ndwi.where(valid_mask)

        mean_ndwi = ndwi.mean(dim=["x", "y"])
        return mean_ndwi

    ## Plot NDWI time series
    def plot_ndwi_time_series(mean_ndwi: xr.DataArray) -> None:
        # Ensure the DataArray has a name for the NDWI values
        mean_ndwi.name = "ndwi"

        ## Convert xarray DataArray to pandas DataFrame for better handling
        df = mean_ndwi.to_dataframe().reset_index()

        ## Validate the DataFrame structure
        if "ndwi" not in df.columns or "time" not in df.columns:
            raise KeyError("Expected columns 'ndwi' and 'time' in the DataFrame.")

        ## Generate the plot
        plt.figure(figsize=(12, 6))
        plt.plot(df["time"], df["ndwi"], marker="o", linestyle="--", color="blue", label="Mean NDWI")

        ## Add grid, labels, title and legend
        plt.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)
        plt.xlabel("Time", fontsize=12)
        plt.ylabel("Mean NDWI", fontsize=12)
        plt.title("NDWI Time Series", fontsize=14, fontweight="bold")

        plt.legend(loc="upper right", fontsize=10)

        ## Customize ticks
        plt.xticks(rotation=45, fontsize=10)
        plt.yticks(fontsize=10)

        ## Display plots
        plt.tight_layout()
        plt.show()

    ## Steps to run pipeline
    items = search_stac_items(bbox, start_date, end_date)
    print(f"Number of Sentinel-2 scenes processed: {len(items)}")
    
    if not items:
        print("No items found for given parameters.")
        return

    assets = ["green", "nir", "scl"]
    stack = stack_and_clip(items, assets, bbox)
    mean_ndwi = calculate_mean_ndwi(stack, filter_clouds)
    plot_ndwi_time_series(mean_ndwi)
