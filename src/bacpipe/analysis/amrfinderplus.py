"""
BacPipe 2.0 - AMRFinderPlus Integration Module
Wraps NCBI's AMRFinderPlus (v4.2.7+) for comprehensive AMR, virulence,
stress, and Stx operon detection.

AMRFinderPlus is the gold-standard NCBI tool used by the Pathogen Detection
pipeline. It integrates curated reference genes + HMMs and supports
organism-specific point mutation calling for several taxa.

References:
  - Tool: https://github.com/ncbi/amr
  - DB:   https://ftp.ncbi.nlm.nih.gov/pathogen/Antimicrobial_resistance/AMRFinderPlus/database/latest
  - Cite: Feldgarden et al., Sci Rep 2021, 11:12728

BSB (Basil Britto Xavier) — UMCG / DRAIGON Project
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Supported organisms for point-mutation detection (AMRFinderPlus --organism)
# Keep this list in sync with `amrfinder -l` output.
# ---------------------------------------------------------------------------
class AMRFinderOrganism(Enum):
    ACINETOBACTER_BAUMANNII = "Acinetobacter_baumannii"
    BURKHOLDERIA_CEPACIA = "Burkholderia_cepacia"
    BURKHOLDERIA_PSEUDOMALLEI = "Burkholderia_pseudomallei"
    CAMPYLOBACTER = "Campylobacter"
    CITROBACTER_FREUNDII = "Citrobacter_freundii"
    CLOSTRIDIOIDES_DIFFICILE = "Clostridioides_difficile"
    ENTEROBACTER_ASBURIAE = "Enterobacter_asburiae"
    ENTEROBACTER_CLOACAE = "Enterobacter_cloacae"
    ENTEROCOCCUS_FAECALIS = "Enterococcus_faecalis"
    ENTEROCOCCUS_FAECIUM = "Enterococcus_faecium"
    ENTEROCOCCUS_HIRAE = "Enterococcus_hirae"
    ESCHERICHIA = "Escherichia"
    KLEBSIELLA_OXYTOCA = "Klebsiella_oxytoca"
    KLEBSIELLA_PNEUMONIAE = "Klebsiella_pneumoniae"
    NEISSERIA_GONORRHOEAE = "Neisseria_gonorrhoeae"
    NEISSERIA_MENINGITIDIS = "Neisseria_meningitidis"
    PSEUDOMONAS_AERUGINOSA = "Pseudomonas_aeruginosa"
    SALMONELLA = "Salmonella"
    SERRATIA_MARCESCENS = "Serratia_marcescens"
    STAPHYLOCOCCUS_AUREUS = "Staphylococcus_aureus"
    STAPHYLOCOCCUS_PSEUDINTERMEDIUS = "Staphylococcus_pseudintermedius"
    STREPTOCOCCUS_AGALACTIAE = "Streptococcus_agalactiae"
    STREPTOCOCCUS_PNEUMONIAE = "Streptococcus_pneumoniae"
    STREPTOCOCCUS_PYOGENES = "Streptococcus_pyogenes"
    VIBRIO_CHOLERAE = "Vibrio_cholerae"
    VIBRIO_PARAHAEMOLYTICUS = "Vibrio_parahaemolyticus"
    VIBRIO_VULNIFICUS = "Vibrio_vulnificus"


class AMRFinderInputType(Enum):
    NUCLEOTIDE = "nucleotide"   # Assembly FASTA  (-n)
    PROTEIN = "protein"         # Protein FASTA   (-p)
    COMBINED = "combined"       # Assembly + GFF  (-n + -g + -p) -- best mode


@dataclass
class AMRFinderConfig:
    """Configuration for an AMRFinderPlus run."""
    input_type: AMRFinderInputType = AMRFinderInputType.NUCLEOTIDE
    organism: Optional[AMRFinderOrganism] = None    # Enables point-mutation calling
    threads: int = 8
    ident_min: float = -1                           # -1 = use curated cutoffs (recommended)
    coverage_min: float = 0.5                       # 50% coverage default
    plus: bool = True                               # Include virulence, stress, biocide
    report_all_equal: bool = True                   # Report all equally-good hits
    nucleotide_output: bool = True                  # Write hit FASTA
    print_node: bool = True                         # Include hierarchy node in output
    extra_args: List[str] = field(default_factory=list)


@dataclass
class AMRFinderHit:
    """One row of AMRFinderPlus tabular output, normalised."""
    protein_id: str
    contig_id: str
    start: int
    stop: int
    strand: str
    gene_symbol: str
    sequence_name: str
    scope: str               # core | plus
    element_type: str        # AMR | STRESS | VIRULENCE
    element_subtype: str     # AMR | POINT | ACID | BIOCIDE | METAL | HEAT | ANTIGEN | VIRULENCE
    drug_class: str
    drug_subclass: str
    method: str              # EXACTX | ALLELEX | BLASTX | PARTIALX | INTERNAL_STOP | HMM | POINTX | ...
    target_length: int
    reference_sequence_length: int
    percent_coverage_of_reference: float
    percent_identity_to_reference: float
    alignment_length: int
    accession_of_closest_sequence: str
    name_of_closest_sequence: str
    hierarchy_node: str = ""
    hmm_id: str = ""
    hmm_description: str = ""

    @property
    def is_high_confidence(self) -> bool:
        """High confidence: AMRFinderPlus curated cutoff passed AND identity ≥ 95%."""
        return self.percent_identity_to_reference >= 95.0 and self.percent_coverage_of_reference >= 90.0


@dataclass
class AMRFinderReport:
    """Aggregated AMRFinderPlus result for a sample."""
    sample_id: str
    input_file: str
    organism: Optional[str]
    database_version: str
    software_version: str
    total_hits: int
    amr_hits: List[AMRFinderHit]
    virulence_hits: List[AMRFinderHit]
    stress_hits: List[AMRFinderHit]
    point_mutations: List[AMRFinderHit]
    mcr_hits: List[AMRFinderHit]            # Convenience: extracted mcr-* hits
    van_hits: List[AMRFinderHit]            # Convenience: extracted van* hits (incl. vanP)
    drug_class_summary: Dict[str, int]      # {"COLISTIN": 2, "CARBAPENEM": 3, ...}
    raw_tsv_path: str
    nucleotide_hits_fasta: Optional[str] = None


# ---------------------------------------------------------------------------
# AMRFinderPlus runner
# ---------------------------------------------------------------------------
class AMRFinderPlusRunner:
    """
    Async wrapper around the `amrfinder` CLI.

    Workflow:
        1. Verify amrfinder is installed and database is present.
        2. Run amrfinder with appropriate flags.
        3. Parse TSV output into AMRFinderHit objects.
        4. Build an AMRFinderReport with mcr/van convenience extracts.
    """

    EXECUTABLE = "amrfinder"

    def __init__(
        self,
        config: AMRFinderConfig,
        database_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config
        self.database_dir = Path(database_dir) if database_dir else None
        self.logger = logger or self._default_logger()

    @staticmethod
    def _default_logger() -> logging.Logger:
        log = logging.getLogger("AMRFinderPlus")
        if not log.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            log.addHandler(h)
        log.setLevel(logging.INFO)
        return log

    # ---------- environment checks -----------------------------------------
    def check_installation(self) -> Dict[str, str]:
        """Return software version + DB version, or raise if not installed."""
        if shutil.which(self.EXECUTABLE) is None:
            raise RuntimeError(
                "amrfinder not found on PATH. "
                "Install with: conda install -c bioconda ncbi-amrfinderplus"
            )

        result = subprocess.run(
            [self.EXECUTABLE, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        software_version = result.stdout.strip() or "unknown"

        db_version = "unknown"
        try:
            db_check = subprocess.run(
                [self.EXECUTABLE, "-V"],
                capture_output=True, text=True, check=False,
            )
            for line in (db_check.stdout + db_check.stderr).splitlines():
                if "database version" in line.lower():
                    db_version = line.split(":", 1)[-1].strip()
                    break
        except Exception:
            pass

        self.logger.info(f"AMRFinderPlus: software={software_version}, db={db_version}")
        return {"software_version": software_version, "database_version": db_version}

    async def update_database(self, force: bool = False) -> bool:
        """Download / update the AMRFinderPlus database via `amrfinder -u`."""
        flag = "--force_update" if force else "-u"
        cmd = [self.EXECUTABLE, flag]
        if self.database_dir:
            cmd += ["-d", str(self.database_dir)]
        self.logger.info(f"Updating AMRFinderPlus DB: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            self.logger.error(f"amrfinder update failed: {stderr.decode(errors='ignore')}")
            return False
        self.logger.info("AMRFinderPlus database updated.")
        return True

    # ---------- main run ---------------------------------------------------
    async def run(
        self,
        sample_id: str,
        nucleotide_fasta: Optional[Path] = None,
        protein_fasta: Optional[Path] = None,
        gff_file: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> AMRFinderReport:
        """
        Execute AMRFinderPlus for a single sample.

        Mode depends on `self.config.input_type`:
          - NUCLEOTIDE  → -n nucleotide_fasta
          - PROTEIN     → -p protein_fasta
          - COMBINED    → -n + -p + -g  (recommended, most sensitive)
        """
        output_dir = Path(output_dir or f"output/{sample_id}/amrfinder")
        output_dir.mkdir(parents=True, exist_ok=True)
        tsv_out = output_dir / f"{sample_id}.amrfinder.tsv"
        nuc_out = output_dir / f"{sample_id}.amrfinder.hits.fasta"

        cmd: List[str] = [
            self.EXECUTABLE,
            "--threads", str(self.config.threads),
            "-o", str(tsv_out),
        ]

        # Database location
        if self.database_dir:
            cmd += ["-d", str(self.database_dir)]

        # Input mode
        if self.config.input_type == AMRFinderInputType.NUCLEOTIDE:
            if nucleotide_fasta is None:
                raise ValueError("nucleotide_fasta required for NUCLEOTIDE mode")
            cmd += ["-n", str(nucleotide_fasta)]
        elif self.config.input_type == AMRFinderInputType.PROTEIN:
            if protein_fasta is None:
                raise ValueError("protein_fasta required for PROTEIN mode")
            cmd += ["-p", str(protein_fasta)]
        elif self.config.input_type == AMRFinderInputType.COMBINED:
            if not (nucleotide_fasta and protein_fasta and gff_file):
                raise ValueError("COMBINED mode requires nucleotide_fasta, protein_fasta and gff_file")
            cmd += ["-n", str(nucleotide_fasta), "-p", str(protein_fasta), "-g", str(gff_file)]

        # Organism-specific (point mutations)
        if self.config.organism is not None:
            cmd += ["--organism", self.config.organism.value]

        # 'plus' subset (virulence + stress)
        if self.config.plus:
            cmd += ["--plus"]

        # Output options
        if self.config.nucleotide_output and self.config.input_type != AMRFinderInputType.PROTEIN:
            cmd += ["--nucleotide_output", str(nuc_out)]
        if self.config.print_node:
            cmd += ["--print_node"]
        if self.config.report_all_equal:
            cmd += ["--report_all_equal"]
        if self.config.coverage_min and self.config.coverage_min != 0.5:
            cmd += ["--coverage_min", str(self.config.coverage_min)]
        if self.config.ident_min != -1:
            cmd += ["--ident_min", str(self.config.ident_min)]

        cmd += list(self.config.extra_args)

        self.logger.info(f"Running AMRFinderPlus for {sample_id}: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="ignore")
            self.logger.error(f"AMRFinderPlus failed for {sample_id}: {err_msg}")
            raise RuntimeError(f"AMRFinderPlus failed: {err_msg}")

        versions = self.check_installation()
        report = self._parse_results(
            sample_id=sample_id,
            tsv_path=tsv_out,
            nuc_hits_fasta=nuc_out if nuc_out.exists() else None,
            input_file=str(nucleotide_fasta or protein_fasta),
            versions=versions,
        )

        # Persist a JSON report alongside the TSV
        json_path = output_dir / f"{sample_id}.amrfinder.report.json"
        with open(json_path, "w") as fh:
            json.dump(asdict(report), fh, indent=2, default=str)
        self.logger.info(
            f"AMRFinderPlus for {sample_id}: {report.total_hits} hits "
            f"(AMR={len(report.amr_hits)}, VIR={len(report.virulence_hits)}, "
            f"STRESS={len(report.stress_hits)}, mcr={len(report.mcr_hits)}, "
            f"van={len(report.van_hits)})"
        )
        return report

    # ---------- parsing ----------------------------------------------------
    def _parse_results(
        self,
        sample_id: str,
        tsv_path: Path,
        nuc_hits_fasta: Optional[Path],
        input_file: str,
        versions: Dict[str, str],
    ) -> AMRFinderReport:
        if not tsv_path.exists() or tsv_path.stat().st_size == 0:
            return AMRFinderReport(
                sample_id=sample_id,
                input_file=input_file,
                organism=self.config.organism.value if self.config.organism else None,
                database_version=versions.get("database_version", "unknown"),
                software_version=versions.get("software_version", "unknown"),
                total_hits=0,
                amr_hits=[], virulence_hits=[], stress_hits=[],
                point_mutations=[], mcr_hits=[], van_hits=[],
                drug_class_summary={},
                raw_tsv_path=str(tsv_path),
            )

        df = pd.read_csv(tsv_path, sep="\t", dtype=str).fillna("")
        # AMRFinderPlus column names (v4.x). We map to our dataclass.
        col = {
            "protein_id": "Protein identifier",
            "contig":     "Contig id",
            "start":      "Start",
            "stop":       "Stop",
            "strand":     "Strand",
            "gene":       "Gene symbol",
            "name":       "Sequence name",
            "scope":      "Scope",
            "etype":      "Element type",
            "esubtype":   "Element subtype",
            "class":      "Class",
            "subclass":   "Subclass",
            "method":     "Method",
            "tlen":       "Target length",
            "rlen":       "Reference sequence length",
            "cov":        "% Coverage of reference sequence",
            "pid":        "% Identity to reference sequence",
            "alen":       "Alignment length",
            "acc":        "Accession of closest sequence",
            "cname":      "Name of closest sequence",
            "node":       "HierarchyNode",
            "hmm_id":     "HMM id",
            "hmm_desc":   "HMM description",
        }

        def get(row, key, default=""):
            return row.get(col.get(key, key), default)

        hits: List[AMRFinderHit] = []
        for _, row in df.iterrows():
            try:
                hit = AMRFinderHit(
                    protein_id=str(get(row, "protein_id")),
                    contig_id=str(get(row, "contig")),
                    start=int(float(get(row, "start") or 0)),
                    stop=int(float(get(row, "stop") or 0)),
                    strand=str(get(row, "strand") or "."),
                    gene_symbol=str(get(row, "gene")),
                    sequence_name=str(get(row, "name")),
                    scope=str(get(row, "scope")).lower(),
                    element_type=str(get(row, "etype")).upper(),
                    element_subtype=str(get(row, "esubtype")).upper(),
                    drug_class=str(get(row, "class")).upper(),
                    drug_subclass=str(get(row, "subclass")).upper(),
                    method=str(get(row, "method")).upper(),
                    target_length=int(float(get(row, "tlen") or 0)),
                    reference_sequence_length=int(float(get(row, "rlen") or 0)),
                    percent_coverage_of_reference=float(get(row, "cov") or 0.0),
                    percent_identity_to_reference=float(get(row, "pid") or 0.0),
                    alignment_length=int(float(get(row, "alen") or 0)),
                    accession_of_closest_sequence=str(get(row, "acc")),
                    name_of_closest_sequence=str(get(row, "cname")),
                    hierarchy_node=str(get(row, "node")),
                    hmm_id=str(get(row, "hmm_id")),
                    hmm_description=str(get(row, "hmm_desc")),
                )
                hits.append(hit)
            except Exception as e:
                self.logger.warning(f"Skipping malformed AMRFinderPlus row: {e}")

        amr_hits   = [h for h in hits if h.element_type == "AMR"]
        vir_hits   = [h for h in hits if h.element_type == "VIRULENCE"]
        stress     = [h for h in hits if h.element_type == "STRESS"]
        point_muts = [h for h in hits if "POINT" in h.method or h.element_subtype == "POINT"]

        mcr  = [h for h in amr_hits if h.gene_symbol.lower().startswith("mcr")]
        van  = [h for h in amr_hits if h.gene_symbol.lower().startswith("van")]

        drug_summary: Dict[str, int] = {}
        for h in amr_hits:
            if h.drug_class:
                drug_summary[h.drug_class] = drug_summary.get(h.drug_class, 0) + 1

        return AMRFinderReport(
            sample_id=sample_id,
            input_file=input_file,
            organism=self.config.organism.value if self.config.organism else None,
            database_version=versions.get("database_version", "unknown"),
            software_version=versions.get("software_version", "unknown"),
            total_hits=len(hits),
            amr_hits=amr_hits,
            virulence_hits=vir_hits,
            stress_hits=stress,
            point_mutations=point_muts,
            mcr_hits=mcr,
            van_hits=van,
            drug_class_summary=drug_summary,
            raw_tsv_path=str(tsv_path),
            nucleotide_hits_fasta=str(nuc_hits_fasta) if nuc_hits_fasta else None,
        )


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------
def auto_select_organism(species_string: str) -> Optional[AMRFinderOrganism]:
    """
    Heuristic mapping from a species string (e.g. from GTDB-Tk or Kraken2)
    to an AMRFinderPlus --organism value. Returns None when no match.
    """
    if not species_string:
        return None
    s = species_string.lower()
    mapping = {
        "acinetobacter baumannii": AMRFinderOrganism.ACINETOBACTER_BAUMANNII,
        "campylobacter":           AMRFinderOrganism.CAMPYLOBACTER,
        "clostridioides difficile":AMRFinderOrganism.CLOSTRIDIOIDES_DIFFICILE,
        "enterococcus faecalis":   AMRFinderOrganism.ENTEROCOCCUS_FAECALIS,
        "enterococcus faecium":    AMRFinderOrganism.ENTEROCOCCUS_FAECIUM,
        "enterococcus hirae":      AMRFinderOrganism.ENTEROCOCCUS_HIRAE,
        "escherichia":             AMRFinderOrganism.ESCHERICHIA,
        "klebsiella pneumoniae":   AMRFinderOrganism.KLEBSIELLA_PNEUMONIAE,
        "klebsiella oxytoca":      AMRFinderOrganism.KLEBSIELLA_OXYTOCA,
        "neisseria gonorrhoeae":   AMRFinderOrganism.NEISSERIA_GONORRHOEAE,
        "neisseria meningitidis":  AMRFinderOrganism.NEISSERIA_MENINGITIDIS,
        "pseudomonas aeruginosa":  AMRFinderOrganism.PSEUDOMONAS_AERUGINOSA,
        "salmonella":              AMRFinderOrganism.SALMONELLA,
        "serratia marcescens":     AMRFinderOrganism.SERRATIA_MARCESCENS,
        "staphylococcus aureus":   AMRFinderOrganism.STAPHYLOCOCCUS_AUREUS,
        "streptococcus agalactiae":AMRFinderOrganism.STREPTOCOCCUS_AGALACTIAE,
        "streptococcus pneumoniae":AMRFinderOrganism.STREPTOCOCCUS_PNEUMONIAE,
        "streptococcus pyogenes":  AMRFinderOrganism.STREPTOCOCCUS_PYOGENES,
        "vibrio cholerae":         AMRFinderOrganism.VIBRIO_CHOLERAE,
    }
    for key, org in mapping.items():
        if key in s:
            return org
    return None


# ---------------------------------------------------------------------------
# CLI entry point (optional convenience)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BacPipe 2.0 — AMRFinderPlus runner")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--nucleotide", type=Path, help="Assembly FASTA")
    parser.add_argument("--protein", type=Path, help="Protein FASTA (e.g. Prokka *.faa)")
    parser.add_argument("--gff", type=Path, help="GFF (e.g. Prokka *.gff) — required for --combined")
    parser.add_argument("--combined", action="store_true", help="Combined nucleotide+protein mode")
    parser.add_argument("--organism", default=None,
                        help="Organism name string (e.g. 'Escherichia coli')")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--db-dir", type=Path, default=None,
                        help="AMRFinderPlus database directory")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--update-db", action="store_true",
                        help="Run `amrfinder -u` before analysis")
    args = parser.parse_args()

    org = auto_select_organism(args.organism) if args.organism else None
    mode = (AMRFinderInputType.COMBINED if args.combined
            else AMRFinderInputType.NUCLEOTIDE if args.nucleotide
            else AMRFinderInputType.PROTEIN)

    cfg = AMRFinderConfig(input_type=mode, organism=org, threads=args.threads, plus=True)
    runner = AMRFinderPlusRunner(cfg, database_dir=args.db_dir)

    async def _main():
        if args.update_db:
            await runner.update_database()
        report = await runner.run(
            sample_id=args.sample_id,
            nucleotide_fasta=args.nucleotide,
            protein_fasta=args.protein,
            gff_file=args.gff,
            output_dir=args.output_dir,
        )
        print(json.dumps({
            "sample_id": report.sample_id,
            "total_hits": report.total_hits,
            "drug_class_summary": report.drug_class_summary,
            "mcr_genes": [h.gene_symbol for h in report.mcr_hits],
            "van_genes": [h.gene_symbol for h in report.van_hits],
            "point_mutations": [h.gene_symbol for h in report.point_mutations],
            "tsv": report.raw_tsv_path,
        }, indent=2))

    asyncio.run(_main())
