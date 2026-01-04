# Assessing Water Quality Dynamics and Environmental Drivers in Tampa Bay, Florida Using Remote Sensing
This workflow demonstrates how satellite-derived indicators can support scalable coastal water-quality monitoring, with applications to environmental management, public health surveillance, and climate-adaptation planning in estuarine systems.

**Authors:** Grace Nwachukwu and Kalu Okigwe  
**Course:** GEOG 313 – Final Project  

***

## Project Overview

This project builds a modular, reproducible pipeline to link satellite‑derived water quality indices with large‑scale environmental drivers in Tampa Bay, Florida. It combines custom data-access functions, statistical analysis, and robust error handling to evaluate how sea surface temperature (SST) covaries with Sentinel‑2–based water-quality indicators (NDWI, NDTI, NDCI) during 2019–2022.[1]

All analyses are implemented in Python using xarray, Dask, StackStac, and STAC APIs. The workflow is fully containerized with a Conda environment (including pip-installed packages) and a Docker image to ensure reproducibility.

***

### System Requirements
Before running the project, ensure that you have the following installed on your machine:

- [Docker](https://docs.docker.com/get-started/get-docker/)

### Clone the Repository

```bash
git clone https://github.com/Gracey0201/tampa-bay-water-quality.git
cd tampa-bay-water-quality
```

### Steps to Run the Docker Container
You may either pull the Docker image from Dockerhub or build the image locally.

#### 1. Pull or Build the Docker Image (recommended)
```bash
docker pull tampa-bay-water-quality
```
Optionally, you can build the Docker image locally from the project folder.

```bash
docker build -t tampa-bay-water-quality .
```
#### 2. Run the container
```bash
docker run -it -p 8888:8888 -p 8787:8787 -v $(pwd):/home/jupyteruser/ --name wqi_container tampa-bay-water-quality

```
- Port `8888` is used by JupyterLab
- Port `8787` is used by Dask Dashboard

#### 3. Access JupyterLab
- Once the container starts, JupyterLab will launch automatically.
- Copy the access token printed in the terminal and paste it into your browser.

#### 4. Open and Run the Notebooks
Inside JupyterLab, navigate to the `src/notebooks/` directory and open the notebooks in sequence to reproduce the analysis.

***
### Stopping and Managing the Container
```bash
docker stop wqi_container
```

### To Restart the Container, Use
```bash
docker start -i wqi_container
```
### To Remove the Container Use
```bash
docker rm wqi_container
```

### To Remove the Image Use
```bash
docker rmi tampa-bay-water-quality
```
***

### Notebook Overview (src/notebooks)

| Notebook                       | Objective                                                            |
| ------------------------------ | -------------------------------------------------------------------- |
| `WQI.ipynb`                    | Compute NDWI, NDTI, and NDCI from Sentinel-2 imagery                 |
| `WQI_precip_correlation.ipynb` | Correlation analysis between water quality indices and precipitation |
| `WQI_spatial_maps.ipynb`       | Spatial mapping of water quality indices (pro                             |
| `env_variables.ipynb`          | Aggregate SST and precipitation datasets                             |

***
### Util Overview (src/utils)

| File                       | Description                                             |
| -------------------------- | ------------------------------------------------------- |
| `stack_loader.py`          | Loads sentinel-2 stack for fast map plotting    |
| `WQI_utils.py`             | Functions to compute NDWI, NDTI, and NDCI               |
| `env_variables_utils.py`   | SST and precipitation aggregation functions             |
| `plots_utils.py`           | Time-series and comparative plotting functions          |
| `spatial_utils.py`         | Spatial processing, mapping, and hotspot detection       |

***
#### Notebooks and Functions Workflow Summary
The analysis workflow is organized across multiple notebooks:

- **Water Quality Indices (`WQI.ipynb`)**  
  Uses the `WQI_utils` and `plots_utils` functions to compute and plot water quality indices.

- **Environmental Variables (`env_variables.ipynb`)**  
  Uses the `env_variables_utils` functions to evaluate environmental data.

- **Spatial Maps (`WQI_spatial_maps.ipynb`)**  
  Generates maps for water quality indices using `spatial_utils.py` and `stack_loader.py`.

- **Correlation Analysis (`WQI_precip_correlation.ipynb`)**  
  Reads precomputed CSV outputs from other notebooks to efficiently explore relationships between water quality and environmental variables without rerunning computationally intensive computations.

***
## Methods Summary

### Environmental data (env_utils.py)

`environmental_variables` provides a generic interface to environmental drivers:

- Opens a public SST Zarr store with `xarray.open_zarr`, selecting the correct variable name (`analysed_sst` or `sst`) depending on the product.  
- Subsets SST in space (Tampa Bay bounding box) and time, converts from Kelvin to Celsius when needed, computes spatial means, and resamples to monthly means.  
- Uses the Planetary Computer STAC API to search MRMS precipitation items over the same bbox/time window, handling time ranges year‑by‑year to avoid long requests and wrapping calls in `try/except` to catch timeouts.[1]

The function returns a dictionary with SST as an `xarray.DataArray` and precipitation as a list of STAC `Item`s or `None`.

### Water quality indices (WQI_utils.py)

`compute_wqi_indices` implements the Sentinel‑2 WQI pipeline:

- Queries Sentinel‑2 L2A scenes via Earth Search STAC for a Tampa Bay bounding box and date range.  
- Filters scenes by cloud cover threshold (e.g., `< 20%`) before stacking.  
- Uses `stackstac.stack` to build a lazy 4‑D array over bands `green`, `red`, `nir`, `rededge1`, and `scl`.  
- Computes NDWI, NDTI, and NDCI via a normalized difference function and applies an SCL‑based water mask (classes 5–6) to focus on water pixels.  
- Aggregates indices to spatial means/medians per time step, builds a dataset of NDWI/NDTI/NDCI statistics, and converts to a pandas DataFrame with a datetime index.  
- Computes rolling means over a user‑defined window and monthly climatologies for all indices.

- To verify that the Sentinel‑2 inputs over Tampa Bay were suitable for water‑quality analysis, a diagnostics mode was implemented that inspects the first few scenes before index computation. For each of the first five acquisitions, the workflow reports the acquisition date and ID, the thumbnail link, and the metadata cloud-cover value, then uses the SCL band to quantify the fraction of cloud versus water pixels and the number of valid observations. It also computes a scene‑average NDWI sanity check (green vs. NIR) to flag obviously contaminated scenes (e.g., strongly positive NDWI suggesting land or cloud influence). This diagnostic loop provides a quick, reproducible quality‑control snapshot of typical scenes and documents, and the subsequent NDWI/NDTI/NDCI time series is based predominantly on cloud‑free water pixels rather than artifacts.

- To ensure a clean and physically meaningful water‑quality time series, the workflow uses strict daily sub‑sampling rather than multi‑scene mosaics. Sentinel‑2 scenes are first filtered to retain only observations with less than 20% eo:cloud_cover, removing heavily contaminated acquisitions. From the remaining scenes, only the lowest‑cloud‑cover image for each date is retained, so at most one scene per day enters the analysis. This daily deduplication is applied prior to stacking and computing NDWI, NDTI, and NDCI for Tampa Bay. By avoiding mosaicking of multiple intra‑day scenes, the method prevents artificial smoothing and pixel mixing that could distort temporal variability in the indices. The result is a temporally consistent water‑quality time series in which changes reflect fundamental environmental dynamics rather than artifacts of overlapping Sentinel‑2 acquisitions. 

#### Literature justification
- Griffiths et al. (2019) show that temporal compositing based on the single best‑quality observation per interval (e.g., daily or weekly) preserves phenology and land‑surface dynamics better than pixel‑based mosaics, which can mix acquisitions and introduce cross‑scene artifacts.
- Li & Roy (2017) and related work on harmonized Landsat–Sentinel data demonstrate that single‑date, quality‑filtered observations are preferred for water‑index time series because mosaicking can smooth signals and mix viewing/illumination geometries, degrading change‑detection performance.
- Copernicus Sentinel‑2 processing guidance recommends temporal filtering to one acquisition per time step for consistent analysis of indices such as NDWI, NDTI, and NDCI, rather than relying on automatic mosaicking, especially when intra‑orbit variability and cloud contamination are concerns

***
#### Error Handling and Limitations

Two key external issues were observed:

1. **Duplicate / non‑unique time coordinates**  
   Selecting by time (`sel(time=dt, method="nearest")`) can raise “Reindexing only valid with uniquely valued Index objects” when time coordinates are duplicated. The diagnostics in `compute_wqi_indices` were updated to catch these errors and either skip SCL/NDWI diagnostics for problematic timestamps or print a clear message instead of failing.[6][5]

2. **Remote COG access errors (CURL “Recv failure”)**  
   During `ds_ts.compute()`, some Sentinel‑2 COG reads through `stackstac` fail with `RasterioIOError: CURL error: Recv failure: Connection reset by peer`. These are transient remote host/network issues rather than logic bugs. To mitigate them, the code and documentation recommend reducing `max_items`, narrowing the time window, re‑running cells, and optionally wrapping `.compute()` in a `try/except` block to convert hard failures into warnings.[7][1]

Despite these measures, full reproducibility still depends on external cloud services (Earth Search, Sentinel‑COGs, Planetary Computer) being available and responsive at runtime.
***

#### Environmental Variables Documentation And Limitation
- Precipitation (NOAA MRMS QPE 24h Pass2)
The NOAA-MRMS-QPE-24h-pass2 dataset provides high-resolution (1 km) quantitative precipitation estimates from NEXRAD radar networks across the contiguous U.S., updated every 24 hours with quality-controlled pass-2 processing. Temporal gaps in 2019-2020 often result from sparse radar coverage in coastal regions such as Tampa Bay or from delayed STAC ingestion.

- SST (surftemp-sst Zarr)
The surftemp-sst Zarr dataset contains daily analyses of sea surface temperature fields derived from satellite infrared radiometers, stored in Kelvin and requiring conversion to Celsius (-273.15). NaN values occur in coastal/high-latitude areas due to missing Zarr tiles from cloud cover or land masking in the original satellite processing.

- Due to the large number of missing values (NaNs) in the environmental variables, the correlation analysis was performed only on precipitation, which had complete data for the full year between 2023 and 2024. Consequently, the study focuses on this time period.
***

***
### Results
Tampa Bay Water Quality Assessment

- The annual mean maps of NDWI, NDTI, and NDCI reveal spatially coherent patterns across Tampa Bay consistent with estuarine water processes. NDWI effectively delineates open-bay waters from shorelines, confirming its utility as a water-masking index. In contrast, elevated NDTI values near coastal margins and river mouths indicate higher turbidity, driven by sediment resuspension and riverine inflows. In contrast, the central bay areas exhibit lower turbidity, and NDCI highlights elevated chlorophyll concentrations in nearshore, semi-enclosed zones, suggestive of nutrient enrichment and phytoplankton productivity.

- The composite water quality risk map integrates these indices into a classification framework that highlights spatial vulnerability gradients. Low-risk areas (green) dominate the deeper central bay waters, which experience strong ocean exchange. At the same time, moderate-to-high risk zones (yellow-red) cluster along margins, tidal creeks, and estuaries where turbidity and chlorophyll signals converge. This pattern underscores the susceptibility of nearshore environments to water-quality degradation due to reduced flushing and anthropogenic nutrient loading.

- Annual mean composites effectively reduce short-term noise to reveal persistent spatial patterns, with index stacking providing a multi-dimensional assessment superior to single-index analysis. The classification translates continuous spectral data into actionable risk categories suitable for monitoring, while spatial coherence across outputs validates preprocessing, masking, and computation accuracy.

- These results demonstrate remote sensing indices' reliability for identifying coastal water quality gradients, with higher-risk shoreline/estuarine concentrations aligning with established nutrient dynamics and sediment transport understanding. This scalable multi-index framework supports environmental monitoring and identifies priority management areas in Tampa Bay and similar coastal systems.
***

***
#### AI Use Policy
In addition to using the lecture notes and resources (especially in creating functions), AI tools were also utilized both in generating codes, scripts (mostly generating utils) and documentations to support the development of this project. However, all AI-generated content has been carefully reviewed to ensure accuracy and correctness.
***

***
#### Team Roles

- **Grace Nwachukwu**
  - Developed all functions and accompanying notebooks for water quality analysis, plots, and maps.
  
- **Kalu Okigwe**
  - Developed functions and accompanying notebooks for environmental variables (SST and precipitation)analysis and plots.  

- **Joint**
  - Designed the integrated pipeline, Docker/conda setup.  
  - Wrote documentation and coordinated Git/GitHub workflow.
  - produced the notebook and codes for the Pearson correlation, RMSE, and PCA plots.
***

#### References
- Griffiths, P., Nendel, C., & Hostert, P. (2019). Intra-annual reflectance composites from Sentinel-2 and Landsat for national-scale crop and land cover mapping. Remote sensing of environment, 220, 135-151.
- Ju, J., Zhou, Q., Freitag, B., Roy, D. P., Zhang, H. K., Sridhar, M., ... & Neigh, C. S. (2025). The Harmonized Landsat and Sentinel-2 version 2.0 surface reflectance dataset. Remote Sensing of Environment, 324, 114723.
-  [ESA Sentinel-2 Documentation](https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html)
***

#### Cite This Work

If you use this project in your research or publications, please cite it as:

### Tampa Bay Water Quality Project
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18148374.svg)](https://doi.org/10.5281/zenodo.18148374)

**Citation:**
Nwachukwu, G., & Okigwe, K. (2026). *Assessing Water Quality Dynamics and Environmental Drivers in Tampa Bay, Florida Using Remote Sensing* [Software]. Zenodo. https://doi.org/10.5281/zenodo.18148374

