import xarray as xr
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import geopandas as gpd
from rasterio import features

def clip_to_boundary(stack: xr.DataArray, boundary: gpd.GeoDataFrame) -> xr.DataArray:
    """
    Clip xarray DataArray to the provided boundary GeoDataFrame.

    Parameters
    ----------
    stack : xr.DataArray
        Raster data with 'x' and 'y' coordinates.
    boundary : gpd.GeoDataFrame
        Polygon boundary to clip the raster.

    Returns
    -------
    xr.DataArray
        Clipped raster data.
    """
    geom = [boundary.unary_union.__geo_interface__]
    mask = features.geometry_mask(
        geom,
        out_shape=(stack.sizes['y'], stack.sizes['x']),
        transform=stack.rio.transform(),
        invert=True
    )
    return stack.where(mask)


def plot_heatmap(stack: xr.DataArray, title: str):
    """
    Plot heatmap of mean values across space.
    """
    arr = stack.mean(dim='time')
    plt.figure(figsize=(10,6))
    sns.heatmap(arr.values, cmap='coolwarm')
    plt.title(title)
    plt.show()


def create_composite_risk_map(stack_dict: dict, thresholds: dict) -> xr.DataArray:
    """
    Create a composite risk map combining multiple WQI indices.

    Parameters
    ----------
    stack_dict : dict
        Dictionary of xarray.DataArrays, e.g., {'NDWI': stack1, 'NDCI': stack2, 'NDTI': stack3}
    thresholds : dict
        Dictionary with keys 'low', 'medium', 'high'

    Returns
    -------
    xr.DataArray
        Composite risk map
    """
    combined = sum([stack_dict[k].mean(dim='time') for k in stack_dict.keys()]) / len(stack_dict)
    risk = xr.full_like(combined, fill_value=0)
    risk = xr.where(combined < thresholds['low'], 1, risk)
    risk = xr.where((combined >= thresholds['low']) & (combined < thresholds['medium']), 2, risk)
    risk = xr.where(combined >= thresholds['medium'], 3, risk)
    
    plt.figure(figsize=(10,6))
    risk.plot(cmap='RdYlGn_r')
    plt.title("Composite Water Quality Risk Map (1=Low,3=High)")
    plt.show()
    
    return risk
s[0].coords,
        dims=agg_stacks[0].dims,
        name="composite_risk"
    )
