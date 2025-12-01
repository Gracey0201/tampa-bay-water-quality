import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
#import seaborn as sns
from sklearn.decomposition import PCA

# -------------------------------
# 1️⃣ Temporal Analysis Functions
# -------------------------------

def compute_monthly_seasonal_means(data: xr.DataArray) -> dict:
    """
    Compute monthly and seasonal averages for a DataArray.
    
    Parameters
    ----------
    data : xr.DataArray
        Time series data with 'time' dimension.
    
    Returns
    -------
    dict
        Dictionary with keys 'monthly', 'seasonal' containing aggregated DataArrays.
    """
    monthly = data.groupby('time.month').mean(dim='time')
    seasonal = data.groupby('time.season').mean(dim='time')
    return {'monthly': monthly, 'seasonal': seasonal}


def plot_time_series(data: xr.DataArray, variable_name: str):
    """
    Plot a time series for a given variable.
    
    Parameters
    ----------
    data : xr.DataArray
        Time series data
    variable_name : str
        Name of the variable for title/labeling
    """
    df = data.to_dataframe(name=variable_name).reset_index()
    plt.figure(figsize=(12, 6))
    plt.plot(df['time'], df[variable_name], marker='o', linestyle='-')
    plt.title(f"{variable_name} Time Series")
    plt.xlabel("Time")
    plt.ylabel(variable_name)
    plt.grid(True)
    plt.show()


def plot_seasonal_cycle(data: xr.DataArray, variable_name: str):
    """
    Plot seasonal averages for a variable.
    """
    seasonal_means = data.groupby('time.season').mean(dim='time')
    plt.figure(figsize=(8,5))
    seasonal_means.plot(marker='o', linestyle='--')
    plt.title(f"{variable_name} Seasonal Cycle")
    plt.show()


# -------------------------------
# 2️⃣ Correlation and Statistics
# -------------------------------

def compute_correlation_matrix(wqi_data: pd.DataFrame, env_data: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Pearson correlation between water quality indices and environmental variables.
    """
    combined = pd.concat([wqi_data, env_data], axis=1)
    return combined.corr()


def compute_rmse(predicted: np.ndarray, observed: np.ndarray) -> float:
    """
    Compute RMSE between predicted and observed arrays.
    """
    return np.sqrt(np.mean((observed - predicted)**2))


# -------------------------------
# 3️⃣ PCA Analysis
# -------------------------------

def compute_pca(wqi_data: pd.DataFrame, env_data: pd.DataFrame, n_components: int = 2) -> dict:
    """
    Compute PCA to identify co-variation between WQI and environmental variables.
    
    Returns dict with PCA model, scores, and loadings
    """
    combined = pd.concat([wqi_data, env_data], axis=1).dropna()
    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(combined)
    loadings = pd.DataFrame(
        pca.components_.T, 
        index=combined.columns, 
        columns=[f'PC{i+1}' for i in range(n_components)]
    )
    return {'model': pca, 'scores': scores, 'loadings': loadings}


def plot_pca_results(loadings: pd.DataFrame):
    """
    Plot PCA loadings for variables.
    """
    loadings.plot(kind='bar', figsize=(10,6))
    plt.title("PCA Loadings")
    plt.show()