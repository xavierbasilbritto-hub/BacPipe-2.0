# Push this folder to your GitHub account

This folder is ready to become your `BacPipe-2.0` repository on
**https://github.com/xavierbasilbritto-hub**. Three steps.

## 1. Create the empty repo on GitHub

While signed in as `xavierbasilbritto-hub`, go to **https://github.com/new** and:

- **Repository name:** `BacPipe-2.0`
- **Description:** `Modern bacterial WGS pipeline — ONT + Illumina, AMRFinderPlus, mcr/vanP, cross-platform GUI. DRAIGON Project.`
- **Visibility:** Public
- **Do NOT** check "Add README", "Add .gitignore", or "Choose a license" — this folder already has them.
- Click **Create repository**.

## 2. Push from your machine

Open a terminal **inside this `BacPipe-2.0/` folder** and run:

```bash
# Add the GPL-3.0 license text (the scaffold ships a placeholder note)
curl -L -o LICENSE https://www.gnu.org/licenses/gpl-3.0.txt
rm LICENSE.NOTE.md

# Initialise git, commit, and push
git init -b main
git add .
git commit -m "Initial commit: BacPipe 2.0 (ONT + AMRFinderPlus + cross-platform GUI)"

git remote add origin https://github.com/xavierbasilbritto-hub/BacPipe-2.0.git
git push -u origin main
```

If you prefer SSH:
```bash
git remote set-url origin git@github.com:xavierbasilbritto-hub/BacPipe-2.0.git
git push -u origin main
```

## 3. Tag the alpha release (optional)

```bash
git tag -a v2.0.0-alpha.1 -m "BacPipe 2.0 alpha — AMRFinderPlus integration, ONT assemblers"
git push origin v2.0.0-alpha.1
```

---

## Before pushing — quick checklist

- [ ] Add your **ORCID** to `CITATION.cff` (line is commented out).
- [ ] Verify the **author list of the original 2020 iScience paper** in `CITATION.cff` is complete — currently only you and Mysara are listed as a starting point.
- [ ] Replace `LICENSE.NOTE.md` with the real GPL-3.0 text (one curl command above).
- [ ] Skim `README.md` for any internal contact details you'd rather not publish.

## What's in this folder

```
BacPipe-2.0/
├── README.md                 ← project overview (also published on GitHub)
├── CITATION.cff              ← citation metadata (ORCID + iScience paper)
├── LICENSE.NOTE.md           ← replaced by GPL-3.0 text in step 2
├── .gitignore                ← excludes databases, FASTQs, build dirs
├── requirements.txt
├── setup.py
├── PUSH_TO_GITHUB.md         ← this file (delete or keep, your call)
│
├── .github/workflows/
│   └── ci.yml                ← syntax + flake8 + pytest + AMRFinderPlus smoke test
│
├── scripts/
│   └── install.sh            ← conda env + bioconda tools + DBs (incl. AMRFinderPlus)
│
├── src/bacpipe/
│   ├── core/pipeline.py
│   ├── assemblers/ont_assemblers.py
│   ├── analysis/
│   │   ├── amrfinderplus.py            ← NCBI AMRFinderPlus wrapper
│   │   ├── integrated_amr.py           ← AMRFinderPlus + custom mcr/vanP merge
│   │   └── enhanced_amr_detection.py   ← legacy custom-only path (kept for ref)
│   ├── databases/
│   │   ├── database_manager.py
│   │   └── amrfinderplus_db_hook.py    ← `amrfinder -u` integration
│   └── gui/components/BacPipeGUI.jsx
│
├── docs/
│   ├── BacPipe_2.0_Plan.md             ← design rationale
│   ├── IMPLEMENTATION_GUIDE.md         ← phased rollout
│   └── MIGRATION_GUIDE.md              ← fork vs transfer vs fresh-repo options
│
└── tests/                              ← empty for now; CI is wired but tolerant
```

After pushing, on the GitHub repo page click **About → ⚙** and add topics:
`bioinformatics`, `genomics`, `amr`, `amrfinderplus`, `oxford-nanopore`,
`mcr`, `vanp`, `bacterial-genomics`, `whole-genome-sequencing`.

Good luck — ping me when it's pushed and I'll help with the first round of issues / a v2.0.0 release blurb.
