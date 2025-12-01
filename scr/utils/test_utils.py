import xarray as xr
import rioxarray
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import calendar

#-----------------------------------------------
def environmental_variables(bbox, start_year, end_year, variables=["sst","precipitation"]):
    """
    Retrieve environmental variables for a bounding box and year range.

    Returns a dictionary of xarray.DataArrays with time dimension (if available).
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    stacks = {}

    for var in variables:
        if var == "sst":
            # Example: NOAA OISST (daily)
            # In practice, loop over years
            url = f"https://www.ncei.noaa.gov/thredds/dodsC/OisstBase/NetCDF/AVHRR/{end_year}/avhrr-only-v2.{end_year}0101.nc"
            ds = xr.open_dataset(url)
            da = ds['sst'].sel(
                lon=slice(min_lon, max_lon),
                lat=slice(min_lat, max_lat)
            )
            # Spatial mean
            stacks[var] = da.mean(dim=['lat','lon'])

        elif var == "precipitation":
            # CHIRPS example (daily)
            url = f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/{end_year}/CHIRPS_daily_{end_year}0101.tif"
            da = rioxarray.open_rasterio(url)
            da = da.rio.clip_box(minx=min_lon, miny=min_lat, maxx=max_lon, maxy=max_lat)
            stacks[var] = da.mean(dim=['x','y'])

        else:
            raise ValueError(f"Variable {var} not supported.")

    return stacks

#-----------------------------------------------
def get_season(month):
    """Return season name given a month."""
    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    else:
        return 'Autumn'

#-----------------------------------------------
def compute_monthly_average(da):
    """Compute monthly average for xarray.DataArray with time dimension."""
    if 'time' not in da.dims:
        raise ValueError("DataArray has no time dimension")
    return da.resample(time='M').mean()

#-----------------------------------------------
def to_dataframe(da, var_name):
    """Convert xarray.DataArray to pandas DataFrame for plotting seasonal summaries."""
    if 'time' not in da.dims:
        # If no time, return single value DF
        return pd.DataFrame({var_name:[da.values]}, index=[0])
    df = da.to_dataframe(name=var_name).reset_index()
    df['Year'] = df['time'].dt.year
    df['Month'] = df['time'].dt.month
    df['Season'] = df['Month'].apply(get_season)
    return df

#-----------------------------------------------
def plot_variable_timeseries(df, var_name):
    """Plot a simple time series."""
    if 'time' not in df.columns:
        print(f"No time dimension for {var_name}. Value: {df[var_name].values}")
        return
    df.plot(x='time', y=var_name, figsize=(12,4))
    plt.title(f"{var_name} time series")
    plt.xlabel("Time")
    plt.ylabel(var_name)
    plt.show()

#-----------------------------------------------
def plot_variable_by_season(df, var_name, side_by_side=False):
    """
    Plot environmental variable aggregated by season.
    Similar style to MTBS burn area seasonal plots.
    """
    if df.empty:
        print("No data available.")
        return

    # Group by Year & Season
    season_summary = df.groupby(['Year','Season'])[var_name].mean().reset_index()
    pivot_df = season_summary.pivot(index='Year', columns='Season', values=var_name).fillna(0)

    plt.figure(figsize=(12,7))
    if side_by_side:
        pivot_df.plot(kind='bar', width=0.8)
        plt.title(f"{var_name} by Season (side-by-side)")
    else:
        pivot_df.plot(kind='bar', stacked=True)
        plt.title(f"{var_name} by Season (stacked)")

    plt.xlabel("Year")
    plt.ylabel(var_name)
    plt.legend(title="Season")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
