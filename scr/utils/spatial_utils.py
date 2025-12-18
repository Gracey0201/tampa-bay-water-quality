import matplotlib.pyplot as plt
import numpy as np

def normalized_diff(b1, b2):
    """
    Compute the normalized difference between two arrays.

    Parameters
    ----------
    b1, b2 : array-like
        Input arrays (e.g., image bands).

    Returns
    -------
    np.ndarray
        Normalized difference (b1 - b2) / (b1 + b2), with small epsilon to avoid division by zero.
    """
    return (b1 - b2) / (b1 + b2 + 1e-10)


# Annual Mean WQI Maps
def plot_wqi_mean_maps(
    stack,
    title="Tampa Bay Water Quality Index (Annual Mean)",
    cmap="RdYlBu_r"
):
    """
    Plot annual mean maps of NDWI, NDTI, and NDCI from a stackstac stack.

    Parameters
    ----------
    stack : xarray.Dataset
        Multi-band stack containing at least 'green', 'red', 'nir', 'rededge1'.
    title : str
        Title for the figure and PNG file.
    cmap : str
        Colormap to use for plotting.

    Returns
    -------
    None
    """
    # Extract bands
    green = stack.sel(band="green")
    red = stack.sel(band="red")
    nir = stack.sel(band="nir")
    rededge1 = stack.sel(band="rededge1")

    # Compute indices
    indices = {
        "NDWI": normalized_diff(green, nir),
        "NDTI": normalized_diff(red, green),
        "NDCI": normalized_diff(rededge1, red),
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharex=True, sharey=True)

    for ax, (name, data) in zip(axes, indices.items()):
        mean_data = data.mean("time")
        mean_data.plot(
            ax=ax,
            cmap=cmap,
            vmin=-0.5,
            vmax=0.3,
            cbar_kwargs={"label": f"{name} Annual Mean"}
        )
        ax.set_title(f"{name} – Annual Mean", fontweight="bold")
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")
        ax.set_aspect("equal")

    plt.suptitle(title, fontsize=16, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(f"{title.replace(' ', '_')}.png", dpi=300, bbox_inches="tight")
    plt.show()


# WQI Standard Deviation Maps (All Indices)
def plot_wqi_std_maps(
    stack,
    title="Tampa Bay Water Quality Index (Temporal Variability)",
    cmap="Reds"
):
    """
    Plot temporal standard deviation maps of NDWI, NDTI, and NDCI from a stackstac stack.

    Parameters
    ----------
    stack : xarray.Dataset
        Multi-band stack containing at least 'green', 'red', 'nir', 'rededge1'.
    title : str
        Title for the figure and PNG file.
    cmap : str
        Colormap to use for plotting.

    Returns
    -------
    None
    """
    # Extract bands
    green = stack.sel(band="green")
    red = stack.sel(band="red")
    nir = stack.sel(band="nir")
    rededge1 = stack.sel(band="rededge1")

    # Compute indices
    indices = {
        "NDWI": normalized_diff(green, nir),
        "NDTI": normalized_diff(red, green),
        "NDCI": normalized_diff(rededge1, red),
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharex=True, sharey=True)

    for ax, (name, data) in zip(axes, indices.items()):
        std_data = data.std("time")
        std_data.plot(
            ax=ax,
            cmap=cmap,
            vmin=0,
            vmax=0.25,
            cbar_kwargs={"label": f"{name} Std Dev"}
        )
        ax.set_title(f"{name} – Temporal Std Dev", fontweight="bold")
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")
        ax.set_aspect("equal")

    plt.suptitle(title, fontsize=16, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(f"{title.replace(' ', '_')}.png", dpi=300, bbox_inches="tight")
    plt.show()
