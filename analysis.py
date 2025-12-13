import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# -------------------------------
# 1 Temporal Analysis Functions
# -------------------------------

def compute_monthly_seasonal_means(data: xr.DataArray) -> dict:
    """
    Compute monthly and seasonal averages for a DataArray.

    Returns
    -------
    dict
        {'monthly': calendar monthly means, 'seasonal': DJF/MAM/JJA/SON means}
    """
    monthly = data.resample(time="1M").mean()
    seasonal = data.groupby("time.season").mean()
    return {"monthly": monthly, "seasonal": seasonal}


def plot_time_series(data: xr.DataArray, variable_name: str):
    """Plot a time series for a given variable."""
    df = data.to_dataframe(name=variable_name).reset_index()
    plt.figure(figsize=(12, 4))
    plt.plot(df["time"], df[variable_name], marker="o", linestyle="-")
    plt.title(f"{variable_name} Time Series")
    plt.xlabel("Time")
    plt.ylabel(variable_name)
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_seasonal_cycle(data: xr.DataArray, variable_name: str):
    """Plot seasonal averages for a variable."""
    seasonal_means = data.groupby("time.season").mean()
    plt.figure(figsize=(6, 4))
    seasonal_means.plot(marker="o", linestyle="--")
    plt.title(f"{variable_name} Seasonal Cycle")
    plt.ylabel(variable_name)
    plt.tight_layout()
    plt.show()


# -------------------------------
# 2 Correlation and Statistics
# -------------------------------

def compute_correlation_matrix(wqi_data: pd.DataFrame,
                               env_data: pd.DataFrame) -> pd.DataFrame:
    """Compute Pearson correlations between WQI and environmental variables."""
    combined = pd.concat([wqi_data, env_data], axis=1)
    return combined.corr()


def compute_rmse(predicted: np.ndarray, observed: np.ndarray) -> float:
    """Compute RMSE between predicted and observed arrays."""
    return float(np.sqrt(np.mean((observed - predicted) ** 2)))


# -------------------------------
# 3 PCA Analysis
# -------------------------------

def compute_pca(wqi_data: pd.DataFrame,
                env_data: pd.DataFrame,
                n_components: int = 2) -> dict:
    """
    Compute PCA to identify co-variation between WQI and environmental variables.

    Returns
    -------
    dict with keys: 'model', 'scores', 'loadings'
    """
    combined = pd.concat([wqi_data, env_data], axis=1).dropna()
    scaler = StandardScaler()
    X_std = scaler.fit_transform(combined.values)

    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(X_std)

    loadings = pd.DataFrame(
        pca.components_.T,
        index=combined.columns,
        columns=[f"PC{i+1}" for i in range(n_components)],
    )
    return {"model": pca, "scores": scores, "loadings": loadings}


def plot_pca_results(loadings: pd.DataFrame):
    """Plot PCA loadings for variables."""
    plt.figure(figsize=(10, 4))
    loadings.plot(kind="bar")
    plt.title("PCA Loadings")
    plt.tight_layout()
    plt.show()
