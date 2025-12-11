import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests
import io
import xarray as xr
from PIL import Image
from shapely.geometry import shape
import geopandas as gpd
from pystac_client import Client as StacClient
from dask.distributed import Client, LocalCluster
import stackstac

def wqi_indices(
    bbox,
    start_date,
    end_date,
    max_items=5,
    downsample_factor=1,
    filter_clouds=False
):
    """
    Compute water quality indices (NDWI, NDTI, NDCI) for Tampa Bay.
    Supports optional cloud masking using SCL.
    """

    # ----------------------------
    # STEP 1: SEARCH STAC
    # ----------------------------
    print("\nSearching Sentinel-2 scenes…")
    client = StacClient.open("https://earth-search.aws.element84.com/v1")

    items = client.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        max_items=max_items
    ).item_collection()

    print(f" - Found {len(items)} scenes")
    if not items:
        print("No scenes found.")
        return None

    # ----------------------------
    # STEP 2: PLOT FOOTPRINTS
    # ----------------------------
    footprints = []
    for item in items:
        geom = shape(item.geometry)
        footprints.append({"id": item.id, "geometry": geom})

    gdf = gpd.GeoDataFrame(footprints, crs="EPSG:4326")
    print("\nScene footprints:")
    print(gdf)

    # ----------------------------
    # STEP 3: DETECT OVERLAP AOI
    # ----------------------------
    overlap_area = None
    for i in range(len(gdf)):
        for j in range(i + 1, len(gdf)):
            inter = gdf.geometry[i].intersection(gdf.geometry[j])
            if inter.area > 0:
                overlap_area = inter
                break
        if overlap_area:
            break

    if overlap_area is None:
        print("No overlapping scenes detected — using full bbox as AOI.")
        aoi_bbox = bbox
    else:
        minx, miny, maxx, maxy = overlap_area.bounds
        aoi_bbox = (minx, miny, maxx, maxy)
        print("Overlap AOI bounding box:", aoi_bbox)

    # ----------------------------
    # STEP 4: STACK & MOSAIC
    # ----------------------------
    assets = ["green", "red", "nir", "rededge1", "scl"]
    stack = stackstac.stack(
        items,
        assets=assets,
        bounds_latlon=aoi_bbox,
        epsg=32617,
        chunksize=(1, 1, -1, "auto"),
        rescale=False,
        fill_value=np.float32(np.nan),
        dtype="float32",
    )

    mosaic = stack.median(dim="time").compute()

    # ----------------------------
    # STEP 5: CALCULATE INDICES
    # ----------------------------
    green = mosaic.sel(band="green")
    red = mosaic.sel(band="red")
    nir = mosaic.sel(band="nir")
    rededge1 = mosaic.sel(band="rededge1")

    ndwi = (green - nir) / (green + nir + 1e-10)
    ndti = (red - green) / (red + green + 1e-10)
    ndci = (rededge1 - red) / (rededge1 + red + 1e-10)

    # ----------------------------
    # STEP 6: CLOUD MASK (SCL)
    # ----------------------------
    if filter_clouds and "scl" in mosaic.band.values:
        scl = mosaic.sel(band="scl")
        cloud_mask = ~scl.isin([3, 8, 9, 10])  # 3=shadow, 8-10=clouds
        ndwi = ndwi.where(cloud_mask)
        ndti = ndti.where(cloud_mask)
        ndci = ndci.where(cloud_mask)

    # Mask NaN and negative values
    ndwi = ndwi.where(np.isfinite(ndwi) & (ndwi >= 0))
    ndti = ndti.where(np.isfinite(ndti) & (ndti >= 0))
    ndci = ndci.where(np.isfinite(ndci) & (ndci >= 0))

    # ----------------------------
    # STEP 7: VISUALIZE THUMBNAIL
    # ----------------------------
    thumb_url = None
    for item in items:
        if "thumbnail" in item.assets:
            thumb_url = item.assets["thumbnail"].href
            break

    if thumb_url:
        try:
            img_data = requests.get(thumb_url).content
            plt.figure(figsize=(6, 6))
            plt.imshow(Image.open(io.BytesIO(img_data)))
            plt.title("Sentinel-2 Thumbnail")
            plt.axis("off")
            plt.show()
        except:
            print("Could not load thumbnail.")

    # ----------------------------
    # STEP 8: VISUALIZE MOSAIC (NIR)
    # ----------------------------
    plt.figure(figsize=(6, 6))
    plt.imshow(nir, cmap="gray")
    plt.title("Mosaic Area (NIR Band)")
    plt.axis("off")
    plt.show()

    print("\nDone!")

    return {
        "ndwi": ndwi,
        "ndti": ndti,
        "ndci": ndci,
        "mosaic": mosaic,
        "aoi_bbox": aoi_bbox,
        "overlap_area": overlap_area
    }
