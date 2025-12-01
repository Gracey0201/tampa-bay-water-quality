import numpy as np
import xarray as xr
from pystac_client import Client as StacClient
import stackstac

# -------------------- Helper Functions --------------------
def search_stac_items(bbox, start_date, end_date, max_items):
    client = StacClient.open("https://earth-search.aws.element84.com/v1")
    search = client.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        max_items=max_items,
    )
    return search.item_collection()


def stack_assets(items, assets, bbox):
    """Stack Sentinel-2 assets using stackstac."""
    return stackstac.stack(
        items,
        assets=assets,
        bounds_latlon=bbox,
        epsg=32618,
        chunksize=(1, 1, -1, "auto"),
        rescale=False,
        fill_value=np.float32(np.nan),
    )


def mosaic_assets(stack):
    """
    Mosaic multiple scenes per day by averaging them.
    Does NOT reduce bands or spatial dimensions, only time.
    
    Parameters:
        stack : xarray DataArray or Dataset (stacked assets)
        
    Returns:
        xarray DataArray or Dataset with daily mosaics
    """
    # Floor time to daily
    stack['time'] = stack.time.dt.floor('D')

    # Average overlapping scenes per day (preserve x, y, band)
    stack_mosaic = stack.groupby('time').mean(dim='time', skipna=True)

    return stack_mosaic


def calc_indices(stack, filter_clouds=True):
    """Compute NDWI, NDTI, NDCI with cloud and NaN masking, returning both spatial maps and mean time series."""

    # Select bands
    green = stack.sel(band="green")
    red = stack.sel(band="red")
    nir = stack.sel(band="nir")
    rededge3 = stack.sel(band="rededge3")

    # Compute indices
    ndwi = (green - nir) / (green + nir)
    ndti = (red - green) / (red + green)
    ndci = (rededge3 - red) / (rededge3 + red)

    # Cloud mask
    if filter_clouds and "scl" in stack.band.values:
        scl = stack.sel(band="scl")
        mask = ~scl.isin([3, 8, 9, 10])  # 3=cloud shadow, 8-10=clouds
        ndwi = ndwi.where(mask)
        ndti = ndti.where(mask)
        ndci = ndci.where(mask)

    # Mask NaN and negative values
    ndwi = ndwi.where(np.isfinite(ndwi) & (ndwi >= 0))
    ndti = ndti.where(np.isfinite(ndti) & (ndti >= 0))
    ndci = ndci.where(np.isfinite(ndci) & (ndci >= 0))

    # Compute mean time series
    ndwi_ts = ndwi.mean(dim=["x", "y"])
    ndti_ts = ndti.mean(dim=["x", "y"])
    ndci_ts = ndci.mean(dim=["x", "y"])

    # Return dictionary containing both spatial maps and time series
    return {
        "NDWI": {"spatial": ndwi, "time_series": ndwi_ts},
        "NDTI": {"spatial": ndti, "time_series": ndti_ts},
        "NDCI": {"spatial": ndci, "time_series": ndci_ts},
    }


# -------------------- Main Function --------------------
def wqi(
    bbox: tuple,
    start_date: str,
    end_date: str,
    filter_clouds: bool = True,
    max_items: int = 500,
) -> dict:
    """Compute NDWI, NDTI, NDCI from Sentinel-2 with optional mosaicing."""

    # Search STAC items
    items = search_stac_items(bbox, start_date, end_date, max_items)
    print(f"Found {len(items)} Sentinel-2 scenes.")
    if not items:
        return None

    # Required bands
    assets = ["green", "red", "nir", "scl", "rededge3"]

    # Stack and mosaic
    stack = stack_assets(items, assets, bbox)
    stack_mosaic = mosaic_assets(stack)
    print("Stack mosaic shape:", stack_mosaic.shape)

    # Compute indices
    indices = calc_indices(stack_mosaic, filter_clouds=filter_clouds)

    return {"stack": stack_mosaic, "indices": indices}
