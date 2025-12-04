import numpy as np
import xarray as xr
from erddapy import ERDDAP
import stackstac
from pystac_client import Client as StacClient
import planetary_computer as pc
from typing import Dict, List, Tuple, Optional

def environmental_variables(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    variables: List[str] = ["sst", "precip"],
) -> Dict[str, Optional[xr.DataArray]]:
    results: Dict[str, Optional[xr.DataArray]] = {}
    min_lon, min_lat, max_lon, max_lat = bbox

    # -------------------------------------------------
    # SST from NOAA ERDDAP (FULL HISTORICAL 1981-present)
    # -------------------------------------------------
    if "sst" in variables:
        print("\nFetching SST from NOAA ERDDAP...")
        try:
            e = ERDDAP(
                server="https://coastwatch.pfeg.noaa.gov/erddap",  # Historical server
                protocol="griddap"
            )
            e.dataset_id = "erdMBsstd1day"  # FULL HISTORICAL COVERAGE
            
            constraints = {
                "time>=": f"{start_date}T00:00:00Z",
                "time<=": f"{end_date}T23:59:59Z",
                "latitude>=": min_lat,
                "latitude<=": max_lat,
                "longitude>=": min_lon,
                "longitude<=": max_lon,
            }
            
            e.constraints = constraints
            e.variables = ["sst"]
            e.griddap_initialize()
            
            sst_ds = e.to_xarray()
            print(f"SST timesteps from ERDDAP: {sst_ds.sizes.get('time', 0)}")
            
            # Already in °C, just spatial mean
            sst_mean = sst_ds["sst"].mean(dim=["latitude", "longitude"])
            sst_mean.name = "sst"
            
            print(f"SST final: {sst_mean.time.size} days")
            results["sst"] = sst_mean
            
        except Exception as e:
            print(f"SST ERDDAP failed: {e}")
            results["sst"] = None

    # -------------------------------------------------
    # Precip from Planetary Computer
    # -------------------------------------------------
    if "precip" in variables:
        print("\nSearching for precip (NOAA MRMS)...")
        try:
            client = StacClient.open("https://planetarycomputer.microsoft.com/api/stac/v1")
            collection = "noaa-mrms-qpe-24h-pass2"
            assets = ["cog"]
            
            search = client.search(
                collections=[collection],
                datetime=f"{start_date}/{end_date}",
                bbox=bbox,
                max_items=2000,
            )
            items = list(search.items())
            print(f"Found {len(items)} precip items")
            
            signed_items = [pc.sign(item) for item in items]
            stack = stackstac.stack(
                signed_items,
                assets=assets,
                epsg=4326,
                fill_value=np.nan,
            )
            da = stack.mean(dim=["x", "y"]).squeeze()
            da.name = "precip"
            print(f"Precip: {len(da.time)} days")
            results["precip"] = da
            
        except Exception as e:
            print(f"Precip failed: {e}")
            results["precip"] = None

    return results
