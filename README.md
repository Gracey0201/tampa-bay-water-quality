# Assessing Water Quality Dynamics and Environmental Drivers in Tampa Bay, Florida Using Remote Sensing
This project develops a reproducible geospatial analytics pipeline for monitoring coastal water quality using satellite remote sensing and environmental datasets. It demonstrates how scalable Earth observation workflows can support estuarine ecosystem monitoring, environmental risk assessment, and climate-informed decision-making.

**Authors:** Grace Nwachukwu and Kalu Okigwe  
**Project Type:** End-to-End Geospatial Analytics Pipeline for Coastal Environmental Monitoring 

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
### Notebooks and Functions Workflow Summary
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
- Image stacks are constructed using stackstac, enabling lazy loading of spectral bands (green, red, NIR, red-edge, SCL).
- Spectral indices are computed using normalized band ratios, with water pixels isolated using Scene Classification Layer (SCL) masks.
- Outputs are aggregated into spatial statistics (mean and median) per acquisition date, forming a time series structure.
- Rolling means and monthly climatologies are applied to reduce high-frequency noise and enable seasonal pattern detection.
- A built-in quality control module evaluates scene reliability by analyzing cloud fraction, water pixel distribution, and NDWI sanity checks before inclusion in the final time series.
- A strict daily selection strategy is applied where only the lowest-cloud scene per day is retained, preventing duplication effects from multi-scene mosaicking and preserving natural variability in the signal.

#### Rationale for temporal filtering and single-scene selection:
Temporal compositing using a single high-quality observation per time step preserves environmental signals more effectively than mosaicking approaches, which can introduce cross-scene artifacts and distort temporal dynamics (Griffiths et al., 2019).
Harmonized Landsat–Sentinel studies show that single-date, quality-filtered observations improve water index consistency by avoiding geometric and illumination mixing effects (Li & Roy, 2017).
Copernicus Sentinel-2 processing guidance recommends per-time-step filtering rather than mosaicking for indices such as NDWI, NDTI, and NDCI to maintain physical interpretability under cloud-contaminated conditions.

### Analytical Data Integration and Statistical Analysis Module
To enable cross-variable analysis, satellite-derived water quality indicators were integrated with environmental drivers on a common monthly temporal scale.

Sentinel-2 indices (NDWI, NDTI, NDCI) and precipitation data were resampled to monthly resolution and transformed to ensure comparability across differing measurement scales.

This produces a consistent dataset for evaluating relationships between remotely sensed water quality dynamics and environmental forcing.

A combined statistical and exploratory framework was then applied:

- Pearson correlation analysis: Quantifies linear relationships between water quality indices and precipitation, enabling assessment of dependency structures.
- RMSE evaluation: Measures divergence between precipitation patterns and water quality variability as a comparative metric.
- Principal Component Analysis (PCA): Identifies dominant variance structures and reduces dimensional complexity across multivariate inputs.
- Exploratory analysis: Boxplots and scatterplots are used to assess variability, distributional structure, and pairwise relationships.
- Seasonal aggregation: Monthly heatmaps are used to visualise intra-annual and seasonal variability in water quality dynamics.

Together, these methods provide a multi-scale analytical framework combining correlation analysis, dimensionality reduction, and distributional exploration of environmental relationships.
***

### Error Handling and Limitations

Two key external issues were observed:

1. **Duplicate / non‑unique time coordinates**  
   Selecting by time (`sel(time=dt, method="nearest")`) can raise “Reindexing only valid with uniquely valued Index objects” when time coordinates are duplicated. The diagnostics in `compute_wqi_indices` were updated to catch these errors and either skip SCL/NDWI diagnostics for problematic timestamps or print a clear message instead of failing.

2. **Remote COG access errors (CURL “Recv failure”)**  
   During `ds_ts.compute()`, some Sentinel‑2 COG reads through `stackstac` fail with `RasterioIOError: CURL error: Recv failure: Connection reset by peer`. These are transient remote host/network issues rather than logic bugs. To mitigate them, the code and documentation recommend reducing `max_items`, narrowing the time window, re‑running cells, and optionally wrapping `.compute()` in a `try/except` block to convert hard failures into warnings.
   
