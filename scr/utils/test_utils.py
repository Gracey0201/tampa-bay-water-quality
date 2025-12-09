import json
from shapely.geometry import shape
import numpy as np
import pandas as pd
import xarray as xr
from dask.distributed import Client, LocalCluster
from pystac_client import Client as StacClient
import stackstac
import matplotlib.pyplot as plt
import requests
from PIL import Image
import io

def wqi_indices(
    bbox: tuple,
    start_date: str,
    end_date: str,
    filter_clouds: bool = True,
    max_items: int = 2,
    downsample_factor: int = 10
):
    """
    Compute NDWI, NDTI, NDCI time series and generate a quick thumbnail visualization.
    Uses Dask for chunked processing to reduce memory pressure.
    """
    # --- Step 1: Search STAC items ---
    print("Searching STAC items...")
    client = StacClient.open("https://earth-search.aws.element84.com/v1")
    items = client.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        max_items=max_items
    ).item_collection()
    print(f" - Found {len(items)} items")
    if not items:
        print("No Sentinel-2 scenes found.")
        return None

    # --- Step 2: Stack georeferenced bands ---
    assets = ["nir", "scl", "rededge3"]  # exclude thumbnail
    stack = stackstac.stack(
        items,
        assets=assets,
        bounds_latlon=bbox,
        epsg=32618,
        chunksize=(1, 1, -1, "auto"),
        rescale=False,
        fill_value=np.float32(np.nan),
    )
    print(" - Stack created")

    # --- Step 3: Quicklook using thumbnail ---
    print("\nGenerating Quicklook (thumbnail)...")
    thumb_url = None
    for item in items:
        if "thumbnail" in item.assets:
            thumb_url = item.assets["thumbnail"].href
            break

    if thumb_url:
        try:
            img_data = requests.get(thumb_url).content
            plt.figure(figsize=(8,8))
            plt.imshow(Image.open(io.BytesIO(img_data)))
            plt.title("Sentinel-2 Thumbnail Quicklook", fontsize=14)
            plt.axis("off")
            plt.show()
        except Exception as e:
            print("Thumbnail quicklook failed:", e)
    else:
        print("Thumbnail not available in any of the items. Falling back to RGB or skipping quicklook.")

    # --- Step 4: Compute mean indices safely ---
    def calculate_mean_index(stack, index_name):
        print(f" - Calculating {index_name}...")
        if index_name == "NDWI":
            band1 = stack.sel(band="green") if "green" in stack.band.values else stack.sel(band="nir")
            band2 = stack.sel(band="nir")
        elif index_name == "NDTI":
            band1 = stack.sel(band="red") if "red" in stack.band.values else stack.sel(band="nir")
            band2 = stack.sel(band="green") if "green" in stack.band.values else stack.sel(band="rededge3")
        elif index_name == "NDCI":
            band1 = stack.sel(band="rededge3")
            band2 = stack.sel(band="red")
        else:
            raise ValueError("Invalid index name")

        index = (band1 - band2) / (band1 + band2 + 1e-10)  # avoid divide by zero

        if filter_clouds and "scl" in stack.band.values:
            scl = stack.sel(band="scl")
            cloud_mask = ~scl.isin([3, 8, 9, 10])
            index = index.where(cloud_mask)

        index = index.persist()
        mean_index = index.mean(dim=["x", "y"]).compute()
        return mean_index

    # --- Step 5: Plotting function ---
    def plot_index_time_series(mean_index, index_name):
        print(f" - Plotting {index_name} time series...")
        df = mean_index.to_dataframe().reset_index()
        plt.figure(figsize=(12,6))
        plt.plot(df["time"], df[index_name.lower()], marker="o", linestyle="--", color="blue")
        plt.title(f"{index_name} Time Series", fontsize=14, fontweight="bold")
        plt.xlabel("Time")
        plt.ylabel(f"Mean {index_name}")
        plt.grid(alpha=0.4)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    # --- Step 6: Compute all indices ---
    results = {}
    for index_name in ["NDWI", "NDTI", "NDCI"]:
        mean_index = calculate_mean_index(stack, index_name)
        mean_index.name = index_name.lower()
        plot_index_time_series(mean_index, index_name)
        results[index_name] = mean_index

    print(" - Cleaning up memory...")
    del stack
    return results
