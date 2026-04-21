# Assessing Water Quality Dynamics and Environmental Drivers in Tampa Bay, Florida Using Remote Sensing
This project develops a reproducible geospatial analytics pipeline for monitoring coastal water quality using satellite remote sensing and environmental datasets. It demonstrates how scalable Earth observation workflows can support estuarine ecosystem monitoring, environmental risk assessment, and climate-informed decision-making.

**Authors:** Grace Nwachukwu and Kalu Okigwe  
**Course:** GEOG 313 – Final Project  

***

## Project Overview

This project designs and implements a modular geospatial data pipeline to analyze water quality dynamics in Tampa Bay, Florida, by integrating satellite-derived indicators with large-scale environmental drivers.

The work addresses a key challenge in coastal monitoring: the need for consistent, high-frequency, and scalable methods to assess water quality across complex estuarine systems. To address this, the pipeline links Sentinel-2–derived water quality indices—NDWI, NDTI, and NDCI—with environmental variables including sea surface temperature (SST) and precipitation over the period 2019–2022.

The workflow combines custom data-access functions, statistical analysis, and robust error handling to ensure reliable processing of large geospatial datasets. It leverages cloud-based geospatial technologies, including STAC APIs, StackSTAC, xarray, and Dask, enabling efficient querying, processing, and analysis of multi-temporal satellite imagery.

All analyses are fully containerized using Docker and a Conda-based environment, ensuring reproducibility, portability, and scalability across computing environments.

This work provides a transferable framework for coastal water quality monitoring that can be adapted to other regions, supporting environmental management, public health monitoring, and climate resilience planning.

***

### System Requirements
This project is fully containerized to ensure reproducibility across environments. Docker is required to run the project.

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
## Data Outputs

### Generated Datasets

| File | Description |
|------|------------|
| `indices_results.csv` | Sentinel-2 water quality indices (NDWI, NDTI, NDCI) |
| `indices_rolling.csv` | Smoothed time-series using rolling averages |
| `precip_monthly.csv` | Aggregated monthly precipitation |
| `sst_monthly.csv` | Monthly sea surface temperature |
| `env.csv` | Combined environmental dataset |

***
### Statistical and Exploratory Analysis

To evaluate relationships within the processed dataset, a set of statistical and exploratory techniques was applied to the harmonised water quality and environmental variables.

- **Pearson correlation analysis:**  
  Used to quantify pairwise relationships between water quality indices (NDWI, NDTI, NDCI) and precipitation, enabling assessment of linear dependency structures.

- **RMSE-based evaluation:**  
  Root Mean Square Error (RMSE) is used to quantify divergence between precipitation patterns and water quality indices as a comparative variability measure.

- **Principal Component Analysis (PCA):**  
  Applied to standardised variables to identify dominant variance structures and reduce dimensional complexity across environmental inputs.

- **Exploratory data analysis:**  
  Boxplots and scatterplots are used to examine distributional characteristics, variability, and pairwise relationships across precipitation regimes.

- **Seasonal aggregation analysis:**  
  Monthly heatmaps are used to visualise intra-annual variability and seasonal patterns in water quality dynamics.

Together, these methods provide a multi-perspective evaluation of environmental relationships, combining correlation, dimensionality reduction, and distributional analysis.

***
## Methods Summary

This project implements a modular geospatial analytics pipeline for processing satellite-derived water quality and environmental datasets. The system is designed for reproducibility, scalability, and robust handling of remote sensing data uncertainty.

### Environmental Data Processing (`env_utils.py`)

Environmental drivers (sea surface temperature and precipitation) are integrated through a unified data-access layer built using `xarray` and STAC APIs.

- Sea surface temperature (SST) is accessed from a public Zarr store using `xarray.open_zarr`, with dynamic variable handling depending on dataset structure.
- Spatial subsetting is applied using the Tampa Bay bounding box, followed by temporal filtering and resampling to monthly means to reduce noise and ensure temporal comparability.
- Precipitation data is retrieved via the Planetary Computer STAC API, with a year-by-year query strategy to avoid request timeouts and improve reliability over long temporal ranges.
- Error handling (`try/except`) is implemented to ensure pipeline resilience against missing or delayed remote data.

