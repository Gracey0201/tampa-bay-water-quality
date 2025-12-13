import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm

def normalized_diff(b1, b2):
    """Compute normalized difference (b1-b2)/(b1+b2)."""
    return (b1 - b2) / (b1 + b2 + 1e-10)

def plot_wqi_index_maps(stack, indices=["ndwi", "ndti", "ndci"], title="WQI Index Maps"):
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    green = stack.sel(band='green')
    red = stack.sel(band='red') 
    nir = stack.sel(band='nir')
    rededge1 = stack.sel(band='rededge1')
    
    ndwi = normalized_diff(green, nir)
    ndti = normalized_diff(red, green)
    ndci = normalized_diff(rededge1, red)
    
    maps = [ndwi.mean('time'), ndti.mean('time'), ndci.mean('time')]
    map_names = ['NDWI', 'NDTI', 'NDCI']
    
    for i, (map_data, name) in enumerate(zip(maps, map_names)):
        ax = axes[i//2, i%2]
        map_data.plot(ax=ax, cmap='RdYlBu_r', vmin=-0.5, vmax=0.3)
        ax.set_title(f'{name} - Annual Mean')
    
    ndwi_std = ndwi.std('time')
    ndwi_std.plot(ax=axes[1,1], cmap='Reds', vmin=0, vmax=0.2)
    axes[1,1].set_title('NDWI - Std Dev')
    
    plt.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{title.replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
    plt.show()

def plot_wqi_std_maps(stack, indices=["ndwi", "ndti", "ndci"], title="WQI Standard Deviation Maps"):
    green = stack.sel(band='green')
    red = stack.sel(band='red') 
    nir = stack.sel(band='nir')
    rededge1 = stack.sel(band='rededge1')
    
    ndwi = normalized_diff(green, nir)
    ndti = normalized_diff(red, green)
    ndci = normalized_diff(rededge1, red)
    
    fig, axes = plt.subplots(1, len(indices), figsize=(5*len(indices), 5))
    if len(indices) == 1:
        axes = [axes]
    
    std_maps = [ndwi.std('time'), ndti.std('time'), ndci.std('time')]
    
    for i, (std_map, idx) in enumerate(zip(std_maps, indices)):
        std_map.plot(ax=axes[i], cmap='Reds', vmin=0, vmax=0.25)
        axes[i].set_title(f'{idx.upper()} Std Dev')
    
    plt.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{title.replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
    plt.show()
