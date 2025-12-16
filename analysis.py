# kalu_analysis.py

import xarray as xr
import pandas as pd
import numpy as np
from typing import Dict

from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

from env_function import environmental_variables  # your function
from grace_functions import compute_indices       # Grace's indices


def load_env_timeseries(
    bbox,
    start_date: str,
    end_date: str,
) -> xr.DataArray:
    """
    Wrapper to get monthly SST over the bbox and period.
    Returns an xr.DataArray with dimension 'time'.
    """
    env_data = environmental_variables(
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        variables=["sst"],  # precip may be None due to API limits
    )

    sst_da = env_data.get("sst", None)
    if sst_da is None:
        raise ValueError("SST data could not be retrieved.")

    return sst_da


def join_indices_and_env(
    indices_ds: xr.Dataset,
    sst_da: xr.DataArray,
) -> pd.DataFrame:
    """
    Join Grace's monthly water-quality indices (NDWI, NDTI, NDCI)
    with Kalu's SST time series into a single pandas DataFrame.
    Assumes both share a 'time' coordinate.
    """
    # Convert to DataFrame
    idx_df = indices_ds.to_dataframe().reset_index()  # columns: time, NDWI, NDTI, NDCI ...
    sst_df = sst_da.to_series().reset_index()
    sst_df = sst_df.rename(columns={sst_da.name: "sst_c"})

    # Merge on time
    df = pd.merge(idx_df, sst_df, on="time", how="inner").sort_values("time")
    return df


def compute_correlations_and_rmse(df: pd.DataFrame) -> Dict[str, float]:
    """
    Compute Pearson correlations and RMSE between indices and SST.
    Expects columns: 'NDTI', 'NDCI', 'sst_c' in df.
    Returns a dict of stats you can print or write to CSV.
    """
    stats: Dict[str, float] = {}

    # Drop rows with any NaNs in the variables of interest
    sub = df[["NDTI", "NDCI", "sst_c"]].dropna()
    if len(sub) == 0:
        return stats

    # Pearson correlations
    stats["corr_NDTI_SST"] = sub["NDTI"].corr(sub["sst_c"])
    stats["corr_NDCI_SST"] = sub["NDCI"].corr(sub["sst_c"])

    # RMSE on standardized variables (puts them on similar scales)
    for col in ["NDTI", "NDCI", "sst_c"]:
        sub[col + "_z"] = (sub[col] - sub[col].mean()) / sub[col].std()

    stats["rmse_NDTI_SST_z"] = np.sqrt(((sub["NDTI_z"] - sub["sst_c_z"]) ** 2).mean())
    stats["rmse_NDCI_SST_z"] = np.sqrt(((sub["NDCI_z"] - sub["sst_c_z"]) ** 2).mean())

    return stats


def add_season_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'season' column based on month."""
    season_map = {
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring",
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Fall", 10: "Fall", 11: "Fall",
    }
    df = df.copy()
    df["season"] = df["time"].dt.month.map(season_map)
    return df


def seasonal_means(df: pd.DataFrame) -> pd.DataFrame:
    """Compute seasonal means for indices and SST."""
    df_season = add_season_column(df)
    return (
        df_season
        .groupby("season")[["NDWI", "NDTI", "NDCI", "sst_c"]]
        .mean()
        .reindex(["Winter", "Spring", "Summer", "Fall"])
    )


def run_pca(df: pd.DataFrame, n_components: int = 2) -> Dict[str, np.ndarray]:
    """
    Run PCA on standardized variables (NDWI, NDTI, NDCI, SST).
    Returns loadings and explained variance.
    """
    sub = df[["NDWI", "NDTI", "NDCI", "sst_c"]].dropna()
    if len(sub) == 0:
        return {}

    # Standardize
    X = (sub - sub.mean()) / sub.std()

    pca = PCA(n_components=n_components)
    pcs = pca.fit_transform(X)

    return {
        "loadings": pca.components_,          # shape (n_components, 4)
        "explained_variance": pca.explained_variance_ratio_,
        "variables": ["NDWI", "NDTI", "NDCI", "sst_c"],
        "pcs": pcs,
    }


def plot_monthly_timeseries(df: pd.DataFrame) -> None:
    """Simple monthly time-series plot of indices and SST."""
    fig, ax1 = plt.subplots(figsize=(10, 5))

    ax1.plot(df["time"], df["NDTI"], label="NDTI", color="tab:orange")
    ax1.plot(df["time"], df["NDCI"], label="NDCI", color="tab:green")
    ax1.set_ylabel("Index value")
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(df["time"], df["sst_c"], label="SST (°C)", color="tab:red")
    ax2.set_ylabel("SST (°C)", color="tab:red")
    ax2.tick_params(axis="y", labelcolor="tab:red")

    ax1.set_xlabel("Time")
    ax1.set_title("Monthly NDWI/NDTI/NDCI and SST – Tampa Bay")
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.show()
