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
    micromamba install -n dwa_env -c conda-forge vina -y && \
    micromamba clean --all --yes

# Now copy code
COPY src/ /app/src/

# Activate environment
ENV MAMBA_DOCKERFILE_ACTIVATE=1
ENV CONDA_DEFAULT_ENV=dwa_env
ENV PATH=/opt/conda/envs/dwa_env/bin:$PATH

# Clone additional repos
RUN git clone --single-branch --branch develop https://github.com/ToolProof/molscrub.git && \
    micromamba run -n dwa_env pip install --use-pep517 -e molscrub

RUN git clone https://github.com/ToolProof/geostd.git

RUN micromamba run -n dwa_env pip install --no-cache-dir --force-reinstall \
  "numpy<1.24" \
  git+https://github.com/forlilab/Meeko.git

EXPOSE 8080

CMD ["micromamba", "run", "-n", "dwa_env", "python", "-m", "src.main"]
