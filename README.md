# Assessing Water Quality Dynamics and Environmental Drivers in Tampa Bay, Florida Using Remote Sensing

**Authors:** Grace Nwachukwu and Kalu Okigwe  
**Course:** GEOG 313 – Final Project  

***

## Project Overview

This project builds a modular, reproducible pipeline to link satellite‑derived water quality indices with large‑scale environmental drivers in Tampa Bay, Florida. It combines custom data access functions, statistical analysis, and robust error handling to evaluate how sea surface temperature (SST) co‑varies with Sentinel‑2–based water quality indicators (NDWI, NDTI, NDCI) over 2019–2022.[1]

All analysis is implemented in Python using `xarray`, `dask`, `stackstac`, and STAC APIs, and is fully containerized via a conda environment and Docker image for reproducibility.

***

## Repository Structure

- `Notebook.ipynb`  
  Main Jupyter notebook that orchestrates the full workflow: calls functions, runs diagnostics, computes indices, joins with SST, and performs correlation and PCA analysis. 

- `env_function.py`  
  - `environmental_variables(...)`: Fetches SST from a public Zarr archive and precipitation metadata from the Planetary Computer STAC API for a given bounding box and time window.  
  - Returns SST as an `xarray.DataArray` (monthly mean, spatially averaged) and precipitation as a list of STAC `Item` objects or `None` if requests fail.[1]

- `analysis.py`  
  - `load_env_timeseries(...)`: Wrapper around `environmental_variables` to get monthly SST.  
  - `join_indices_and_env(...)`: Merges Grace’s NDWI/NDTI/NDCI with Kalu’s SST into a single pandas DataFrame by time.  
  - `compute_correlations_and_rmse(...)`: Computes Pearson correlations between indices and SST and standardized RMSE after z‑scoring.  
  - `add_season_column(...)`, `seasonal_means(...)`: Adds a season label and aggregates NDWI, NDTI, NDCI, and SST to Winter/Spring/Summer/Fall means.  
  - `run_pca(...)`: Runs PCA on standardized NDWI, NDTI, NDCI, and SST, returning loadings, explained variance, variables, and PCs.  
  - `plot_monthly_timeseries(...)`: Dual‑axis plot of monthly NDTI/NDCI and SST.[2][3]

- `grace_functions.py`  
  - `compute_wqi_indices(...)`: Queries Sentinel‑2 L2A via Earth Search STAC, filters scenes by cloud cover, stacks bands with `stackstac`, computes NDWI/NDTI/NDCI, applies SCL‑based water masking, and aggregates to time series, rolling means, and monthly climatologies with detailed diagnostics for selected scenes.  
  - `compute_indices(...)`: Backwards‑compatible alias calling `compute_wqi_indices` so existing imports in `analysis.py` continue to work.[4][1]

- `environment.yml`  
  Conda environment specification:

  - `name: geog313-final-project`  
  - Core packages: `python=3.11`, `jupyterlab`, `pystac-client`, `stackstac`, `dask`, `distributed`, `xarray`, `rasterio`, `geopandas`, `scikit-learn`, `zarr`, `s3fs`, etc.  
  - `pip` extras: `planetary-computer`, `pystac-client`, `stackstac`.[1]

- `Dockerfile`  
  Docker configuration based on `continuumio/miniconda3:24.7.1-0`:

  - Builds the `geog313-final-project` conda environment from `environment.yml`.  
  - Activates the environment via `.bashrc` and `PATH`.  
  - Creates non‑root user `jupyteruser` and sets `/home/jupyteruser` as `WORKDIR`.  
  - Exposes ports `8888` (JupyterLab) and `8787` (Dask dashboard).  
  - Starts JupyterLab with `CMD ["jupyter", "lab", "--ip=0.0.0.0"]`.[1]

- `kalu_environmental.csv`, `kalu_sst_data.csv`, `kalu_precip_data.csv`  
  Exported SST and environmental results (optional artifacts).

- `results/`  
  Folder for derived outputs (plots, tables, metrics).

***

## Methods Summary

### Environmental data (env_function.py)

`environmental_variables` provides a generic interface to environmental drivers:

- Opens a public SST Zarr store with `xarray.open_zarr`, selecting the correct variable name (`analysed_sst` or `sst`) depending on the product.  
- Subsets SST in space (Tampa Bay bounding box) and time, converts from Kelvin to Celsius when needed, computes spatial means, and resamples to monthly means.  
- Uses the Planetary Computer STAC API to search MRMS precipitation items over the same bbox/time window, handling time ranges year‑by‑year to avoid long requests and wrapping calls in `try/except` to catch timeouts.[1]

The function returns a dictionary with SST as an `xarray.DataArray` and precipitation as a list of STAC `Item`s or `None`.

