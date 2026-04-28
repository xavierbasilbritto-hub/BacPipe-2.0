"""
BacPipe 2.0 - Integrated AMR Detection
=======================================
Combines three complementary engines:

  1. AMRFinderPlus (NCBI)   - PRIMARY engine
                              - Curated cutoffs, point-mutation detection,
                                'plus' subset (virulence, stress, biocide)
  2. Custom mcr database    - SECONDARY high-sensitivity layer for mcr-1..mcr-10
                              - Catches divergent / novel mcr alleles below
                                AMRFinderPlus curated cutoffs
  3. Custom vanP database   - SECONDARY layer for Enterococcus vanP cluster
                              - Useful when AMRFinderPlus does not flag a hit

The integrated profile cross-references hits between engines and reports
a confidence-weighted summary.

BSB (Basil Britto Xavier) — UMCG / DRAIGON Project
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# AMRFinderPlus integration
from .amrfinderplus import (
    AMRFinderConfig,
    AMRFinderInputType,
    AMRFinderPlusRunner,
    AMRFinderReport,
    auto_select_organism,
)


# ---------------------------------------------------------------------------
# Confidence model
# ---------------------------------------------------------------------------
class Confidence(Enum):
    HIGH = "high"           # AMRFinderPlus pass + ≥95% ID + ≥90% cov
    MODERATE = "moderate"   # AMRFinderPlus pass + ≥90% ID
    LOW = "low"             # Custom DB hit only
    UNCERTAIN = "uncertain" # Below all thresholds


@dataclass
class IntegratedHit:
    gene_symbol: str
    detected_by: List[str]                     # ["amrfinderplus", "custom_mcr", ...]
    drug_class: str
    contig_id: str
    start: int
    stop: int
    strand: str
    percent_identity: float
    percent_coverage: float
    method: str                                # AMRFinderPlus method or "BLAST_CUSTOM"
    confidence: str                            # Confidence enum value
    accession: str = ""
    notes: str = ""


@dataclass
class IntegratedAMRProfile:
    sample_id: str
    species: Optional[str]
    organism_used: Optional[str]               # AMRFinderPlus --organism, if any
    amrfinderplus_software: str
    amrfinderplus_database: str
    total_resistance_genes: int
    integrated_hits: List[IntegratedHit]
    drug_class_summary: Dict[str, int]
    point_mutations: List[IntegratedHit]
    virulence_factors: List[IntegratedHit]
    stress_response: List[IntegratedHit]

    # Specialised summaries (BSB's research focus)
    mcr_hits: List[IntegratedHit]
    van_hits: List[IntegratedHit]              # All van* (vanA, vanB, vanP, ...)
    vanP_hits: List[IntegratedHit]             # vanP cluster only
    colistin_resistance_call: str              # negative | positive_low | positive_moderate | positive_high
    vancomycin_resistance_call: str

    raw_amrfinder_report: str                  # Path to JSON
    confidence_score: float                    # 0.0 – 1.0


# ---------------------------------------------------------------------------
# Custom mcr/vanP screen (lightweight BLAST wrapper)
# ---------------------------------------------------------------------------
@dataclass
class CustomBlastHit:
    query_contig: str
    subject_gene: str
    pident: float
    qcov: float
    evalue: float
    qstart: int
    qend: int
    strand: str


async def _run_blastn(
    query_fasta: Path,
    subject_db_fasta: Path,
    output_tsv: Path,
    pident_min: float = 80.0,
    qcov_min: float = 60.0,
    evalue: str = "1e-5",
    threads: int = 4,
) -> List[CustomBlastHit]:
    """Run a sensitive blastn search for divergent/novel alleles."""
    cmd = [
        "blastn",
        "-query", str(query_fasta),
        "-subject", str(subject_db_fasta),
        "-out", str(output_tsv),
        "-outfmt", "6 qseqid sseqid pident qcovs evalue qstart qend sstart send",
        "-perc_identity", str(pident_min),
        "-qcov_hsp_perc", str(qcov_min),
        "-evalue", evalue,
        "-num_threads", str(threads),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        return []  # Tool/DB missing — fall through; AMRFinderPlus is primary

    hits: List[CustomBlastHit] = []
    if not output_tsv.exists():
        return hits
    with open(output_tsv) as fh:
        for line in fh:
            parts = line.strip().split("\t")
            if len(parts) < 9:
                continue
            try:
                strand = "+" if int(parts[7]) < int(parts[8]) else "-"
                hits.append(CustomBlastHit(
                    query_contig=parts[0],
                    subject_gene=parts[1],
                    pident=float(parts[2]),
                    qcov=float(parts[3]),
                    evalue=float(parts[4]),
                    qstart=int(parts[5]),
                    qend=int(parts[6]),
                    strand=strand,
                ))
            except ValueError:
                continue
    return hits


# ---------------------------------------------------------------------------
# Integrated AMR analyser
# ---------------------------------------------------------------------------
class IntegratedAMRAnalyser:
    """Run AMRFinderPlus + custom mcr/vanP screens and merge the results."""

    def __init__(
        self,
        amrfinder_db_dir: Optional[Path] = None,
        custom_mcr_db: Optional[Path] = None,
        custom_vanp_db: Optional[Path] = None,
        threads: int = 8,
        logger: Optional[logging.Logger] = None,
    ):
        self.amrfinder_db_dir = amrfinder_db_dir
        self.custom_mcr_db = custom_mcr_db
        self.custom_vanp_db = custom_vanp_db
        self.threads = threads
        self.logger = logger or logging.getLogger("IntegratedAMR")

    async def analyse(
        self,
        sample_id: str,
        assembly_fasta: Path,
        protein_fasta: Optional[Path] = None,
        gff_file: Optional[Path] = None,
        species: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> IntegratedAMRProfile:
        output_dir = Path(output_dir or f"output/{sample_id}/amr")
        output_dir.mkdir(parents=True, exist_ok=True)

        # ---- 1. AMRFinderPlus (PRIMARY) ----------------------------------
        organism = auto_select_organism(species) if species else None
        if protein_fasta and gff_file:
            mode = AMRFinderInputType.COMBINED
        elif protein_fasta:
            mode = AMRFinderInputType.PROTEIN
        else:
            mode = AMRFinderInputType.NUCLEOTIDE

        cfg = AMRFinderConfig(
            input_type=mode,
            organism=organism,
            threads=self.threads,
            plus=True,
            print_node=True,
            report_all_equal=True,
        )
        runner = AMRFinderPlusRunner(cfg, database_dir=self.amrfinder_db_dir,
                                     logger=self.logger)
        afp_report: AMRFinderReport = await runner.run(
            sample_id=sample_id,
            nucleotide_fasta=assembly_fasta,
            protein_fasta=protein_fasta,
            gff_file=gff_file,
            output_dir=output_dir / "amrfinderplus",
        )

        # ---- 2. Custom mcr (SECONDARY high-sensitivity) -------------------
        mcr_blast_hits: List[CustomBlastHit] = []
        if self.custom_mcr_db and self.custom_mcr_db.exists():
            mcr_blast_hits = await _run_blastn(
                query_fasta=assembly_fasta,
                subject_db_fasta=self.custom_mcr_db,
                output_tsv=output_dir / f"{sample_id}.custom_mcr.tsv",
                pident_min=80.0, qcov_min=60.0, threads=self.threads,
            )

        # ---- 3. Custom vanP (SECONDARY) -----------------------------------
        vanp_blast_hits: List[CustomBlastHit] = []
        if self.custom_vanp_db and self.custom_vanp_db.exists():
            vanp_blast_hits = await _run_blastn(
                query_fasta=assembly_fasta,
                subject_db_fasta=self.custom_vanp_db,
                output_tsv=output_dir / f"{sample_id}.custom_vanp.tsv",
                pident_min=85.0, qcov_min=70.0, threads=self.threads,
            )

        # ---- 4. Integrate -------------------------------------------------
        integrated = self._integrate(afp_report, mcr_blast_hits, vanp_blast_hits)

        profile = IntegratedAMRProfile(
            sample_id=sample_id,
            species=species,
            organism_used=organism.value if organism else None,
            amrfinderplus_software=afp_report.software_version,
            amrfinderplus_database=afp_report.database_version,
            total_resistance_genes=len(integrated["amr_all"]),
            integrated_hits=integrated["amr_all"],
            drug_class_summary=integrated["drug_summary"],
            point_mutations=integrated["point_muts"],
            virulence_factors=integrated["virulence"],
            stress_response=integrated["stress"],
            mcr_hits=integrated["mcr"],
            van_hits=integrated["van_all"],
            vanP_hits=integrated["vanP"],
            colistin_resistance_call=self._call_colistin(integrated["mcr"]),
            vancomycin_resistance_call=self._call_vancomycin(integrated["van_all"]),
            raw_amrfinder_report=str(output_dir / "amrfinderplus" /
                                     f"{sample_id}.amrfinder.report.json"),
            confidence_score=self._overall_confidence(integrated["amr_all"]),
        )

        # Persist integrated profile
        json_out = output_dir / f"{sample_id}.integrated_amr.json"
        with open(json_out, "w") as fh:
            json.dump(asdict(profile), fh, indent=2, default=str)
        self.logger.info(
            f"Integrated AMR profile written for {sample_id}: "
            f"{profile.total_resistance_genes} AMR, "
            f"{len(profile.mcr_hits)} mcr, {len(profile.vanP_hits)} vanP"
        )
        return profile

    # ---------- helpers ----------------------------------------------------
    def _integrate(
        self,
        afp: AMRFinderReport,
        mcr_blast: List[CustomBlastHit],
        vanp_blast: List[CustomBlastHit],
    ) -> Dict[str, list]:
        """Merge AMRFinderPlus + custom BLAST hits, deduplicating by gene symbol+contig."""
        seen: set = set()
        amr_all: List[IntegratedHit] = []

        # AMRFinderPlus AMR hits
        for h in afp.amr_hits:
            conf = self._confidence_from_afp(h.percent_identity_to_reference,
                                             h.percent_coverage_of_reference)
            ih = IntegratedHit(
                gene_symbol=h.gene_symbol,
                detected_by=["amrfinderplus"],
                drug_class=h.drug_class,
                contig_id=h.contig_id,
                start=h.start,
                stop=h.stop,
                strand=h.strand,
                percent_identity=h.percent_identity_to_reference,
                percent_coverage=h.percent_coverage_of_reference,
                method=h.method,
                confidence=conf,
                accession=h.accession_of_closest_sequence,
                notes=h.sequence_name,
            )
            amr_all.append(ih)
            seen.add((h.gene_symbol.lower(), h.contig_id, h.start // 1000))

        # Custom mcr BLAST — only add when not already seen
        for b in mcr_blast:
            key = (b.subject_gene.lower(), b.query_contig, b.qstart // 1000)
            if key in seen:
                continue
            amr_all.append(IntegratedHit(
                gene_symbol=b.subject_gene,
                detected_by=["custom_mcr"],
                drug_class="COLISTIN",
                contig_id=b.query_contig,
                start=b.qstart,
                stop=b.qend,
                strand=b.strand,
                percent_identity=b.pident,
                percent_coverage=b.qcov,
                method="BLAST_CUSTOM",
                confidence=Confidence.LOW.value,
                notes="Below AMRFinderPlus curated cutoff — verify",
            ))

        for b in vanp_blast:
            key = (b.subject_gene.lower(), b.query_contig, b.qstart // 1000)
            if key in seen:
                continue
            amr_all.append(IntegratedHit(
                gene_symbol=b.subject_gene,
                detected_by=["custom_vanp"],
                drug_class="GLYCOPEPTIDE",
                contig_id=b.query_contig,
                start=b.qstart,
                stop=b.qend,
                strand=b.strand,
                percent_identity=b.pident,
                percent_coverage=b.qcov,
                method="BLAST_CUSTOM",
                confidence=Confidence.LOW.value,
                notes="Below AMRFinderPlus curated cutoff — verify",
            ))

        # Convenience extracts
        mcr = [h for h in amr_all if h.gene_symbol.lower().startswith("mcr")]
        van_all = [h for h in amr_all if h.gene_symbol.lower().startswith("van")]
        vanP = [h for h in van_all if h.gene_symbol.lower().startswith("vanp")]

        # Drug class summary
        drug_summary: Dict[str, int] = {}
        for h in amr_all:
            if h.drug_class:
                drug_summary[h.drug_class] = drug_summary.get(h.drug_class, 0) + 1

        # Point mutations / virulence / stress from AMRFinderPlus only
        def _afp_to_ih(h, default_conf):
            return IntegratedHit(
                gene_symbol=h.gene_symbol,
                detected_by=["amrfinderplus"],
                drug_class=h.drug_class,
                contig_id=h.contig_id,
                start=h.start,
                stop=h.stop,
                strand=h.strand,
                percent_identity=h.percent_identity_to_reference,
                percent_coverage=h.percent_coverage_of_reference,
                method=h.method,
                confidence=default_conf,
                accession=h.accession_of_closest_sequence,
                notes=h.sequence_name,
            )

        point_muts = [_afp_to_ih(h, self._confidence_from_afp(
            h.percent_identity_to_reference, h.percent_coverage_of_reference))
            for h in afp.point_mutations]
        virulence  = [_afp_to_ih(h, Confidence.MODERATE.value) for h in afp.virulence_hits]
        stress     = [_afp_to_ih(h, Confidence.MODERATE.value) for h in afp.stress_hits]

        return {
            "amr_all": amr_all,
            "mcr": mcr,
            "van_all": van_all,
            "vanP": vanP,
            "point_muts": point_muts,
            "virulence": virulence,
            "stress": stress,
            "drug_summary": drug_summary,
        }

    @staticmethod
    def _confidence_from_afp(pident: float, qcov: float) -> str:
        if pident >= 95.0 and qcov >= 90.0:
            return Confidence.HIGH.value
        if pident >= 90.0 and qcov >= 80.0:
            return Confidence.MODERATE.value
        if pident >= 85.0 and qcov >= 60.0:
            return Confidence.LOW.value
        return Confidence.UNCERTAIN.value

    @staticmethod
    def _call_colistin(mcr_hits: List[IntegratedHit]) -> str:
        if not mcr_hits:
            return "negative"
        confs = [h.confidence for h in mcr_hits]
        if Confidence.HIGH.value in confs:
            return "positive_high"
        if Confidence.MODERATE.value in confs:
            return "positive_moderate"
        return "positive_low_verify"

    @staticmethod
    def _call_vancomycin(van_hits: List[IntegratedHit]) -> str:
        if not van_hits:
            return "negative"
        # vanA, vanB → high-level; vanC, vanP → low-level (intrinsic-like)
        symbols = [h.gene_symbol.lower() for h in van_hits]
        if any(s.startswith(("vana", "vanb", "vand", "vanm")) for s in symbols):
            return "positive_high_level"
        if any(s.startswith(("vanc", "vanp", "vane", "vang", "vanl", "vann")) for s in symbols):
            return "positive_low_level"
        return "positive_uncharacterised"

    @staticmethod
    def _overall_confidence(hits: List[IntegratedHit]) -> float:
        if not hits:
            return 0.0
        weights = {
            Confidence.HIGH.value: 1.0,
            Confidence.MODERATE.value: 0.75,
            Confidence.LOW.value: 0.4,
            Confidence.UNCERTAIN.value: 0.15,
        }
        total = sum(weights.get(h.confidence, 0.15) for h in hits)
        return round(total / len(hits), 3)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BacPipe 2.0 — Integrated AMR analysis")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--protein", type=Path, default=None)
    parser.add_argument("--gff", type=Path, default=None)
    parser.add_argument("--species", default=None,
                        help="Species string for AMRFinderPlus --organism mapping")
    parser.add_argument("--amrfinder-db", type=Path, default=None)
    parser.add_argument("--mcr-db", type=Path, default=None)
    parser.add_argument("--vanp-db", type=Path, default=None)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    analyser = IntegratedAMRAnalyser(
        amrfinder_db_dir=args.amrfinder_db,
        custom_mcr_db=args.mcr_db,
        custom_vanp_db=args.vanp_db,
        threads=args.threads,
    )

    profile = asyncio.run(analyser.analyse(
        sample_id=args.sample_id,
        assembly_fasta=args.assembly,
        protein_fasta=args.protein,
        gff_file=args.gff,
        species=args.species,
        output_dir=args.output_dir,
    ))

    print(json.dumps({
        "sample_id": profile.sample_id,
        "amrfinderplus": {
            "software": profile.amrfinderplus_software,
            "database": profile.amrfinderplus_database,
            "organism": profile.organism_used,
        },
        "totals": {
            "amr_genes": profile.total_resistance_genes,
            "point_mutations": len(profile.point_mutations),
            "virulence": len(profile.virulence_factors),
            "stress": len(profile.stress_response),
            "mcr": len(profile.mcr_hits),
            "van_all": len(profile.van_hits),
            "vanP": len(profile.vanP_hits),
        },
        "calls": {
            "colistin": profile.colistin_resistance_call,
            "vancomycin": profile.vancomycin_resistance_call,
        },
        "drug_class_summary": profile.drug_class_summary,
        "confidence_score": profile.confidence_score,
    }, indent=2))
