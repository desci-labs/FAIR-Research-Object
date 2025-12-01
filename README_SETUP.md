# FAIROs - Complete Setup Guide

> **FAIR Research Object Assessment Tool**  
> A comprehensive tool to evaluate the FAIRness (Findable, Accessible, Interoperable, Reusable) of Research Objects serialized as RO-Crates.

[![DOI](https://zenodo.org/badge/431199041.svg)](https://zenodo.org/badge/latestdoi/431199041)
[![Documentation Status](https://readthedocs.org/projects/fairos/badge/?version=latest)](https://fairos.readthedocs.io/en/latest/?badge=latest)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
   - [Step 1: Clone the Repository](#step-1-clone-the-repository)
   - [Step 2: Set Up FAIROs Environment](#step-2-set-up-fairos-environment)
   - [Step 3: Set Up F-UJI Server](#step-3-set-up-f-uji-server)
   - [Step 4: Configure SOMEF](#step-4-configure-somef)
5. [Running FAIROs](#running-fairos)
6. [Testing](#testing)
7. [Input Format](#input-format)
8. [Output Format](#output-format)
9. [Troubleshooting](#troubleshooting)

---

## Overview

FAIROs evaluates Research Objects (RO-Crates) against the FAIR principles:

- **F**indable - Persistent identifiers, rich metadata, searchable
- **A**ccessible - Retrievable via standard protocols
- **I**nteroperable - Uses formal knowledge representations
- **R**eusable - Clear licensing, provenance, community standards

The tool integrates multiple assessment services:

| Service | Purpose | Evaluates |
|---------|---------|-----------|
| **RO-Crate Checker** | Built-in RO-Crate validation | RO-Crate structure & metadata |
| **F-UJI** | FAIR data assessment | Datasets, URLs, DOIs |
| **SOMEF** | Software metadata extraction | GitHub/GitLab repositories |
| **FOOPS** | Ontology assessment | OWL/RDF ontologies |

---

## Architecture

```
FAIROs
├── ROCrateFAIRnessCalculator  → Built-in RO-Crate FAIR checks
├── FujiWrapper                → F-UJI API client (localhost:1071)
├── SoftwareFAIRnessCalculator → SOMEF-based software analysis
└── FoopsWrapper               → FOOPS API client (ontologies)
```

---

## Prerequisites

### Required Software

- **Python 3.11** (required for F-UJI compatibility)
- **Git**
- **Graphviz** (for diagram generation)

### Install Graphviz

**macOS:**
```bash
brew install graphviz
```

**Ubuntu/Debian:**
```bash
sudo apt-get install graphviz
```

**Windows:**
Download from https://graphviz.org/download/ and ensure it's added to PATH.

---

## Installation

### Step 1: Clone the Repository

```bash
# Clone FAIROs
cd /path/to/your/workspace
git clone https://github.com/oeg-upm/FAIR-Research-Object.git
cd FAIR-Research-Object
```

### Step 2: Set Up FAIROs Environment

**Important:** Use Python 3.11 for compatibility with all dependencies.

```bash
# Find Python 3.11 on your system
# Common locations:
# - /usr/bin/python3.11
# - /usr/local/bin/python3.11
# - ~/miniconda3/bin/python3.11
# - /opt/homebrew/bin/python3.11

# Create virtual environment with Python 3.11
python3.11 -m venv venv

# Activate the virtual environment
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# Upgrade pip
pip install --upgrade pip

# Install FAIROs dependencies
# Note: We install the latest compatible SOMEF (>=0.9.10) instead of the pinned version
pip install rocrate validators graphviz requests 'somef>=0.9.10'
```

### Step 3: Set Up F-UJI Server

F-UJI provides comprehensive FAIR assessment for datasets and URLs.

```bash
# Navigate to parent directory
cd ..

# Clone F-UJI
git clone https://github.com/pangaea-data-publisher/fuji.git
cd fuji

# Checkout the master branch (latest stable)
git checkout master

# Create virtual environment with Python 3.11
python3.11 -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS

# Upgrade pip
pip install --upgrade pip

# Install F-UJI
pip install .
```

**Verify F-UJI installation:**
```bash
python -c "import fuji_server; print('F-UJI installed successfully')"
```

### Step 4: Configure SOMEF

SOMEF extracts metadata from software repositories.

```bash
# Go back to FAIROs directory
cd ../FAIR-Research-Object
source venv/bin/activate

# Download required NLTK data
python -c "
import nltk
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
"

# Configure SOMEF (auto-configuration without GitHub token)
somef configure --auto
```

**Optional: Configure GitHub Token for better API limits**

For extensive use, add a GitHub personal access token:

```bash
# Find the config file location
somef configure --help

# Edit ~/.somef/config.json and add:
# {
#   "Authorization": "token YOUR_GITHUB_TOKEN"
# }
```

---

## Running FAIROs

### 1. Start the F-UJI Server

In a **separate terminal**:

```bash
cd /path/to/fuji
source venv/bin/activate
python -m fuji_server -c fuji_server/config/server.ini
```

You should see:
```
INFO:     Uvicorn running on http://localhost:1071 (Press CTRL+C to quit)
```

### 2. Run FAIROs Assessment

In another terminal:

```bash
cd /path/to/FAIR-Research-Object
source venv/bin/activate

# Basic usage
python code/fair_assessment/full_ro_fairness.py -ro /path/to/your/ro-crate/ -o output.json

# With all options
python code/fair_assessment/full_ro_fairness.py \
    -ro /path/to/your/ro-crate/ \
    -o my_FAIR_assessment.json \
    -m true \
    -a 1 \
    -d true
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-ro` | Path to RO-Crate directory (required) | - |
| `-o` | Output JSON filename | `ro-fairness.json` |
| `-m` | Evaluate RO metadata components | `false` |
| `-a` | Aggregation mode (0 or 1) | `0` |
| `-d` | Generate diagram | `false` |

---

## Testing

Two test scripts are provided:

### 1. test_cli.py - Test Core Functionality

Tests the FAIROs CLI and core classes without requiring external services:

```bash
cd /path/to/FAIR-Research-Object
source venv/bin/activate
python test_cli.py
```

This tests:
- Python dependencies (rocrate, validators, requests)
- CLI argument parsing (`-ro`, `-o`, `-m`, `-a`, `-d`)
- ROCrateFAIRnessCalculator class
- F-UJI wrapper (if server running)
- SOMEF installation

### 2. test_real_input.py - Test with Real RO-Crates

Downloads and tests real RO-Crates from WorkflowHub:

```bash
# Start F-UJI server first (in separate terminal)
cd /path/to/fuji
source venv/bin/activate
python -m fuji_server -c fuji_server/config/server.ini

# Run tests (in another terminal)
cd /path/to/FAIR-Research-Object
source venv/bin/activate
python test_real_input.py
```

This tests:
- Downloading RO-Crates from WorkflowHub
- Full FAIROs assessment pipeline
- F-UJI FAIR evaluation
- Results parsing and display

Example output:
```
🎯 Overall FAIR Score: 66.67%
📦 Components Assessed: 4
   ┌─ Research Object Crate for Cheminformatics
   │  Type: ro-crate
   │  Tools: F-uji, ro-crate-metadata
   │  Checks: 15/17 passed
   └────────────────────────
```

---

## Input Format

FAIROs expects an **RO-Crate** directory containing a `ro-crate-metadata.json` file:

```
my-research-object/
├── ro-crate-metadata.json    ← Required manifest
├── data/                     ← Your research data
├── scripts/                  ← Analysis scripts
└── README.md                 ← Documentation
```

### ro-crate-metadata.json Structure

```json
{
    "@context": "https://w3id.org/ro/crate/1.1/context",
    "@graph": [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": { "@id": "./" },
            "conformsTo": { "@id": "https://w3id.org/ro/crate/1.1" }
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": "My Research Project",
            "description": "Description of the research...",
            "author": [{ "@id": "https://orcid.org/0000-0001-2345-6789" }],
            "license": { "@id": "https://spdx.org/licenses/CC-BY-4.0" },
            "identifier": "https://doi.org/10.1234/example",
            "datePublished": "2024-01-15",
            "hasPart": [
                { "@id": "data/dataset.csv" },
                { "@id": "#my-software" }
            ]
        },
        {
            "@id": "#my-software",
            "@type": "SoftwareApplication",
            "name": "Analysis Tool",
            "installUrl": "https://github.com/user/repo"
        }
    ]
}
```

### Supported Entity Types

| Type | Assessment Tool | Required Properties |
|------|-----------------|---------------------|
| `Dataset` | F-UJI | `@id` (URL), `description` |
| `SoftwareApplication` | SOMEF | `installUrl` or `codeRepository` |
| `Ontology` | FOOPS | `@id` (w3id/purl URL) |
| `File` | RO-Crate checker | `@id`, `license` |

---

## Output Format

FAIROs generates a JSON file with detailed assessment results:

```json
{
    "components": [
        {
            "name": "My Research Project",
            "identifier": "https://doi.org/10.1234/example",
            "type": "ro-crate",
            "tool-used": ["F-uji", "ro-crate-metadata"],
            "checks": [
                {
                    "principle_id": "F1.1",
                    "category_id": "Findable",
                    "title": "Data is assigned a globally unique identifier",
                    "status": "pass",
                    "score": 1,
                    "total_score": 1,
                    "sources": [...]
                }
            ],
            "score": {
                "Findable": { "tests_passed": 5, "total_tests": 6 },
                "Accessible": { "tests_passed": 3, "total_tests": 3 },
                "Interoperable": { "tests_passed": 2, "total_tests": 3 },
                "Reusable": { "tests_passed": 4, "total_tests": 5 }
            }
        }
    ],
    "overall_score": {
        "description": "Formula: score of each principle / total score",
        "score": 82.35
    }
}
```

---

## Troubleshooting

### Common Issues

#### 1. F-UJI Server Not Starting

**Error:** `ModuleNotFoundError: No module named 'fuji_server'`

**Solution:**
```bash
cd /path/to/fuji
source venv/bin/activate
pip install .
```

#### 2. SOMEF NLTK Data Missing

**Error:** `LookupError: Resource wordnet not found`

**Solution:**
```bash
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
```

#### 3. SOMEF Configuration Error

**Error:** `Error: Please provide a config.json file or run somef configure`

**Solution:**
```bash
somef configure --auto
```

#### 4. Python Version Mismatch

**Error:** `ERROR: Package 'fuji' requires a different Python`

**Solution:** Ensure you're using Python 3.11:
```bash
python3.11 --version  # Should show Python 3.11.x
```

#### 5. F-UJI Connection Refused

**Error:** `ConnectionRefusedError: [Errno 111] Connection refused`

**Solution:** Make sure F-UJI server is running in a separate terminal:
```bash
cd /path/to/fuji
source venv/bin/activate
python -m fuji_server -c fuji_server/config/server.ini
```

### Checking Service Status

```bash
# Check F-UJI
curl http://localhost:1071/fuji/api/v1/

# Check SOMEF
somef --version

# Check Python packages
pip list | grep -E "rocrate|somef|validators"
```

---

## Directory Structure After Setup

```
workspace/
├── FAIR-Research-Object/
│   ├── venv/                          ← FAIROs virtual environment
│   ├── code/
│   │   └── fair_assessment/
│   │       ├── full_ro_fairness.py    ← Main entry point
│   │       ├── rocrate_fairness/      ← RO-Crate checker
│   │       ├── fuji_wrapper/          ← F-UJI client
│   │       ├── somef_wrapper/         ← SOMEF client
│   │       ├── foops_wrapper/         ← FOOPS client
│   │       └── ro-examples/           ← Sample RO-Crates
│   ├── test-ro-crates/                ← Downloaded test RO-Crates
│   └── README_SETUP.md                ← This file
│
└── fuji/
    ├── venv/                          ← F-UJI virtual environment
    └── fuji_server/
        └── config/
            └── server.ini             ← F-UJI configuration
```

---

## Quick Reference

### Start Everything

**Terminal 1 - F-UJI Server:**
```bash
cd /path/to/fuji
source venv/bin/activate
python -m fuji_server -c fuji_server/config/server.ini
```

**Terminal 2 - FAIROs:**
```bash
cd /path/to/FAIR-Research-Object
source venv/bin/activate
python code/fair_assessment/full_ro_fairness.py -ro /path/to/ro-crate/ -o output.json
```

### Service Ports

| Service | URL |
|---------|-----|
| F-UJI API | http://localhost:1071/fuji/api/v1/ |
| F-UJI Swagger UI | http://localhost:1071/fuji/api/v1/ui/ |

---

## Citation

If you use FAIROs, please cite:

```bibtex
@inproceedings{10.1007/978-3-031-16802-4_6,
    author="González, Esteban and Benítez, Alejandro and Garijo, Daniel",
    title="FAIROs: Towards FAIR Assessment in Research Objects",
    booktitle="Linking Theory and Practice of Digital Libraries",
    year="2022",
    publisher="Springer International Publishing",
    pages="68--80",
    isbn="978-3-031-16802-4",
    doi="https://doi.org/10.1007/978-3-031-16802-4_6"
}
```

---

## License

Apache License 2.0

---

*Last updated: December 2024*

