import json
from shapely.geometry import shape
import numpy as np
import pandas as pd
import xarray as xr
from dask.distributed import Client, LocalCluster
from pystac_client import Client as StacClient
import stackstac
import matplotlib.pyplot as plt

def wqi_indices(
    bbox: tuple,
    start_date: str,
    end_date: str,
    filter_clouds: bool = True,
    max_items: int = 2,
    downsample_factor: int = 10
):
    """
    This function compute RGB quicklook and mean NDWI, NDTI, NDCI with chunked/persisted Dask arrays
    to reduce memory pressure and avoid kernel crashes.
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

    # --- Step 2: Stack and clip ---
    print("Stacking and clipping data...")
    assets = ["blue", "green", "red", "nir", "scl", "rededge3"]
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

    # --- Step 3: RGB quicklook with downsampling ---
    print("\nGenerating RGB Quicklook (Median Composite)...")
    try:
        # Compute median and coarsen first
        r = stack.sel(band="red").median(dim="time", skipna=True).coarsen(
            x=downsample_factor, y=downsample_factor, boundary='trim'
        ).mean()
        g = stack.sel(band="green").median(dim="time", skipna=True).coarsen(
            x=downsample_factor, y=downsample_factor, boundary='trim'
        ).mean()
        b = stack.sel(band="blue").median(dim="time", skipna=True).coarsen(
            x=downsample_factor, y=downsample_factor, boundary='trim'
        ).mean()

        # Normalize
        def normalize(arr):
            arr_min = arr.min().compute()
            arr_max = arr.max().compute()
            return ((arr - arr_min) / (arr_max - arr_min + 1e-6)).compute()

        rgb = np.dstack([
            normalize(r),
            normalize(g),
            normalize(b)
        ])

        rgb = np.nan_to_num(rgb, nan=0.0)

        plt.figure(figsize=(8, 8))
        plt.imshow(rgb)
        plt.title("Sentinel-2 RGB Median Composite", fontsize=14)
        plt.axis("off")
        plt.show()

    except Exception as e:
        print("RGB quicklook failed:", e)

    # --- Step 4: Function to compute mean indices safely ---
    def calculate_mean_index(stack, index_name):
        print(f" - Calculating {index_name}...")
        if index_name == "NDWI":
            band1 = stack.sel(band="green")
            band2 = stack.sel(band="nir")
        elif index_name == "NDTI":
            band1 = stack.sel(band="red")
            band2 = stack.sel(band="green")
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

        index = index.persist()  # keep in memory in chunks
        mean_index = index.mean(dim=["x", "y"]).compute()  # compute chunked mean
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

    # --- Step 6: Compute indices ---
    results = {}
    for index_name in ["NDWI", "NDTI", "NDCI"]:
        mean_index = calculate_mean_index(stack, index_name)
        mean_index.name = index_name.lower()
        plot_index_time_series(mean_index, index_name)
        results[index_name] = mean_index

    print(" - Cleaning up memory...")
    del stack, rgb
    return results