### Water quality indices (grace_functions.py)

`compute_wqi_indices` implements the Sentinel‑2 WQI pipeline:

- Queries Sentinel‑2 L2A scenes via Earth Search STAC for a Tampa Bay bounding box and date range.  
- Filters scenes by cloud cover threshold (e.g., `< 20%`) before stacking.  
- Uses `stackstac.stack` to build a lazy 4‑D array over bands `green`, `red`, `nir`, `rededge1`, and `scl`.  
- Computes NDWI, NDTI, and NDCI via a normalized difference function and applies an SCL‑based water mask (classes 5–6) to focus on water pixels.  
- Aggregates indices to spatial means/medians per time step, builds a dataset of NDWI/NDTI/NDCI statistics, and converts to a pandas DataFrame with a datetime index.  
- Computes rolling means over a user‑defined window and monthly climatologies for all indices.[4][1]

A rich diagnostics loop prints thumbnails, cloud metadata, SCL cloud/water ratios, and NDWI “sanity checks” for the first few scenes. This was hardened with explicit `scene = None` guards and `try/except` around `sel(time=...)` and SCL/NDWI calculations to avoid crashes when time coordinates are duplicated or non‑unique.[5][6]

### Joining indices and environment (analysis.py)

The analysis module links WQI indices to SST:

1. **Load SST time series**

   ```python
   env_da = load_env_timeseries(bbox, start_date, end_date)
   ```

   This returns a monthly SST series (`sst_c`) over Tampa Bay or raises a clear error if SST cannot be retrieved.

2. **Compute WQI indices**

   ```python
   wqi_df, wqi_rolling, wqi_monthly = compute_wqi_indices(
       bbox=bbox,
       start_date=start_date,
       end_date=end_date,
       export_csv=False,
       anomaly_detection=True,
       rolling_window=3,
   )
   ```

3. **Join indices and SST**

   ```python
   df = join_indices_and_env(wqi_df, env_da)
   ```

   Produces a pandas DataFrame with columns like `NDWI`, `NDTI`, `NDCI`, and `sst_c` on a common time index.

4. **Correlations and standardized RMSE**

   ```python
   stats = compute_correlations_and_rmse(df)
   ```

   - Computes Pearson correlations `corr_NDTI_SST` and `corr_NDCI_SST`.  
   - Z‑scores `NDTI`, `NDCI`, and `sst_c` and computes RMSE between z‑scored indices and z‑scored SST to quantify mismatch on a common scale.[2]

5. **Seasonal means and PCA**

   - `seasonal_means(df)` groups by derived season (Winter, Spring, Summer, Fall) and computes average NDWI/NDTI/NDCI/SST.  
   - `run_pca(df, n_components=2)` standardizes NDWI, NDTI, NDCI, and SST, runs PCA, and returns loadings, explained variance ratios, variable names, and PC scores for interpretation.[3]

6. **Visualization**

   - `plot_monthly_timeseries(df)` draws a dual‑axis plot with NDTI/NDCI on the left y‑axis and SST on the right y‑axis, supporting visual comparison of temporal co‑variability.

***

## Error Handling and Limitations

Two key external issues were observed:

1. **Duplicate / non‑unique time coordinates**  
   Selecting by time (`sel(time=dt, method="nearest")`) can raise “Reindexing only valid with uniquely valued Index objects” when time coordinates are duplicated. The diagnostics in `compute_wqi_indices` were updated to catch these errors and either skip SCL/NDWI diagnostics for problematic timestamps or print a clear message instead of failing.[6][5]

2. **Remote COG access errors (CURL “Recv failure”)**  
   During `ds_ts.compute()`, some Sentinel‑2 COG reads through `stackstac` fail with `RasterioIOError: CURL error: Recv failure: Connection reset by peer`. These are transient remote host/network issues rather than logic bugs. To mitigate them, the code and documentation recommend reducing `max_items`, narrowing the time window, re‑running cells, and optionally wrapping `.compute()` in a `try/except` block to convert hard failures into warnings.[7][1]

Despite these measures, full reproducibility still depends on external cloud services (Earth Search, Sentinel‑COGs, Planetary Computer) being available and responsive at runtime.

***

## How to Run the Project

### 1. Clone the repository

```bash
git clone https://github.com/Gracey0201/geog313-final-project.git
cd geog313-final-project
```

### 2. Create and activate the conda environment

```bash
conda env create -f environment.yml
conda activate geog313-final-project
```

### 3. Option A – Run locally with JupyterLab

```bash
jupyter lab
```

Then open `Notebook.ipynb`, ensure the kernel is set to `geog313-final-project`, and run all cells in order.

### 4. Option B – Run using Docker

1. Build the image:

```bash
docker build -t geog313-final-project .
```

