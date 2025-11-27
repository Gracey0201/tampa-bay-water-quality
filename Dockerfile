# Base image with Miniconda
FROM continuumio/miniconda3:24.7.1-0

# Copy environment.yml and create the Conda environment
COPY environment.yml .
RUN conda env create -f environment.yml

# Activate the Conda environment
RUN echo "conda activate geog313-final-project" >> ~/.bashrc
ENV PATH="$PATH:/opt/conda/envs/geog313-final-project/bin"

# Create a non-root user for safer execution
RUN useradd -m jupyteruser
USER jupyteruser
WORKDIR /home/jupyteruser

# Expose ports for JupyterLab and Dask Dashboard
EXPOSE 8888
EXPOSE 8787

# Start JupyterLab by default
CMD ["jupyter", "lab", "--ip=0.0.0.0"]
