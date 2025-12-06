import xarray as xr
import numpy as np
from pystac_client import Client
import planetary_computer as pc
import stackstac

def environmental_variables(
    bbox,
    start_date,
    end_date,
    variables=["sst", "precip"]
):
    """
    Hybrid environmental variable loader:
    - SST from NOAA OISST daily (OPeNDAP, multiple per-year files; lon 0–360)
    - Precip from MRMS (Planetary Computer STAC)

    bbox = (min_lon, min_lat, max_lon, max_lat) in -180..180
    start_date, end_date = "YYYY-MM-DD"
    """

    results = {}

    # -----------------------------------
    # 1. SST FROM OPeNDAP (NOAA OISST)
    # -----------------------------------
    if "sst" in variables:
        print("\n Fetching SST from NOAA OISST (OPeNDAP)...")

        try:
            start_year = int(start_date[:4])
            end_year = int(end_date[:4])

            urls = [
                (
                    "https://psl.noaa.gov/thredds/dodsC/"
                    f"Datasets/noaa.oisst.v2.highres/sst.day.mean.{year}.nc"
                )
                for year in range(start_year, end_year + 1)
            ]

            # Open all needed years and combine by coordinates
            ds = xr.open_mfdataset(urls, combine="by_coords")

            # Unpack bbox
            min_lon, min_lat, max_lon, max_lat = bbox

            # OISST longitudes are 0–360, so convert western hemisphere
            if min_lon < 0:
                min_lon_360 = min_lon + 360
                max_lon_360 = max_lon + 360
            else:
                min_lon_360, max_lon_360 = min_lon, max_lon

            # Slice spatially and temporally
            sst_region = ds["sst"].sel(
                time=slice(start_date, end_date),
                lat=slice(min_lat, max_lat),
                lon=slice(min_lon_360, max_lon_360)
            )

            # Mask fill values if present
            fill = ds["sst"].attrs.get("_FillValue", None)
            if fill is not None:
                sst_region = sst_region.where(sst_region != fill)

            # Daily mean over bbox
            sst_mean = sst_region.mean(dim=["lat", "lon"])

            # Drop all-NaN times
            if "time" in sst_mean.dims:
                sst_mean = sst_mean.dropna("time", how="all")

            sst_mean.name = "sst"
            results["sst"] = sst_mean

            print(f"✔ SST loaded: {sst_mean.sizes.get('time', 0)} days")

        except Exception as e:
            print(f" SST load failed: {e}")
            results["sst"] = None

    # -----------------------------------
    # 2. PRECIP FROM PLANETARY COMPUTER
    # -----------------------------------
    if "precip" in variables:
        print("\n Fetching Precipitation (NOAA MRMS)...")

        try:
            client = Client.open(
                "https://planetarycomputer.microsoft.com/api/stac/v1",
                modifier=pc.sign_inplace
            )

            search = client.search(
                collections=["noaa-mrms-qpe-24h-pass2"],
                datetime=f"{start_date}/{end_date}",
                bbox=bbox,
                limit=1000
            )

            items = list(search.items())
            print(f"Found {len(items)} precip items")

            if len(items) == 0:
                results["precip"] = None
            else:
                signed = [pc.sign(i) for i in items]

                precip_stack = stackstac.stack(
                    signed,
                    assets=["cog"],
                    epsg=4326,
                    fill_value=np.nan
                )

                precip_mean = precip_stack.mean(dim=["x", "y"]).squeeze()
                precip_mean.name = "precip"

                # Drop any all-NaN time steps just to be safe
                if "time" in precip_mean.dims:
                    precip_mean = precip_mean.dropna("time", how="all")

                results["precip"] = precip_mean
                print(f"✔ Precip loaded: {precip_mean.sizes.get('time', 0)} days")

        except Exception as e:
            print(f" Precip load failed: {e}")
            results["precip"] = None

    return results