2. Run the container:

```bash
docker run -it --rm \
  -p 8888:8888 -p 8787:8787 \
  -v $(pwd):/home/jupyteruser/project \
  geog313-final-project
```

3. Copy the JupyterLab URL from the container logs into your browser and open `project/Notebook.ipynb`.

***

## Team Roles

- **Grace Nwachukwu**
  - Developed WQI functions and Sentinel‑2 processing (NDWI, NDTI, NDCI).  
  - Implemented STAC queries, diagnostics, and mapping‑ready outputs.

- **Kalu Okigwe**
  - Developed environmental data functions for SST (and precipitation).  
  - Implemented join, correlation, RMSE, seasonal means, PCA, and time‑series plots.

- **Joint**
  - Designed the integrated pipeline, Docker/conda setup, and reproducible notebook.  
  - Wrote documentation and coordinated Git/GitHub workflow.



## PROJECT SUMMARY

This project builds a modular, reproducible pipeline to link satellite‑derived water quality indices with large‑scale environmental drivers in Tampa Bay. It combines custom data access functions, statistical analysis, and robust error handling to evaluate how sea surface temperature co‑varies with Sentinel‑2 water quality indicators.

## Environmental data function (env_function.py)

The `environmental_variables` function provides a generic interface to fetch sea surface temperature (SST) from a public Zarr archive and precipitation metadata from the Planetary Computer STAC API for any bounding box and time window. It dynamically handles different SST products by switching between `analysed_sst` and `sst` variable names and, when needed, converts Kelvin to Celsius before aggregating to monthly, spatially averaged time series. SST is returned as an `xarray.DataArray` with a monthly `time` coordinate, while precipitation is returned as a list of STAC `Item` objects or `None` if the STAC search fails or times out, which is explicitly handled in `try/except` blocks.

## Analysis module (analysis.py)

The analysis module wraps the environmental function and Grace’s indices into a coherent workflow. `load_env_timeseries` calls `environmental_variables` and extracts a monthly SST series over Tampa Bay, raising a clear error if SST cannot be retrieved. `join_indices_and_env` merges Grace’s monthly NDWI, NDTI, and NDCI with Kalu’s SST into a single pandas DataFrame keyed on a shared time coordinate, which is then used for statistical analysis. `compute_correlations_and_rmse` computes Pearson correlations between each index and SST and standardized RMSE (after z‑scoring) to place all variables on comparable scales, while `seasonal_means` aggregates NDWI, NDTI, NDCI, and SST into climatological means for Winter, Spring, Summer, and Fall using a derived `season` column. [web:39][web:37]

## PCA and visualization

The `run_pca` function performs principal component analysis on standardized NDWI, NDTI, NDCI, and SST, returning PCA loadings, explained variance ratios, variable names, and principal component scores. This allows quantifying the dominant joint modes of variability between water quality indices and SST and identifying which variables load most strongly on each component. The `plot_monthly_timeseries` helper produces a dual‑axis plot of monthly NDTI/NDCI and SST, enabling visual inspection of co‑variability and potential lagged relationships between surface temperature and optically derived indices in Tampa Bay.

## Water quality index function (grace_functions.py)

Grace’s function, `compute_wqi_indices`, was adapted into a robust index engine that queries Sentinel‑2 L2A via the Earth Search STAC API, filters scenes by cloud cover, and computes NDWI, NDTI, and NDCI using `stackstac` over the Tampa Bay bounding box. It includes a rich diagnostics loop for the first few scenes, printing thumbnails, cloud metadata, Scene Classification Layer (SCL) cloud and water fractions, and “sanity check” NDWI values; this loop was hardened by guarding against duplicate or non‑unique time indices and catching selection errors so that scene diagnostics never crash the main computation. The function produces time‑indexed NDWI/NDTI/NDCI mean and median series, rolling smoothed versions, and monthly climatologies, and a backwards‑compatible `compute_indices` alias ensures existing imports in `analysis.py` continue to work.

## Error handling and network robustness

While running the pipeline, two external issues were identified: (1) xarray’s “Reindexing only valid with uniquely valued Index objects” when selecting scenes by time, and (2) `RasterioIOError` / CURL “Recv failure: Connection reset by peer” when reading remote Sentinel‑2 COG tiles through `stackstac`. The first was mitigated by explicitly catching selection errors and skipping SCL/NDWI diagnostics if `scene` could not be safely defined, while the second was documented as a transient network/remote host problem and addressed by recommending smaller `max_items`, narrower time windows, reruns, and wrapping the final `.compute()` in a `try/except` to convert fatal errors into warnings. This treatment aligns with community reports of similar CURL and reindexing errors in remote EO workflows and demonstrates a clear understanding of the limits and behavior of cloud‑hosted COG access.
