#!/usr/bin/env bash
# BacPipe 2.0 — installation script
# Basil Britto Xavier — DRAIGON Project
#
# Usage:
#   bash scripts/install.sh           # full install (conda env + tools + DBs)
#   bash scripts/install.sh --no-db   # skip database downloads
#   bash scripts/install.sh --env-only

set -euo pipefail

ENV_NAME="${BACPIPE_ENV:-bacpipe2}"
SKIP_DB=0
ENV_ONLY=0

for arg in "$@"; do
    case "$arg" in
        --no-db)    SKIP_DB=1 ;;
        --env-only) ENV_ONLY=1 ;;
        -h|--help)
            sed -n '2,12p' "$0"; exit 0 ;;
    esac
done

echo "=========================================="
echo " BacPipe 2.0 installer"
echo " Conda env: ${ENV_NAME}"
echo "=========================================="

# --- 1. Conda check --------------------------------------------------------
if ! command -v conda >/dev/null 2>&1; then
    echo "ERROR: conda not found. Install Miniforge / Miniconda first:"
    echo "       https://github.com/conda-forge/miniforge"
    exit 1
fi

# --- 2. Create / update env ------------------------------------------------
if conda env list | grep -qE "^\s*${ENV_NAME}\s"; then
    echo "[*] Environment '${ENV_NAME}' already exists — updating."
else
    echo "[*] Creating conda env '${ENV_NAME}' (python 3.11)"
    conda create -y -n "${ENV_NAME}" python=3.11
fi

# Activate
# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"

# --- 3. Bioinformatics tools (bioconda) -----------------------------------
echo "[*] Installing bioinformatics tools from bioconda..."
conda install -y -c bioconda -c conda-forge \
    ncbi-amrfinderplus \
    spades \
    skesa \
    flye \
    raven-assembler \
    miniasm \
    minimap2 \
    unicycler \
    fastp \
    filtlong \
    nanoplot \
    medaka \
    racon \
    prokka \
    bakta \
    mlst \
    blast \
    hmmer \
    quast \
    parsnp \
    iqtree \
    samtools

# Canu can be heavy; install only if not already present
if ! command -v canu >/dev/null 2>&1; then
    conda install -y -c bioconda canu || \
        echo "[!] canu install skipped (not critical — Flye/Raven cover most cases)"
fi

# --- 4. Python deps --------------------------------------------------------
echo "[*] Installing Python dependencies..."
pip install --upgrade pip
if [[ -f requirements.txt ]]; then
    pip install -r requirements.txt
fi
pip install -e . || echo "[!] 'pip install -e .' skipped (no setup.py yet)"

# --- 5. Sanity check -------------------------------------------------------
echo "[*] Verifying tool installation:"
for tool in amrfinder spades.py flye unicycler prokka mlst blastn fastp filtlong; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf "    [OK]   %-18s %s\n" "$tool" "$($tool --version 2>&1 | head -1 || true)"
    else
        printf "    [MISS] %s\n" "$tool"
    fi
done

if [[ $ENV_ONLY -eq 1 ]]; then
    echo "[*] --env-only specified, stopping here."
    exit 0
fi

# --- 6. Databases ----------------------------------------------------------
if [[ $SKIP_DB -eq 1 ]]; then
    echo "[*] --no-db specified, skipping database downloads."
    exit 0
fi

DB_ROOT="${BACPIPE_DB:-databases}"
mkdir -p "${DB_ROOT}"

echo "[*] Downloading AMRFinderPlus database..."
amrfinder -u -d "${DB_ROOT}/amrfinderplus" || \
    echo "[!] AMRFinderPlus DB download failed — re-run later with: amrfinder -u -d ${DB_ROOT}/amrfinderplus"

echo "[*] Updating MLST schemes (pubMLST)..."
mlst --update 2>/dev/null || echo "[!] mlst --update skipped (will use bundled schemes)"

echo "[*] CARD database..."
mkdir -p "${DB_ROOT}/card"
if command -v wget >/dev/null 2>&1; then
    wget -q -O "${DB_ROOT}/card/card-data.tar.bz2" \
        https://card.mcmaster.ca/latest/data && \
        tar -xjf "${DB_ROOT}/card/card-data.tar.bz2" -C "${DB_ROOT}/card/" && \
        echo "    CARD downloaded." || \
        echo "[!] CARD download failed — fetch manually from https://card.mcmaster.ca/latest/data"
fi

echo "[*] ResFinder + VirulenceFinder (git)..."
for repo in resfinder_db virulencefinder_db; do
    target="${DB_ROOT}/${repo%_db}"
    if [[ -d "${target}/.git" ]]; then
        git -C "${target}" pull --quiet || true
    else
        git clone --depth 1 "https://bitbucket.org/genomicepidemiology/${repo}.git" "${target}" \
            2>/dev/null || echo "[!] git clone of ${repo} failed (will retry next install)"
    fi
done

echo
echo "=========================================="
echo " BacPipe 2.0 installation complete!"
echo "=========================================="
echo "Activate the environment:"
echo "    conda activate ${ENV_NAME}"
echo
echo "Test AMRFinderPlus:"
echo "    amrfinder -V"
echo
echo "Run integrated AMR analysis on an assembly:"
echo "    python -m bacpipe.analysis.integrated_amr \\"
echo "        --sample-id TEST \\"
echo "        --assembly path/to/assembly.fasta \\"
echo "        --species 'Escherichia coli' \\"
echo "        --amrfinder-db ${DB_ROOT}/amrfinderplus"
echo
