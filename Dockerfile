# Use micromamba base image
FROM mambaorg/micromamba:latest

# Set workdir
WORKDIR /app

# Copy early so dependencies can install
COPY environment.yml /app/

# 🔧 Install git early for pip git+ installs to work
USER root
RUN apt-get update && apt-get install -y git build-essential

# Create conda environment
RUN micromamba env create -f /app/environment.yml && \
    micromamba install -n adapter_autodock_env -c conda-forge vina -y && \
    micromamba run -n adapter_autodock_env pip install --force-reinstall --no-cache-dir git+https://github.com/ToolProof/helpers_py.git && \
    micromamba clean --all --yes

# Now copy code
COPY src/ /app/src/

# Activate environment
ENV MAMBA_DOCKERFILE_ACTIVATE=1
ENV CONDA_DEFAULT_ENV=adapter_autodock_env
ENV PATH=/opt/conda/envs/adapter_autodock_env/bin:$PATH

# Clone additional repos
RUN git clone --single-branch --branch develop https://github.com/ToolProof/molscrub.git && \
    micromamba run -n adapter_autodock_env pip install --use-pep517 -e molscrub

RUN git clone https://github.com/ToolProof/geostd.git

EXPOSE 8080

CMD ["micromamba", "run", "-n", "adapter_autodock_env", "python", "-m", "src.main"]
