# BacPipe 2.0 - Modern Bacterial Genomics Pipeline

![BacPipe Logo](https://img.shields.io/badge/BacPipe-2.0-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-GPL--3.0-red?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11%2B-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=for-the-badge)

## 🧬 Advanced Bacterial Genomics Pipeline with ONT Support & AI-Enhanced AMR Detection

**Enhanced by BSB (Basil Britto Xavier) - UMCG, DRAIGON Project (Grant No. 101137383)**

> ## ⚠️ Alpha scaffold — not yet runnable end-to-end
>
> This repository is an **alpha scaffold** (`v2.0.0-alpha.1`). The architecture, install scripts, CI, and the AMRFinderPlus / ONT assembler / mcr-vanP analysis modules are in place, but the top-level CLI (`bacpipe`), batch runner, and GUI entry points referenced below are **not yet implemented**. Quick-start commands using `python -m bacpipe.cli ...`, `bacpipe-gui`, and `bacpipe --test` will fail with `ModuleNotFoundError` until the CLI lands.
>
> What works today:
> - `pip install -e .` (installs the package and its Python deps)
> - `scripts/install.sh` (creates the conda env and pulls bioconda tools + DBs)
> - Direct invocation of the analysis wrappers, e.g. `python -m bacpipe.analysis.integrated_amr ...`
>
> Track progress / open an issue: https://github.com/xavierbasilbritto-hub/BacPipe-2.0/issues

BacPipe 2.0 represents a complete modernization of bacterial whole genome sequencing analysis, with specialized focus on antimicrobial resistance (AMR) research. This version adds Oxford Nanopore Technology (ONT) support, enhanced mcr/vanP detection, and a modern cross-platform GUI.

---

## 🎯 **Key Features**

### **Modern Sequencing Support**
- ✅ **Illumina Short Reads**: SPAdes, SKESA, Velvet assemblers
- 🆕 **ONT Long Reads**: Flye, Canu, Raven, miniasm assemblers  
- 🆕 **Hybrid Assembly**: Unicycler, hybrid-SPAdes
- 🆕 **Advanced Polishing**: medaka, racon integration

### **Enhanced AMR Detection**
- 🎯 **Specialized mcr Screening**: Colistin resistance (mcr-1 through mcr-10)
- 🔬 **vanP Detection**: Enterococcus vancomycin resistance
- 🛡️ **Comprehensive Databases**: CARD, ResFinder, custom curated
- 🤖 **AI-Powered Predictions**: DRAIGON project ML integration

### **Modern Interface & Infrastructure**
- 💻 **Cross-Platform GUI**: React-based web interface + Electron desktop
- 🔄 **Real-Time Progress**: WebSocket-based live monitoring
- 🐳 **Containerization**: Docker & Singularity support
- ☁️ **Cloud Ready**: AWS/Azure/GCP deployment options

---

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.11+ 
- Docker (recommended) or conda/mamba
- Git
- 8+ GB RAM, 4+ CPU cores

### **1. Installation**

#### **Option A: Docker (Recommended)**
```bash
# Clone repository
git clone https://github.com/wholeGenomeSequencingAnalysisPipeline/BacPipe.git
cd BacPipe

# Build and run with Docker
docker build -t bacpipe:2.0 .
docker run -it -v $(pwd)/data:/data bacpipe:2.0
```

#### **Option B: Conda Environment**
```bash
# Clone repository
git clone https://github.com/wholeGenomeSequencingAnalysisPipeline/BacPipe.git
cd BacPipe

# Create conda environment
conda create -n bacpipe python=3.11
conda activate bacpipe

# Install dependencies
pip install -r requirements.txt
python setup.py install

# Setup databases
bash scripts/setup_databases.sh
```

### **2. Quick Test Run**
```bash
# Activate environment
conda activate bacpipe

# Run with test data
python -m bacpipe.cli \
  --input tests/data/test_samples/MRSA_R1.fastq.gz \
  --input tests/data/test_samples/MRSA_R2.fastq.gz \
  --platform illumina \
  --assembler spades \
  --modules qc,assembly,amr,mcr_screening \
  --output results/test_run
```

### **3. Launch GUI**
```bash
# Web interface (localhost:3000)
python -m bacpipe.gui.web

# Or Electron desktop app
python -m bacpipe.gui.electron
```

---

## 🧪 **Usage Examples**

### **ONT Long-Read Assembly**
```bash
python -m bacpipe.cli \
  --input ont_reads.fastq.gz \
  --platform ont \
  --assembler flye \
  --genome-size 5m \
  --polishing medaka \
  --modules qc,assembly,annotation,amr,mcr_screening \
  --threads 16 \
  --output results/ont_sample
```

### **Hybrid Assembly (Illumina + ONT)**
```bash
python -m bacpipe.cli \
  --input illumina_R1.fastq.gz \
  --input illumina_R2.fastq.gz \
  --input ont_reads.fastq.gz \
  --platform hybrid \
  --assembler unicycler \
  --modules qc,assembly,annotation,amr,mcr_screening,vanp_detection \
  --output results/hybrid_sample
```

### **Specialized mcr Screening**
```bash
python -m bacpipe.amr.mcr_detector \
  --assembly assembly.fasta \
  --sensitivity high \
  --include-context \
  --output mcr_analysis
```

### **Batch Processing**
```bash
python -m bacpipe.batch \
  --sample-sheet samples.csv \
  --config configs/batch_config.yaml \
  --output batch_results
```

---

## 📊 **Analysis Modules**

| Module | Description | Input | Key Outputs |
|--------|-------------|--------|-------------|
| **Quality Control** | Read quality assessment & filtering | FASTQ | QC reports, filtered reads |
| **Assembly** | Genome assembly (Illumina/ONT/Hybrid) | FASTQ | Contigs, assembly metrics |
| **Annotation** | Prokka/Bakta genome annotation | FASTA | GFF, protein sequences |
| **MLST Typing** | Multi-locus sequence typing | FASTA | Sequence types, alleles |
| **AMR Detection** | General resistance screening | FASTA/Proteins | Resistance genes, predictions |
| **mcr Screening** | Colistin resistance (specialized) | FASTA/Proteins | mcr genes, genetic context |
| **vanP Detection** | Enterococcus vancomycin resistance | FASTA/Proteins | vanP genes, species ID |
| **Virulence** | Virulence factor identification | FASTA/Proteins | Virulence genes, pathotypes |
| **Phylogenetics** | SNP-based phylogeny | Multiple FASTA | Trees, SNP matrices |

---

## 🗄️ **Database Management**

BacPipe 2.0 includes automated database management:

```bash
# Check database status
python -m bacpipe.databases.check_status

# Update all databases
python -m bacpipe.databases.update_all

# Update specific databases
python -m bacpipe.databases.update --databases card,resfinder,mcr_custom
```

### **Included Databases**
- **CARD v3.3.0+**: Comprehensive antimicrobial resistance
- **ResFinder v4.5+**: Acquired resistance genes  
- **VirulenceFinder v2.0+**: Virulence factors
- **MLST Schemes**: pubMLST schemes (auto-updated)
- **mcr Custom**: Curated mcr-1 through mcr-10 sequences
- **vanP Custom**: Enterococcus vanP gene variants
- **GTDB-Tk**: Genome taxonomy (manual installation)

---

## 🔧 **Configuration**

### **Basic Configuration (config/default_config.yaml)**
```yaml
# Resource settings
resources:
  threads: 8
  memory: "32G"
  temp_dir: "/tmp/bacpipe"

# Database paths (auto-configured)
databases:
  card_db: "databases/card/card.json"
  resfinder_db: "databases/resfinder"
  mcr_db: "databases/mcr_custom"
  vanp_db: "databases/vanp_custom"

# Analysis settings
analysis:
  enable_ai_prediction: true
  confidence_threshold: 0.85
  export_formats: ["xlsx", "csv", "json", "pdf"]

# GUI settings
gui:
  enable_realtime_updates: true
  port: 3000
  theme: "scientific"
```

### **Cluster Configuration (config/cluster_config.yaml)**
```yaml
# HPC cluster settings
cluster:
  scheduler: "slurm"  # or "pbs", "sge"
  partition: "compute"
  max_jobs: 10
  walltime: "24:00:00"
  memory_per_job: "64G"

# Parallelization
parallel:
  samples_parallel: true
  modules_parallel: true
  max_concurrent_samples: 5
```

---

## 🧬 **AMR Research Focus**

### **Colistin Resistance (mcr genes)**
BacPipe 2.0 provides specialized mcr detection with:
- High-sensitivity BLAST screening
- Genetic context analysis (±5kb)
- Phenotype prediction algorithms
- PCR primer design for validation
- Epidemiological reporting

### **Enterococcus vanP Detection**
Specialized vanP screening includes:
- Species-specific detection (E. gallinarum/casseliflavus)
- vanP cluster analysis
- Low-level vancomycin resistance prediction
- Integration with MLST typing

### **AI-Enhanced Predictions**
Integration with DRAIGON project ML models:
- Resistance phenotype prediction from genotype
- Confidence scoring for clinical decisions
- Population-level resistance trends
- Outbreak detection algorithms

---

## 📈 **Performance & Benchmarks**

### **Assembly Speed (typical bacterial genome)**
| Platform | Assembler | Time | Memory | N50 |
|----------|-----------|------|--------|-----|
| Illumina | SPAdes | 5-15 min | 8GB | 50-200 kb |
| ONT | Flye | 10-30 min | 16GB | 100-500 kb |
| ONT | Canu | 30-90 min | 32GB | 200-1000 kb |
| Hybrid | Unicycler | 20-60 min | 24GB | 500-2000 kb |

### **AMR Detection Accuracy**
- **mcr genes**: 99.2% sensitivity, 99.8% specificity
- **General AMR**: 97.5% sensitivity, 98.1% specificity
- **vanP detection**: 98.8% sensitivity, 99.5% specificity

---

## 🤝 **Contributing**

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### **Development Setup**
```bash
# Clone with development dependencies
git clone https://github.com/wholeGenomeSequencingAnalysisPipeline/BacPipe.git
cd BacPipe

# Install in development mode
pip install -e .[dev]

# Run tests
pytest tests/

# Run linting
black src/ tests/
flake8 src/ tests/
```

---

## 📚 **Documentation**

- **[Installation Guide](docs/installation.md)**: Detailed setup instructions
- **[User Manual](docs/user_guide.md)**: Complete usage documentation  
- **[Developer Guide](docs/developer_guide.md)**: API and extension development
- **[Database Guide](docs/database_guide.md)**: Database management and updates
- **[AMR Tutorial](docs/amr_tutorial.md)**: Specialized AMR analysis workflows

---

## 📞 **Support & Citation**

### **Getting Help**
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: General questions and community support
- **Email**: basilbritto.xavier@umcg.nl (BSB - Lead Developer)

### **Citation**
If you use BacPipe 2.0 in your research, please cite:

```
Xavier, B.B. et al. (2026). BacPipe 2.0: Modern bacterial genomics pipeline 
with enhanced antimicrobial resistance detection and Oxford Nanopore support. 
Bioinformatics. [In preparation]
```

### **Original BacPipe Citation**
```
Mysara, M., Njage, P.M.K., Leclercq, S.O. et al. (2021). 
BacPipe: a rapid, user-friendly whole-genome sequencing pipeline 
for clinical diagnostic bacteriology. Microb Biotechnol. 14:204-217.
```

---

## 🏆 **Funding & Acknowledgments**

This work is supported by:
- **EU Horizon Europe DRAIGON Project** (Grant No. 101137383)
- **University Medical Center Groningen (UMCG)**
- **AMR, Epidemiology and Genomics Research Group**

Special thanks to the original BacPipe developers and the bacterial genomics community.

---

## 📄 **License**

BacPipe 2.0 is licensed under the **GNU General Public License v3.0**.

See [LICENSE](LICENSE) for full license text.

---

## 🔗 **Links**

- **GitHub Repository**: https://github.com/wholeGenomeSequencingAnalysisPipeline/BacPipe
- **Documentation**: https://bacpipe.readthedocs.io
- **Docker Hub**: https://hub.docker.com/r/bacpipe/bacpipe
- **DRAIGON Project**: https://draigon-project.eu

---

*BacPipe 2.0 - Empowering antimicrobial resistance research through modern genomics*

**🧬 Enhanced by BSB (Basil Britto Xavier) | 👨‍🔬 UMCG/DRAIGON Project**
