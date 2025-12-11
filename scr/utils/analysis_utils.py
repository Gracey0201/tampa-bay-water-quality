import matplotlib.pyplot as plt
import pandas as pd

def plot_wqi_time_series(df_results, df_rolling=None, indices=["ndwi", "ndti", "ndci"], title="WQI Time Series"):
    """
    Plot WQI indices time series with rolling mean (mean & median).
    
    Parameters
    ----------
    df_results : pd.DataFrame
        Raw indices per scene (datetime index)
    df_rolling : pd.DataFrame or None
        Rolling mean time series (same columns as df_results)
    indices : list
        List of indices to plot
    title : str
        Plot title
    """
    plt.figure(figsize=(12,8))
    
    # plot raw mean & median
    for idx in indices:
        mean_col = f"{idx}_mean"
        med_col = f"{idx}_median"
        
        if mean_col in df_results.columns:
            plt.plot(df_results.index, df_results[mean_col], 
                    'o-', alpha=0.6, linewidth=1.5, markersize=4,
                    label=f"{idx.upper()} mean")
        if med_col in df_results.columns:
            plt.plot(df_results.index, df_results[med_col], 
                    's--', alpha=0.4, linewidth=1.5, markersize=3,
                    label=f"{idx.upper()} median")
    
    # plot rolling mean if provided
    if df_rolling is not None:
        for idx in indices:
            mean_col = f"{idx}_mean"
            if mean_col in df_rolling.columns:
                plt.plot(df_rolling.index, df_rolling[mean_col], 
                        '-', linewidth=3, alpha=0.9,
                        label=f"{idx.upper()} rolling")

    plt.xlabel("Date")
    plt.ylabel("Index Value")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_wqi_seasonal(monthly_avg, indices=["ndwi", "ndti", "ndci"], title="WQI Seasonal Cycle"):
    """
    Plot monthly/seasonal cycle of WQI indices (mean & median).
    
    Parameters
    ----------
    monthly_avg : pd.DataFrame
        Monthly averages with month names as index
    indices : list
        List of indices to plot
    title : str
        Plot title
    """
    plt.figure(figsize=(12,6))
    
    # plot mean & median
    for idx in indices:
        mean_col = f"{idx}_mean"
        med_col = f"{idx}_median"
        
        if mean_col in monthly_avg.columns:
            plt.plot(monthly_avg.index, monthly_avg[mean_col], 
                    'o-', linewidth=3, markersize=8, label=f"{idx.upper()} mean")
        if med_col in monthly_avg.columns:
            plt.plot(monthly_avg.index, monthly_avg[med_col], 
                    's--', linewidth=2.5, markersize=6, label=f"{idx.upper()} median")

    plt.xlabel("Month")
    plt.ylabel("Index Value")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()
