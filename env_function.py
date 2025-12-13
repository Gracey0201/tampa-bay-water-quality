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
    sst_zarr_url: str = "s3://surftemp-sst/data/sst.zarr",
    precip_collection: str = "noaa-mrms-qpe-24h-pass2",
    stac_api_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
) -> Dict[str, Union[xr.DataArray, List[Item], None]]:
    """
    Modular environmental data fetcher.

    Parameters
    ----------
    bbox : (minx, miny, maxx, maxy)
    start_date, end_date : ISO date strings
    variables : list of requested variables
    sst_zarr_url : Zarr store for SST
    precip_collection : STAC precipitation collection ID
    stac_api_url : STAC endpoint

    Returns
    -------
    dict with keys ['sst', 'precip']
    """

    results = {}

    # ======================
    # SST (Zarr)
    # ======================
    if "sst" in variables:
        try:
            ds = xr.open_zarr(sst_zarr_url, storage_options={"anon": True})

            sst = (
                ds["analysed_sst"]
                .sel(
                    time=slice(start_date, end_date),
                    lat=slice(bbox[1], bbox[3]),
                    lon=slice(bbox[0], bbox[2])
                )
                .chunk({"time": "auto", "lat": -1, "lon": -1})
            )

            sst = (sst - 273.15).mean(dim=["lat", "lon"])
            sst = sst.resample(time="1ME").mean()
            sst.name = "sst"

            results["sst"] = sst

        except Exception as e:
            print(f"SST failed: {e}")
            results["sst"] = None

    # ======================
    # Precipitation (STAC)
    # ======================
    if "precip" in variables:
        all_items: List[Item] = []

        client = STACClient.open(
            stac_api_url,
            modifier=pc.sign_inplace
        )

        for year in range(
            pd.to_datetime(start_date).year,
            pd.to_datetime(end_date).year + 1
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
                limit=1000
            )

            all_items.extend(list(search.get_all_items()))

        results["precip"] = all_items if all_items else None

    return results