Despite these measures, full reproducibility still depends on external cloud services (Earth Search, Sentinel‑COGs, Planetary Computer) being available and responsive at runtime.
***

### Environmental Variables Documentation And Limitation
- Precipitation (NOAA MRMS QPE 24h Pass2)
The NOAA-MRMS-QPE-24h-pass2 dataset provides high-resolution (1 km) quantitative precipitation estimates from NEXRAD radar networks across the contiguous U.S., updated every 24 hours with quality-controlled pass-2 processing. Temporal gaps in 2019-2020 often result from sparse radar coverage in coastal regions such as Tampa Bay or from delayed STAC ingestion.

- SST (surftemp-sst Zarr)
The surftemp-sst Zarr dataset contains daily analyses of sea surface temperature fields derived from satellite infrared radiometers, stored in Kelvin and requiring conversion to Celsius (-273.15). NaN values occur in coastal/high-latitude areas due to missing Zarr tiles from cloud cover or land masking in the original satellite processing.

- Due to the large number of missing values (NaNs) in the environmental variables, the correlation analysis was performed only on precipitation, which had complete data for the full year between 2023 and 2024. Consequently, the study focuses on this time period.

***
## Results
- Annual composite products of NDWI, NDTI, and NDCI were generated from Sentinel-2 imagery to quantify spatial and temporal variability in Tampa Bay coastal water quality.

- NDWI output reliably delineates land–water boundaries, enabling robust masking for downstream geospatial analysis.

- NDTI identifies persistent turbidity hotspots associated with sediment resuspension at riverine inflows.

- NDCI captures chlorophyll variability, with elevated concentrations concentrated in semi-enclosed nearshore zones, indicating nutrient enrichment and phytoplankton activity.

- A multi-index classification system was implemented to generate spatial water quality risk zones (low–high) across the estuary.

- Low-risk zones are primarily located in deeper offshore waters with stronger hydrodynamic exchange, while higher-risk zones cluster along tidal creeks, estuarine boundaries, and coastal margins where turbidity and chlorophyll signals co-occur, indicating reduced flushing capacity and elevated environmental stress.

- Temporal aggregation of annual composites reduces atmospheric noise and short-term variability, producing stable and physically consistent spatial patterns suitable for scalable coastal water quality monitoring and environmental assessment.
***
### Technical Contributions
This project was developed collaboratively, with shared responsibility across data engineering, geospatial processing, and analytical system design.

- **Grace Nwachukwu**
  - Developed core geospatial processing functions and analysis notebooks for water quality extraction, visualisation, and spatial mapping of Sentinel-2–derived indices.
  
- **Kalu Okigwe**
  - Developed environmental data processing functions and analysis notebooks for sea surface temperature (SST) and precipitation datasets, including data cleaning, aggregation, and visualisation workflows.

- **Joint**
  - Designed and implemented the end-to-end geospatial analytics pipeline integrating satellite-derived and environmental datasets.
  - Built the reproducible computational environment using Docker and Conda for portability and deployment consistency.
  - Developed analytical workflows for correlation analysis (Pearson), error quantification (RMSE), and dimensionality reduction (PCA).
  - Coordinated Git/GitHub workflow, documentation structure, and version-controlled project organisation.
***

## References
- Griffiths, P., Nendel, C., & Hostert, P. (2019). Intra-annual reflectance composites from Sentinel-2 and Landsat for national-scale crop and land cover mapping. Remote sensing of environment, 220, 135-151.
- Ju, J., Zhou, Q., Freitag, B., Roy, D. P., Zhang, H. K., Sridhar, M., ... & Neigh, C. S. (2025). The Harmonized Landsat and Sentinel-2 version 2.0 surface reflectance dataset. Remote Sensing of Environment, 324, 114723.
-  [ESA Sentinel-2 Documentation](https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html)
***

## Citation

If you use this project in your research or publications, please cite it as:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18148374.svg)](https://doi.org/10.5281/zenodo.18148374)

Nwachukwu, G., & Okigwe, K. (2026). *Assessing Water Quality Dynamics and Environmental Drivers in Tampa Bay, Florida Using Remote Sensing* [Software]. Zenodo. https://doi.org/10.5281/zenodo.18148374

