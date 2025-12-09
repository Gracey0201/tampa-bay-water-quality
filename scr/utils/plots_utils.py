import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
#import seaborn as sns
from sklearn.decomposition import PCA


def plot_indices_analysis(indices_dict, smooth_window=7):
    """
    Plot smoothed time series and seasonal cycle for all water quality indices (NDWI, NDTI, NDCI).

    Parameters:
        indices_dict : dict
            Dictionary returned by wqi()['indices']
            Must contain 'NDWI', 'NDTI', 'NDCI' with 'time_series' keys
        smooth_window : int
            Rolling window size in days for smoothing the time series (default=7)
    """
    indices = ["NDWI", "NDTI", "NDCI"]

    for index in indices:
        ts = indices_dict[index]["time_series"]
        df = ts.to_dataframe(name="value").reset_index()
        df["month"] = df["time"].dt.month

        # Apply rolling mean to smooth the time series
        df["value_smooth"] = df["value"].rolling(window=smooth_window, center=True).mean()

        # Seasonal cycle: monthly average from raw values
        monthly_avg = df.groupby("month")["value"].mean()

        # Create a figure with 2 subplots: time series and seasonal cycle
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Smoothed time series
        axes[0].plot(df["time"], df["value_smooth"], color="tab:blue")
        axes[0].set_title(f"{index} Smoothed Time Series ({smooth_window}-day rolling)")
        axes[0].set_xlabel("Date")
        axes[0].set_ylabel("Index Value")
        axes[0].grid(True)

        # Seasonal cycle
        axes[1].plot(monthly_avg.index, monthly_avg.values, marker="o", color="tab:orange")
        axes[1].set_title(f"{index} Seasonal Cycle")
        axes[1].set_xlabel("Month")
        axes[1].set_ylabel("Average Index Value")
        axes[1].set_xticks(range(1, 13))
        axes[1].grid(True)

        plt.tight_layout()
        plt.show()
