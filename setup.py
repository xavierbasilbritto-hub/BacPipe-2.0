#!/usr/bin/env python3
"""
BacPipe 2.0 - Modern Bacterial Genomics Pipeline
Setup script for Python package installation
BSB (Basil Britto Xavier) - UMCG/DRAIGON Project
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages

# Ensure Python 3.11+
if sys.version_info < (3, 11):
    sys.exit("BacPipe 2.0 requires Python 3.11 or higher")

# Read version from __init__.py
def get_version():
    version_file = Path(__file__).parent / "src" / "bacpipe" / "__init__.py"
    if version_file.exists():
        with open(version_file, 'r') as f:
            for line in f:
                if line.startswith('__version__'):
                    return line.split('"')[1]
    return "2.0.0"

# Read README for long description
def get_long_description():
    readme_file = Path(__file__).parent / "README.md"
    if readme_file.exists():
        with open(readme_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "BacPipe 2.0 - Modern Bacterial Genomics Pipeline"

# Read requirements
def get_requirements():
    requirements_file = Path(__file__).parent / "requirements.txt"
    requirements = []
    if requirements_file.exists():
        with open(requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('python'):
                    # Remove extra dependencies markers for basic install
                    if ';extra==' not in line:
                        requirements.append(line)
    return requirements

setup(
    # Basic package information
    name="bacpipe",
    version=get_version(),
    description="Modern Bacterial Genomics Pipeline with ONT Support & AI-Enhanced AMR Detection",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    
    # Author information
    author="BSB (Basil Britto Xavier)",
    author_email="basilbritto.xavier@umcg.nl",
    maintainer="BSB (Basil Britto Xavier)",
    maintainer_email="basilbritto.xavier@umcg.nl",
    
    # Project URLs
    url="https://github.com/xavierbasilbritto-hub/BacPipe-2.0",
    project_urls={
        "Source": "https://github.com/xavierbasilbritto-hub/BacPipe-2.0",
        "Tracker": "https://github.com/xavierbasilbritto-hub/BacPipe-2.0/issues",
        "DRAIGON Project": "https://draigon-project.eu"
    },
    
    # Package discovery
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # Include non-Python files
    include_package_data=True,
    package_data={
        "bacpipe": [
            "data/*",
            "configs/*",
            "gui/web/build/*",
            "databases/*/metadata.json"
        ]
    },
    
    # Dependencies
    python_requires=">=3.11",
    install_requires=get_requirements(),
    
    # Optional dependencies
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0", 
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.4.0",
            "pre-commit>=3.3.0"
        ],
        "ai": [
            "torch>=2.0.0",
            "transformers>=4.30.0",
            "scikit-bio>=0.5.8"
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0"
        ],
        "gui": [
            "streamlit>=1.25.0",
            "plotly>=5.15.0",
            "dash>=2.10.0"
        ]
    },
    
    # Console scripts. Only modules that actually exist today are wired up;
    # specialised mcr / vanP CLIs will be added when those modules land.
    entry_points={
        "console_scripts": [
            "bacpipe=bacpipe.cli:main",
            "bacpipe-gui=bacpipe.gui.web:main",
        ]
    },
    
    # Classification
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Environment :: Web Environment"
    ],
    
    # Keywords for discovery
    keywords=[
        "bioinformatics", 
        "genomics", 
        "bacterial-genomics",
        "whole-genome-sequencing",
        "antimicrobial-resistance", 
        "amr",
        "oxford-nanopore",
        "ont",
        "illumina",
        "mcr-genes",
        "colistin-resistance",
        "vancomycin-resistance",
        "phylogenetics",
        "mlst"
    ],
    
    # License
    license="GPL-3.0",
    
    # Platforms
    platforms=["any"],
    
    # Zip safe
    zip_safe=False,
    
    # Test suite
    test_suite="tests",
    
    # Setup requires
    setup_requires=[
        "wheel",
        "setuptools_scm"
    ]
)

# Post-installation message
print("""
🧬 BacPipe 2.0 Installation Complete!

Next steps:
1. Setup databases: bacpipe-update-db --all
2. Test installation: bacpipe --test
3. Launch GUI: bacpipe-gui
4. Read documentation: https://bacpipe.readthedocs.io

For support: basilbritto.xavier@umcg.nl
""")
