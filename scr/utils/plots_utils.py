import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import DateFormatter
import calendar
import numpy as np


# ime Series Plot
def plot_wqi_time_series(df_results, df_rolling=None, indices=["ndwi", "ndti", "ndci"], 
                         title="WQI Time Series", show_anomalies=True, anomaly_suffix="_mean_anomaly"):
    """
    Enhanced time series plot for mean/median/rolling + anomalies.
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



# Seasonal Plot
def plot_wqi_seasonal(monthly_avg, indices=["ndwi", "ndti", "ndci"], title="WQI Seasonal Cycle"):
    """
    Enhanced seasonal plot with separate mean/median panels + full 12-month axis.
    """
    # Reindex to full 12 months
    all_months = [calendar.month_name[m] for m in range(1, 13)]
    monthly_12 = monthly_avg.reindex(all_months).fillna(np.nan)
    
    x_pos = range(12)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    colors = ['blue', 'orange', 'green']
    
    # MEAN panel
    ax_mean = axes[0]
    for idx, color in zip(indices, colors):
        if f'{idx}_mean' in monthly_12.columns:
            ax_mean.plot(x_pos, monthly_12[f'{idx}_mean'], 'o-', 
                         color=color, linewidth=3, markersize=10, label=f'{idx.upper()} mean')
    ax_mean.set_title('Seasonal Cycle - MEANS', fontweight='bold', fontsize=14)
    ax_mean.grid(alpha=0.3)
    ax_mean.legend()
    
    # MEDIAN panel
    ax_med = axes[1]
    for idx, color in zip(indices, colors):
        if f'{idx}_median' in monthly_12.columns:
            ax_med.plot(x_pos, monthly_12[f'{idx}_median'], 's--', 
                        color=color, linewidth=2.5, markersize=8, label=f'{idx.upper()} median')
    ax_med.set_title('Seasonal Cycle - MEDIANS', fontweight='bold', fontsize=14)
    ax_med.grid(alpha=0.3)
    ax_med.legend()
    
    # X-axis labels
    plt.xticks(x_pos, all_months, rotation=45)
    
    fig.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f'{title.replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
    plt.show()



# generating multi-Season Plot
def plot_wqi_seasons(df_results, indices=["ndwi", "ndti", "ndci"], title="WQI by Season"):
    """
    Plot WQI indices grouped by meteorological seasons (Winter, Spring, Summer, Fall).
    """
    # Assign seasons with full names
    seasons = {
        12: 'Winter', 1: 'Winter', 2: 'Winter',
        3: 'Spring', 4: 'Spring', 5: 'Spring',
        6: 'Summer', 7: 'Summer', 8: 'Summer',
        9: 'Fall', 10: 'Fall', 11: 'Fall'
    }
    df_results['season'] = df_results.index.month.map(seasons)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['blue', 'orange', 'green']
    
    for idx, color in zip(indices, colors):
        means = df_results.groupby('season')[f'{idx}_mean'].mean()
        # Order explicitly so it always goes Winter->Spring->Summer->Fall
        ordered = ['Winter', 'Spring', 'Summer', 'Fall']
        ax.plot(ordered, means[ordered], 'o-', color=color, linewidth=3, markersize=8, label=f'{idx.upper()} mean')
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylabel("Index Value")
    ax.grid(alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.show()




# Pie Chart Plot
def plot_wqi_pie_charts(df_results, indices=["ndwi", "ndti", "ndci"], title="WQI Pie Chart"):
    """
    Generate pie charts showing the fraction of positive vs negative index values.
    """
    fig, axes = plt.subplots(1, len(indices), figsize=(5*len(indices), 5))
    if len(indices) == 1:
        axes = [axes]
    
    colors = ['green', 'red']
    
    for ax, idx in zip(axes, indices):
        if f'{idx}_mean' in df_results.columns:
            pos = (df_results[f'{idx}_mean'] > 0).sum()
            neg = (df_results[f'{idx}_mean'] <= 0).sum()
            ax.pie([pos, neg], labels=['Positive', 'Negative'], autopct='%1.1f%%', colors=colors, startangle=90)
            ax.set_title(f'{idx.upper()} Positive vs Negative')
    
    fig.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()


