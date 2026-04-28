# Migrating BacPipe 2.0 to your personal GitHub account

**Target:** `https://github.com/xavierbasilbritto-hub/BacPipe`
**Origin:** `https://github.com/wholeGenomeSequencingAnalysisPipeline/BacPipe`

> **Important — what I can and cannot do:** I can generate every file you
> need (modules, scripts, docs, config). I **cannot** create the GitHub
> repository, push commits, or authenticate to your account on your behalf —
> those steps require *your* GitHub credentials and must be run from your
> machine. The commands below do exactly that, and they're standard `git`
> operations you can review line by line.

---

## Decision: fork, transfer, or fresh repo?

You have three options. Pick the one that fits your situation:

| Option | When to use | Pros | Cons |
|---|---|---|---|
| **A. Fork + rename** | You want history of the original BacPipe preserved under your account | Keeps git history; clear lineage from Mysara 2019 paper | The `wholeGenomeSequencingAnalysisPipeline/BacPipe` org repo stays as-is |
| **B. Transfer ownership** | You are an admin of the `wholeGenomeSequencingAnalysisPipeline` org and want to *move* the repo | Same URL semantics; existing forks/stars carry over | You lose the repo from the original org |
| **C. Fresh repo (`BacPipe-2.0`)** | Cleanest break — treat 2.0 as a new project that *cites* BacPipe 1.x | Clean history, modern structure from day one, no legacy baggage | Need to credit & cite the original explicitly |

**My recommendation: Option C** — a fresh `BacPipe-2.0` repo on your account.
The 2019 codebase (Python 2.7, appJar, bundled Linux binaries) is structurally
incompatible with the modern stack, and a clean repo lets you do CI/CD,
proper packaging, and Docker without dragging legacy folders. You credit
Mysara et al. 2019 in the README and CITATION.cff, which is the correct
academic practice.

---

## Option C — Step-by-step (recommended)

### 1. Create the empty repository on GitHub

In your browser, while signed in as `xavierbasilbritto-hub`:

1. Go to https://github.com/new
2. **Repository name:** `BacPipe-2.0` (or `BacPipe2`, your call)
3. **Description:** `Modern bacterial WGS pipeline — ONT + Illumina, AMRFinderPlus, mcr/vanP, cross-platform GUI. DRAIGON Project.`
4. Visibility: **Public**
5. **Do NOT** tick "Add README", "Add .gitignore", or "Add license" — we'll
   commit our own.
6. Click **Create repository**.

### 2. Local layout

On your machine:

```bash
# Pick a working directory
mkdir -p ~/projects && cd ~/projects

# Initialise the new repo
mkdir BacPipe-2.0 && cd BacPipe-2.0
git init -b main
```

### 3. Drop the generated files into the right places

The files Claude generated should land in this layout:

```
BacPipe-2.0/
├── README.md                                # (from session 1)
├── LICENSE                                  # GPL-3.0 (copy from BacPipe 1.x)
├── CITATION.cff                             # (template below)
├── requirements.txt                         # (from session 1)
├── setup.py                                 # (from session 1)
├── pyproject.toml                           # optional, see below
├── .gitignore                               # (template below)
├── BacPipe_2.0_Plan.md                      # design doc (from session 1)
├── scripts/
│   └── install.sh                           # (this session)
├── src/
│   └── bacpipe/
│       ├── __init__.py
│       ├── core/
│       │   └── pipeline.py                  # = bacpipe_core.py (rename)
│       ├── assemblers/
│       │   └── ont_assemblers.py            # (from session 1)
│       ├── analysis/
│       │   ├── amrfinderplus.py             # (this session, NEW)
│       │   ├── integrated_amr.py            # (this session, NEW)
│       │   └── enhanced_amr_detection.py    # (from session 1, optional)
│       ├── databases/
│       │   ├── database_manager.py          # (from session 1)
│       │   └── amrfinderplus_db_hook.py     # (this session, NEW)
│       └── gui/
│           └── components/
│               └── BacPipeGUI.jsx           # = bacpipe_gui.jsx
├── docs/
│   └── ... (move BacPipe_2.0_Plan.md here if you prefer)
└── tests/
    └── __init__.py
```

A minimal `.gitignore` for this stack:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.env

# IDE
.vscode/
.idea/

# OS
.DS_Store

# BacPipe outputs
output/
results/
logs/
*.log

# Databases (too big for git)
databases/
*.fasta
*.fa
*.fastq
*.fq
*.fastq.gz
*.fq.gz
*.bam
*.sam
*.gff

# Node / Electron (when GUI is added)
node_modules/
dist/
build/
```

A starter `CITATION.cff`:

```yaml
cff-version: 1.2.0
message: "If you use BacPipe 2.0, please cite both this software and the original BacPipe paper."
title: "BacPipe 2.0: Modern bacterial WGS pipeline with ONT support and AMRFinderPlus integration"
authors:
  - family-names: Xavier
    given-names: Basil Britto
    affiliation: "University Medical Center Groningen (UMCG); DRAIGON Project"
    orcid: "https://orcid.org/0000-0000-0000-0000"   # <-- add your ORCID
