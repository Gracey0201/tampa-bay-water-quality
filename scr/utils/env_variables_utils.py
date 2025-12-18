from typing import Dict, List, Tuple, Union
import xarray as xr
import pandas as pd
from pystac_client import Client as STACClient
import planetary_computer as pc
from pystac.item import Item


def environmental_variables(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    variables: List[str] = ["sst", "precip"],
    # Original SST URL is default, but the logic inside adapts to alternative URLs like MUR SST.
    sst_zarr_url: str = "s3://surftemp-sst/data/sst.zarr",
    precip_collection: str = "noaa-mrms-qpe-24h-pass2",
    stac_api_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
) -> Dict[str, Union[xr.DataArray, List[Item], None]]:
    """
    Modular environmental data fetcher for SST and Precipitation.

    Parameters
    ----------
    bbox : (minx, miny, maxx, maxy)
        Bounding box for spatial subsetting.
    start_date, end_date : str
        ISO date strings (e.g., "YYYY-MM-DD") for time subsetting.
    variables : list of str
        Requested variables (e.g., ["sst", "precip"]).
    sst_zarr_url : str
        URL to the Zarr store for Sea Surface Temperature.
    precip_collection : str
        STAC Collection ID for precipitation data.
    stac_api_url : str
        Base URL for the STAC API endpoint.

    Returns
    -------
    dict
        Dictionary with keys matching the requested variables, containing either
        an xr.DataArray (for SST) or a List[Item] (for Precipitation, or None if
        the STAC API request fails or times out).
    """

    results: Dict[str, Union[xr.DataArray, List[Item], None]] = {}

    # Define common variables based on the provided URL for modularity
    is_mur_data = "mur-sst" in sst_zarr_url.lower()
    sst_var_name = "sst" if is_mur_data else "analysed_sst"

    # ======================
    # SST (Zarr) - Fully Modular and Adaptive
    # ======================
    if "sst" in variables:
        try:
            ds = xr.open_zarr(sst_zarr_url, storage_options={"anon": True})

            # Select variable name dynamically based on the URL
            sst = (
                ds[sst_var_name]
                .sel(
                    time=slice(start_date, end_date),
                    lat=slice(bbox[1], bbox[3]),
                    lon=slice(bbox[0], bbox[2]),
                )
                .chunk({"time": "auto", "lat": -1, "lon": -1})
            )

            # Apply Kelvin conversion only if not MUR data
            if not is_mur_data:
                # Original dataset requires conversion from Kelvin to Celsius
                sst = sst - 273.15
                print("Note: SST conversion (Kelvin to Celsius) applied.")

            # Final aggregation logic (common to both)
            sst = sst.mean(dim=["lat", "lon"])
            sst = sst.resample(time="1ME").mean()
            sst.name = "sst"

            results["sst"] = sst

        except Exception as e:
            print(f"SST fetch and processing failed: {e}")
            results["sst"] = None

    # ======================
    # Precipitation (STAC) - Robust Item Retrieval with timeout handling
    # ======================
    if "precip" in variables:
        all_items: List[Item] = []

        try:
            client = STACClient.open(
                stac_api_url,
                modifier=pc.sign_inplace,
            )

            for year in range(
                pd.to_datetime(start_date).year,
                pd.to_datetime(end_date).year + 1,
            ):
                y_start = f"{year}-01-01"
                y_end = f"{year}-12-31"

                if year == pd.to_datetime(start_date).year:
                    y_start = start_date
                if year == pd.to_datetime(end_date).year:
                    y_end = end_date

                search = client.search(
                    collections=[precip_collection],
                    datetime=f"{y_start}/{y_end}",
                    bbox=bbox,
                    # no limit → pagination handled internally
                )

                # This call may time out for large queries, so keep inside try/except
                year_items = list(search.get_all_items())
                all_items.extend(year_items)

            results["precip"] = all_items if all_items else None

        except Exception as e:
            print(f"Precipitation search failed or timed out: {e}")
            results["precip"] = None

    return results