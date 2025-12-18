import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import DateFormatter
import calendar
import numpy as np

def plot_wqi_time_series(df_results, df_rolling=None, indices=["ndwi", "ndti", "ndci"], 
                         title="WQI Time Series", show_anomalies=True, anomaly_suffix="_mean_anomaly"):
    """
    Plot WQI time series with mean, median, and optional rolling mean and anomalies.

    Parameters
    ----------
    df_results : pd.DataFrame
        WQI time series with columns '{index}_mean', '{index}_median', and optional anomaly flags.
    df_rolling : pd.DataFrame, optional
        Rolling mean values for indices, plotted in the rolling panel.
    indices : list of str
        WQI indices to plot.
    title : str
        Figure title (also used for PNG filename).
    show_anomalies : bool
        If True, mark anomalies in the mean panel.
    anomaly_suffix : str
        Suffix for anomaly flag columns in df_results.

    Returns
    -------
    None
    """
    n_indices = len(indices)
    fig, axes = plt.subplots(n_indices, 3, figsize=(18, 4*n_indices), sharex=True)
    if n_indices == 1:
        axes = axes.reshape(1, 3)
    
    colors = ['blue', 'orange', 'green']
    
    for i, (idx, color) in enumerate(zip(indices, colors)):
        # Mean panel
        ax_mean = axes[i, 0]
        ax_mean.plot(df_results.index, df_results[f'{idx}_mean'], 
                     color=color, linewidth=2, alpha=0.8, label='Mean')
        
        # Anomalies on mean
        if show_anomalies:
            anom_col = f'{idx}{anomaly_suffix}'
            if anom_col in df_results.columns:
                anomalies = df_results[df_results[anom_col] == True]
                ax_mean.scatter(anomalies.index, anomalies[f'{idx}_mean'], 
                                color='red', s=100, marker='^', 
                                edgecolor='black', linewidth=1.5, zorder=5, label='Anomalies')
        
        ax_mean.set_title(f'{idx.upper()} - MEAN', fontweight='bold')
        ax_mean.grid(alpha=0.3)
        ax_mean.legend()
        
        # Median panel  
        ax_med = axes[i, 1]
        ax_med.plot(df_results.index, df_results[f'{idx}_median'], 
                    color=color, linewidth=2, alpha=0.8, linestyle='--', label='Median')
        ax_med.set_title(f'{idx.upper()} - MEDIAN', fontweight='bold')
        ax_med.grid(alpha=0.3)
        ax_med.legend()
        
        # Rolling panel
        ax_roll = axes[i, 2]
        if df_rolling is not None and f'{idx}_mean' in df_rolling.columns:
            ax_roll.plot(df_rolling.index, df_rolling[f'{idx}_mean'], 
                         color=color, linewidth=3, label='Rolling Mean')
            # Overlay raw mean faintly
            ax_roll.plot(df_results.index, df_results[f'{idx}_mean'], 
                         color=color, alpha=0.3, linewidth=0.8)
        ax_roll.set_title(f'{idx.upper()} - ROLLING', fontweight='bold')
        ax_roll.grid(alpha=0.3)
        ax_roll.legend()
    
    # Format x-axis
    for ax in axes.flat[-3:]:  # Last row
        ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    
    fig.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f'{title.replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
    plt.show()