version: "2.0.0"
date-released: "2026-04-28"
license: GPL-3.0-or-later
repository-code: "https://github.com/xavierbasilbritto-hub/BacPipe-2.0"
references:
  - type: article
    title: "BacPipe: A Rapid, User-Friendly Whole-Genome Sequencing Pipeline for Clinical Diagnostic Bacteriology"
    authors:
      - family-names: Xavier
        given-names: Basil Britto
      - family-names: Mysara
        given-names: Mohamed
      - family-names: Bolzan
        given-names: Mariana
      - family-names: Ribeiro-Gonçalves
        given-names: Bruno
      - family-names: Alako
        given-names: Blaise T. F.
      - family-names: Harrison
        given-names: Owen B.
      - family-names: Lammens
        given-names: Christine
      - family-names: Kumar-Singh
        given-names: Samir
      - family-names: Goossens
        given-names: Herman
      - family-names: Carriço
        given-names: João A.
      - family-names: Cochrane
        given-names: Guy
      - family-names: Maiden
        given-names: Martin C. J.
      - family-names: Malhotra-Kumar
        given-names: Surbhi
    journal: "iScience"
    year: 2020
    doi: "10.1016/j.isci.2019.100769"
```
*(Verify and complete the original BacPipe authors list against the 2020
iScience paper before publishing.)*

### 4. First commit

```bash
# Add and commit everything
git add .
git commit -m "Initial commit: BacPipe 2.0 (ONT + AMRFinderPlus + cross-platform GUI)"

# Connect to your new GitHub repo
git remote add origin https://github.com/xavierbasilbritto-hub/BacPipe-2.0.git

# Push
git push -u origin main
```

If you use SSH instead of HTTPS:

```bash
git remote set-url origin git@github.com:xavierbasilbritto-hub/BacPipe-2.0.git
git push -u origin main
```

### 5. Tag the first release

```bash
git tag -a v2.0.0-alpha.1 -m "BacPipe 2.0 alpha — AMRFinderPlus integration, ONT assemblers"
git push origin v2.0.0-alpha.1
```

Then on GitHub: **Releases → Draft a new release → choose tag `v2.0.0-alpha.1`**.

---

## Option A — Fork the existing repo

If you'd rather preserve the git history:

```bash
# 1. On github.com: click "Fork" on
#    https://github.com/wholeGenomeSequencingAnalysisPipeline/BacPipe
#    and choose your account (xavierbasilbritto-hub) as the owner.

# 2. Clone YOUR fork
git clone https://github.com/xavierbasilbritto-hub/BacPipe.git
cd BacPipe

# 3. Create a modernisation branch
git checkout -b bacpipe-2.0

# 4. Drop the new files in place (overwriting Pipeline.py etc. is fine on
#    a separate branch). Then:
git add .
git commit -m "BacPipe 2.0: full modernisation (ONT, AMRFinderPlus, modern GUI)"
git push -u origin bacpipe-2.0
```

You can later open a PR from `bacpipe-2.0` into your `main`, or simply
make `bacpipe-2.0` your new default branch in **Settings → Branches**.

---

## Option B — Transfer the existing repo

Only works if you're an admin of `wholeGenomeSequencingAnalysisPipeline`:

1. Go to https://github.com/wholeGenomeSequencingAnalysisPipeline/BacPipe/settings
2. Scroll to **Danger Zone → Transfer ownership**
3. New owner: `xavierbasilbritto-hub`
4. Confirm.

After transfer the URL becomes
`https://github.com/xavierbasilbritto-hub/BacPipe`, and existing clones
will need their remote updated:
`git remote set-url origin https://github.com/xavierbasilbritto-hub/BacPipe.git`

---

## After the first push — optional but recommended

1. **Branch protection** — Settings → Branches → add a rule for `main`
   requiring PR reviews.
2. **CI** — add `.github/workflows/ci.yml` that runs `pytest` and
   `flake8` on every PR. (I can generate this when you're ready.)
3. **Topics** — on the repo home page, add topics:
   `bioinformatics`, `genomics`, `amr`, `amrfinderplus`,
   `oxford-nanopore`, `mcr`, `vanp`, `bacterial-genomics`.
   These drive discoverability in GitHub search.
4. **Description (top of repo page):** "Modern bacterial WGS pipeline —
   ONT + Illumina + hybrid, AMRFinderPlus + mcr/vanP, cross-platform GUI.
   UMCG / DRAIGON Project."
5. **Link the original** — add a paragraph to README:
   *"BacPipe 2.0 is a substantially rewritten successor to BacPipe (Xavier
   et al., iScience 2020). The original repository remains available at
   https://github.com/wholeGenomeSequencingAnalysisPipeline/BacPipe."*

---

## Sanity check before going public

Run this from inside the local repo:

```bash
# Make sure no large files snuck in
find . -type f -size +50M -not -path "./.git/*"

# Ensure the conda install script is executable
chmod +x scripts/install.sh

# Smoke-test the AMRFinderPlus runner help
python src/bacpipe/analysis/amrfinderplus.py --help
python src/bacpipe/analysis/integrated_amr.py --help
```

When all three are clean, push and announce. 🚀