This layer ensures consistent preprocessing of heterogeneous environmental datasets prior to integration with satellite-derived indices.

### Water Quality Index Computation (`WQI_utils.py`)

Water quality indicators (NDWI, NDTI, NDCI) are derived from Sentinel-2 Level-2A imagery using a fully cloud-filtered, analysis-ready workflow.

- Sentinel-2 scenes are queried via the Earth Search STAC API for a defined spatial and temporal extent.
- A cloud cover threshold (<20%) is applied to remove contaminated observations prior to analysis.
- Image stacks are constructed using `stackstac`, enabling lazy loading of spectral bands (green, red, NIR, red-edge, SCL).
- Spectral indices are computed using normalized band ratios, with water pixels isolated using Scene Classification Layer (SCL) masks.
- Outputs are aggregated into spatial statistics (mean and median) per acquisition date, forming a time series structure.
- Rolling means and monthly climatologies are applied to reduce high-frequency noise and enable seasonal pattern detection.

A built-in quality control module evaluates scene reliability by analyzing cloud fraction, water pixel distribution, and NDWI sanity checks before inclusion in the final time series.

To ensure temporal consistency, a strict daily selection strategy is applied where only the lowest-cloud scene per day is retained, preventing duplication effects from multi-scene mosaicking and preserving natural variability in the signal.

### Analytical Data Integration Layer

To enable consistent cross-variable analysis, an integrated dataset was constructed by aligning satellite-derived water quality indicators with environmental drivers on a common temporal scale.

- Sentinel-2 water quality indices and precipitation data are aggregated to a monthly resolution and merged into a unified analytical dataset to ensure temporal alignment across heterogeneous sources.
- Feature standardisation is applied to ensure comparability across variables with different measurement scales prior to statistical evaluation.
- The resulting dataset is structured to support downstream exploratory and multivariate analysis of environmental relationships.

This layer provides a consistent analytical interface for evaluating relationships between remotely sensed water quality signals and environmental forcing variables.
***

### Literature justification
- Griffiths et al. (2019) show that temporal compositing based on the single best‑quality observation per interval (e.g., daily or weekly) preserves phenology and land‑surface dynamics better than pixel‑based mosaics, which can mix acquisitions and introduce cross‑scene artifacts.
- Li & Roy (2017) and related work on harmonized Landsat–Sentinel data demonstrate that single‑date, quality‑filtered observations are preferred for water‑index time series because mosaicking can smooth signals and mix viewing/illumination geometries, degrading change‑detection performance.
- Copernicus Sentinel‑2 processing guidance recommends temporal filtering to one acquisition per time step for consistent analysis of indices such as NDWI, NDTI, and NDCI, rather than relying on automatic mosaicking, especially when intra‑orbit variability and cloud contamination are concerns

***
### Error Handling and Limitations

Two key external issues were observed:

1. **Duplicate / non‑unique time coordinates**  
   Selecting by time (`sel(time=dt, method="nearest")`) can raise “Reindexing only valid with uniquely valued Index objects” when time coordinates are duplicated. The diagnostics in `compute_wqi_indices` were updated to catch these errors and either skip SCL/NDWI diagnostics for problematic timestamps or print a clear message instead of failing.[6][5]

2. **Remote COG access errors (CURL “Recv failure”)**  
   During `ds_ts.compute()`, some Sentinel‑2 COG reads through `stackstac` fail with `RasterioIOError: CURL error: Recv failure: Connection reset by peer`. These are transient remote host/network issues rather than logic bugs. To mitigate them, the code and documentation recommend reducing `max_items`, narrowing the time window, re‑running cells, and optionally wrapping `.compute()` in a `try/except` block to convert hard failures into warnings.[7][1]

