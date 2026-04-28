"""
BacPipe 2.0 — top-level command-line interface.

Provides a single `bacpipe` entry point that dispatches to the analysis modules
already shipped under `bacpipe.analysis`, `bacpipe.databases`, and
`bacpipe.assemblers`.

Subcommands
-----------
  bacpipe amr          Run integrated AMR analysis (AMRFinderPlus + custom mcr/vanP)
  bacpipe amrfinder    Run AMRFinderPlus directly (thin wrapper)
  bacpipe update-db    Download/update AMRFinderPlus database
  bacpipe gui          Launch the Streamlit GUI
  bacpipe info         Print version + environment summary
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from bacpipe import __version__


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


# ---------------------------------------------------------------------------
# bacpipe amr
# ---------------------------------------------------------------------------
def _cmd_amr(args: argparse.Namespace) -> int:
    from bacpipe.analysis.integrated_amr import IntegratedAMRAnalyser

    analyser = IntegratedAMRAnalyser(
        amrfinder_db_dir=args.amrfinder_db,
        custom_mcr_db=args.mcr_db,
        custom_vanp_db=args.vanp_db,
        threads=args.threads,
    )
    profile = asyncio.run(
        analyser.analyse(
            sample_id=args.sample_id,
            assembly_fasta=args.assembly,
            protein_fasta=args.protein,
            gff_file=args.gff,
            species=args.species,
            output_dir=args.output_dir,
        )
    )
    summary = {
        "sample_id": profile.sample_id,
        "totals": {
            "amr_genes": profile.total_resistance_genes,
            "mcr": len(profile.mcr_hits),
            "vanP": len(profile.vanP_hits),
        },
        "calls": {
            "colistin": profile.colistin_resistance_call,
            "vancomycin": profile.vancomycin_resistance_call,
        },
        "drug_class_summary": profile.drug_class_summary,
        "confidence_score": profile.confidence_score,
    }
    print(json.dumps(summary, indent=2))
    return 0


# ---------------------------------------------------------------------------
# bacpipe amrfinder
# ---------------------------------------------------------------------------
def _cmd_amrfinder(args: argparse.Namespace) -> int:
    from bacpipe.analysis.amrfinderplus import (
        AMRFinderConfig,
        AMRFinderInputType,
        AMRFinderPlusRunner,
        auto_select_organism,
    )

    if args.combined:
        mode = AMRFinderInputType.COMBINED
    elif args.protein and not args.nucleotide:
        mode = AMRFinderInputType.PROTEIN
    else:
        mode = AMRFinderInputType.NUCLEOTIDE

    organism = auto_select_organism(args.organism) if args.organism else None
    cfg = AMRFinderConfig(
        input_type=mode, organism=organism, threads=args.threads, plus=True
    )
    runner = AMRFinderPlusRunner(cfg, database_dir=args.db_dir)

    async def _run():
        if args.update_db:
            await runner.update_database()
        return await runner.run(
            sample_id=args.sample_id,
            nucleotide_fasta=args.nucleotide,
            protein_fasta=args.protein,
            gff_file=args.gff,
            output_dir=args.output_dir,
        )

    report = asyncio.run(_run())
    print(json.dumps({
        "sample_id": report.sample_id,
        "total_hits": report.total_hits,
        "drug_class_summary": report.drug_class_summary,
        "mcr_genes": [h.gene_symbol for h in report.mcr_hits],
        "van_genes": [h.gene_symbol for h in report.van_hits],
        "tsv": report.raw_tsv_path,
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# bacpipe update-db
# ---------------------------------------------------------------------------
def _cmd_update_db(args: argparse.Namespace) -> int:
    from bacpipe.databases.amrfinderplus_db_hook import update_amrfinderplus_database

    ok = asyncio.run(update_amrfinderplus_database(
        database_dir=args.db_dir, force=args.force
    ))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# bacpipe gui
# ---------------------------------------------------------------------------
def _cmd_gui(args: argparse.Namespace) -> int:
    if shutil.which("streamlit") is None:
        sys.stderr.write(
            "ERROR: streamlit is not installed.\n"
            "Install with: pip install 'bacpipe[gui]'  or  pip install streamlit\n"
        )
        return 1

    app_path = Path(__file__).parent / "gui" / "web.py"
    if not app_path.exists():
        sys.stderr.write(f"ERROR: GUI app not found at {app_path}\n")
        return 1

    cmd = [
        "streamlit", "run", str(app_path),
        "--server.port", str(args.port),
        "--server.headless", "true" if args.headless else "false",
    ]
    return subprocess.call(cmd)


# ---------------------------------------------------------------------------
# bacpipe info
# ---------------------------------------------------------------------------
def _cmd_info(args: argparse.Namespace) -> int:
    info = {
        "bacpipe_version": __version__,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "tools": {},
    }
    for tool in ["amrfinder", "blastn", "spades.py", "flye", "prokka", "mlst",
                 "fastp", "filtlong", "streamlit"]:
        info["tools"][tool] = "found" if shutil.which(tool) else "missing"
    print(json.dumps(info, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Argparse plumbing
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bacpipe",
        description="BacPipe 2.0 — bacterial WGS pipeline (AMRFinderPlus + ONT + custom mcr/vanP)",
    )
    p.add_argument("-V", "--version", action="version",
                   version=f"bacpipe {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    sub = p.add_subparsers(dest="command", required=True, metavar="<command>")

    # amr
    amr = sub.add_parser("amr", help="Integrated AMR analysis (AMRFinderPlus + custom mcr/vanP)")
    amr.add_argument("--sample-id", required=True)
    amr.add_argument("--assembly", type=Path, required=True, help="Assembly FASTA")
    amr.add_argument("--protein", type=Path, default=None, help="Protein FASTA (Prokka *.faa)")
    amr.add_argument("--gff", type=Path, default=None, help="GFF (Prokka *.gff)")
    amr.add_argument("--species", default=None,
                     help="Species string for AMRFinderPlus --organism (e.g. 'Escherichia coli')")
    amr.add_argument("--amrfinder-db", type=Path, default=None)
    amr.add_argument("--mcr-db", type=Path, default=None)
    amr.add_argument("--vanp-db", type=Path, default=None)
    amr.add_argument("--threads", type=int, default=8)
    amr.add_argument("--output-dir", type=Path, default=None)
    amr.set_defaults(func=_cmd_amr)

    # amrfinder
    afp = sub.add_parser("amrfinder", help="Run AMRFinderPlus directly")
    afp.add_argument("--sample-id", required=True)
    afp.add_argument("--nucleotide", type=Path, help="Assembly FASTA")
    afp.add_argument("--protein", type=Path, help="Protein FASTA")
    afp.add_argument("--gff", type=Path, help="GFF (for --combined mode)")
    afp.add_argument("--combined", action="store_true",
                     help="Combined nucleotide+protein+GFF mode (most sensitive)")
    afp.add_argument("--organism", default=None)
    afp.add_argument("--threads", type=int, default=8)
    afp.add_argument("--db-dir", type=Path, default=None)
    afp.add_argument("--output-dir", type=Path, default=None)
    afp.add_argument("--update-db", action="store_true",
                     help="Run `amrfinder -u` before analysis")
    afp.set_defaults(func=_cmd_amrfinder)

    # update-db
    upd = sub.add_parser("update-db", help="Download/update the AMRFinderPlus database")
    upd.add_argument("--db-dir", type=Path, default=None,
                     help="Target database directory (default: amrfinder built-in)")
    upd.add_argument("--force", action="store_true", help="Force re-download")
    upd.set_defaults(func=_cmd_update_db)

    # gui
    gui = sub.add_parser("gui", help="Launch the Streamlit GUI")
    gui.add_argument("--port", type=int, default=8501)
    gui.add_argument("--headless", action="store_true",
                     help="Don't open a browser window automatically")
    gui.set_defaults(func=_cmd_gui)

    # info
    inf = sub.add_parser("info", help="Print version + environment summary")
    inf.set_defaults(func=_cmd_info)

    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(getattr(args, "verbose", False))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
