import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA

def workflow_analysis(wqi_data: xr.DataArray, env_data: pd.DataFrame, variable_name: str):
    """
    Wrapper function to perform complete temporal, correlation, and PCA analysis.

    Steps:
    1. Compute monthly and seasonal means
    2. Plot time series
    3. Plot seasonal cycle
    4. Compute correlation matrix
    5. Compute PCA

    Parameters
    ----------
    wqi_data : xr.DataArray
        Water quality index time series
    env_data : pd.DataFrame
        Environmental variables (SST, Precipitation)
    variable_name : str
        Name of the WQI variable
    """
    print("Computing monthly and seasonal means...")
    means = compute_monthly_seasonal_means(wqi_data)

    print("Plotting time series...")
    plot_time_series(wqi_data, variable_name)

    print("Plotting seasonal cycle...")
    plot_seasonal_cycle(wqi_data, variable_name)

    print("Computing correlation matrix...")
    # Convert wqi_data to DataFrame
    wqi_df = wqi_data.to_dataframe(name=variable_name).reset_index().pivot(index='time', columns='variable', values=variable_name)
    corr = compute_correlation_matrix(wqi_df, env_data)
    print("Correlation Matrix:\n", corr)

    print("Computing PCA...")
    pca_results = compute_pca(wqi_df, env_data)
    plot_pca_results(pca_results['loadings'])

    return {
        'monthly_seasonal_means': means,
        'correlation_matrix': corr,
        'pca_results': pca_results
    }