Despite these measures, full reproducibility still depends on external cloud services (Earth Search, Sentinel‑COGs, Planetary Computer) being available and responsive at runtime.
***

### Environmental Variables Documentation And Limitation
- Precipitation (NOAA MRMS QPE 24h Pass2)
The NOAA-MRMS-QPE-24h-pass2 dataset provides high-resolution (1 km) quantitative precipitation estimates from NEXRAD radar networks across the contiguous U.S., updated every 24 hours with quality-controlled pass-2 processing. Temporal gaps in 2019-2020 often result from sparse radar coverage in coastal regions such as Tampa Bay or from delayed STAC ingestion.

- SST (surftemp-sst Zarr)
The surftemp-sst Zarr dataset contains daily analyses of sea surface temperature fields derived from satellite infrared radiometers, stored in Kelvin and requiring conversion to Celsius (-273.15). NaN values occur in coastal/high-latitude areas due to missing Zarr tiles from cloud cover or land masking in the original satellite processing.

- Due to the large number of missing values (NaNs) in the environmental variables, the correlation analysis was performed only on precipitation, which had complete data for the full year between 2023 and 2024. Consequently, the study focuses on this time period.

***
### Results
Tampa Bay Water Quality Assessment

- The annual mean maps of NDWI, NDTI, and NDCI reveal spatially coherent patterns across Tampa Bay consistent with estuarine water processes. NDWI effectively delineates open-bay waters from shorelines, confirming its utility as a water-masking index. In contrast, elevated NDTI values near coastal margins and river mouths indicate higher turbidity, driven by sediment resuspension and riverine inflows. In contrast, the central bay areas exhibit lower turbidity, and NDCI highlights elevated chlorophyll concentrations in nearshore, semi-enclosed zones, suggestive of nutrient enrichment and phytoplankton productivity.

- The composite water quality risk map integrates these indices into a classification framework that highlights spatial vulnerability gradients. Low-risk areas (green) dominate the deeper central bay waters, which experience strong ocean exchange. At the same time, moderate-to-high risk zones (yellow-red) cluster along margins, tidal creeks, and estuaries where turbidity and chlorophyll signals converge. This pattern underscores the susceptibility of nearshore environments to water-quality degradation due to reduced flushing and anthropogenic nutrient loading.

- Annual mean composites effectively reduce short-term noise to reveal persistent spatial patterns, with index stacking providing a multi-dimensional assessment superior to single-index analysis. The classification translates continuous spectral data into actionable risk categories suitable for monitoring, while spatial coherence across outputs validates preprocessing, masking, and computation accuracy.

- These results demonstrate remote sensing indices' reliability for identifying coastal water quality gradients, with higher-risk shoreline/estuarine concentrations aligning with established nutrient dynamics and sediment transport understanding. This scalable multi-index framework supports environmental monitoring and identifies priority management areas in Tampa Bay and similar coastal systems.

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

### References
- Griffiths, P., Nendel, C., & Hostert, P. (2019). Intra-annual reflectance composites from Sentinel-2 and Landsat for national-scale crop and land cover mapping. Remote sensing of environment, 220, 135-151.
- Ju, J., Zhou, Q., Freitag, B., Roy, D. P., Zhang, H. K., Sridhar, M., ... & Neigh, C. S. (2025). The Harmonized Landsat and Sentinel-2 version 2.0 surface reflectance dataset. Remote Sensing of Environment, 324, 114723.
-  [ESA Sentinel-2 Documentation](https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html)
***

### Citation

If you use this project in your research or publications, please cite it as:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18148374.svg)](https://doi.org/10.5281/zenodo.18148374)

Nwachukwu, G., & Okigwe, K. (2026). *Assessing Water Quality Dynamics and Environmental Drivers in Tampa Bay, Florida Using Remote Sensing* [Software]. Zenodo. https://doi.org/10.5281/zenodo.18148374

