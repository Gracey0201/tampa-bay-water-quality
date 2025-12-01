import xarray as xr
import matplotlib.pyplot as plt
#import seaborn as sns
import numpy as np
import geopandas as gpd
from rasterio import features

def spatial_workflow(stack_dict: dict, boundary: gpd.GeoDataFrame, thresholds: dict):
    """
    Wrapper function to run the spatial workflow:
    Clip WQI stacks to boundary
    Plot heatmaps
    Generate composite risk map

    Parameters
    ----------
    stack_dict : dict
        Dictionary of xarray.DataArrays
    boundary : gpd.GeoDataFrame
        Polygon boundary
    thresholds : dict
        Thresholds for risk map

    Returns
    -------
    dict
        - 'clipped_stacks': dictionary of clipped stacks
        - 'composite_risk': composite risk map
    """
    clipped_stacks = {}
    
    # Clip and plot heatmaps
    for name, stack in stack_dict.items():
        clipped = clip_to_boundary(stack, boundary)
        clipped_stacks[name] = clipped
        plot_heatmap(clipped, title=f"{name} Heatmap")
    
    # Generate composite risk map
    composite_risk = create_composite_risk_map(clipped_stacks, thresholds)
    
    return {'clipped_stacks': clipped_stacks, 'composite_risk': composite_risk}
