# env_utils.py
import xarray as xr
import matplotlib.pyplot as plt
import pooch
import os

# ---------------------------------------------------------
# 1. ENVIRONMENTAL DATASETS
# ---------------------------------------------------------
def environmental_variables():
    """Return dictionary describing SST and precipitation datasets."""
    return {
        "sst": {
            "name": "Sea Surface Temperature (GISTEMP/ERSSTv5)",
            "url": "https://data.giss.nasa.gov/pub/gistemp/gistemp1200_GHCNv4_ERSSTv5.nc.gz",
            "var": "tempanomaly",  # adjust to correct variable name in GISTEMP
        },
        "precipitation": {
            "name": "Monthly Precipitation (CMAP)",
            "url": "https://psl.noaa.gov/thredds/dodsC/Datasets/cmap/enh/cmap_enh.nc",
            "var": "precip",
        }
    }

# ---------------------------------------------------------
# 2. LOAD TIME SERIES
# ---------------------------------------------------------
def load_env_timeseries(bbox, variables=None, cache_dir="data"):
    """
    Load monthly mean environmental variable time series over a bounding box.

    Parameters:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        variables: list of strings ("sst", "precipitation") or None for both
        cache_dir: folder to store downloaded SST file

    Returns:
        dict of xarray DataArrays with spatial mean time series
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    env = environmental_variables()

    if variables is None:
        variables = list(env.keys())

    timeseries = {}

    for var in variables:
        if var == "sst":
            # Download and decompress SST using pooch
            os.makedirs(cache_dir, exist_ok=True)
            local_file = pooch.retrieve(
                env[var]["url"],
                processor=pooch.Decompress(),
                known_hash=None,
                path=cache_dir
            )
            ds = xr.open_dataset(local_file)
        else:
            # Precipitation loads from remote URL
            ds = xr.open_dataset(env[var]["url"])

        da = ds[env[var]["var"]].sel(
            lon=slice(min_lon, max_lon),
            lat=slice(min_lat, max_lat)
        )

        # Spatial mean over bounding box
        timeseries[var] = da.mean(dim=["lat", "lon"])

    return timeseries

# ---------------------------------------------------------
# 3. LOAD SEASONAL CYCLE
# ---------------------------------------------------------
def load_env_seasonal(bbox, variables=None):
    """
    Compute seasonal cycle (Winter/Spring/Summer/Fall) for SST & precipitation.
    """
    ts_dict = load_env_timeseries(bbox, variables)
    seasonal = {}
    for var, da in ts_dict.items():
        da = da.resample(time="M").mean()
        seasonal[var] = da.groupby("time.season").mean()
    return seasonal

# ---------------------------------------------------------
# 4. PLOTTING FUNCTIONS
# ---------------------------------------------------------
def plot_env_timeseries(timeseries_dict):
    """Plot monthly time series for SST and precipitation."""
    plt.figure(figsize=(12, 5))
    for var, da in timeseries_dict.items():
        plt.plot(da['time'], da, label=var.upper())
    plt.title("Environmental Variable Time Series")
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_env_seasonal(seasonal_dict):
    """Plot seasonal mean cycle (DJF, MAM, JJA, SON)."""
    plt.figure(figsize=(10, 5))
    for var, da in seasonal_dict.items():
        seasons = list(da['season'].values)
        values = da.values
        plt.plot(seasons, values, marker="o", label=var.upper())
    plt.title("Seasonal Climatology (DJF, MAM, JJA, SON)")
    plt.xlabel("Season")
    plt.ylabel("Mean Value")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()
