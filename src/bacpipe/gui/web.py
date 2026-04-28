"""
BacPipe 2.0 — Streamlit GUI.

A scientific dashboard wrapping the existing analysis modules. Lets the user:
  - Upload an assembly FASTA (and optionally a protein FASTA + GFF)
  - Pick a species for AMRFinderPlus --organism mapping
  - Run integrated AMR analysis (AMRFinderPlus + custom mcr/vanP BLAST)
  - View hits in interactive tables, drug-class summary chart, and download
    the raw TSV / JSON outputs

Launch with:
    bacpipe gui            # via the bacpipe CLI (recommended)
    bacpipe-gui            # console-script alias — re-execs under streamlit

The GUI shells out to the bioinformatics tools (`amrfinder`, `blastn`) — they
must be installed and on PATH (see scripts/install.sh).
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _streamlit_runtime_active() -> bool:
    """True iff this module is being imported by `streamlit run`."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


def _render_page() -> None:
    """Render the Streamlit page. Must only be called under `streamlit run`."""
    import streamlit as st

    from bacpipe import __version__
    from bacpipe.analysis.amrfinderplus import AMRFinderOrganism
    from bacpipe.analysis.integrated_amr import IntegratedAMRAnalyser

    st.set_page_config(
        page_title="BacPipe 2.0",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🧬 BacPipe 2.0")
    st.caption(
        f"Bacterial WGS pipeline · AMRFinderPlus + ONT + custom mcr/vanP "
        f"· v{__version__} · DRAIGON Project"
    )

    # --- tool availability ----------------------------------------------------
    tools = {tool: shutil.which(tool) is not None for tool in ("amrfinder", "blastn")}
    with st.sidebar:
        st.subheader("Environment")
        for tool, present in tools.items():
            icon = "✅" if present else "❌"
            st.markdown(f"{icon} `{tool}`")
        if not tools["amrfinder"]:
            st.warning(
                "`amrfinder` is required. Install with:\n\n"
                "`conda install -c bioconda ncbi-amrfinderplus`"
            )

        st.divider()
        st.subheader("Run settings")
        threads = st.number_input("Threads", min_value=1, max_value=128, value=8)
        species_list = ["(auto / none)"] + sorted(
            o.value.replace("_", " ") for o in AMRFinderOrganism
        )
        species_choice = st.selectbox(
            "Species (AMRFinderPlus --organism)",
            species_list,
            help="Enables organism-specific point-mutation calling.",
        )
        species_arg = None if species_choice == "(auto / none)" else species_choice

        amrfinder_db = st.text_input(
            "AMRFinderPlus DB dir (optional)",
            value="",
            help="Leave blank to use amrfinder's built-in default location.",
        )
        mcr_db = st.text_input("Custom mcr DB FASTA (optional)", value="")
        vanp_db = st.text_input("Custom vanP DB FASTA (optional)", value="")

    # --- inputs ---------------------------------------------------------------
    st.subheader("1. Input")
    col_a, col_b = st.columns(2)
    with col_a:
        sample_id = st.text_input("Sample ID", value="SAMPLE_001")
        assembly_upload = st.file_uploader(
            "Assembly FASTA (required)",
            type=["fa", "fasta", "fna"],
        )
    with col_b:
        protein_upload = st.file_uploader(
            "Protein FASTA (optional, e.g. Prokka *.faa)",
            type=["faa", "fa", "fasta"],
        )
        gff_upload = st.file_uploader(
            "GFF (optional, for combined mode)",
            type=["gff", "gff3"],
        )

    st.subheader("2. Run")
    run_clicked = st.button(
        "Run integrated AMR analysis",
        type="primary",
        disabled=not (assembly_upload and tools["amrfinder"]),
    )

    def _save_upload(upload, target_dir: Path) -> Path | None:
        if upload is None:
            return None
        target = target_dir / upload.name
        with open(target, "wb") as fh:
            fh.write(upload.getbuffer())
        return target

    def _hits_to_records(hits) -> list[dict]:
        return [dataclasses.asdict(h) for h in hits]

    if run_clicked and assembly_upload:
        workdir = Path(tempfile.mkdtemp(prefix=f"bacpipe_{sample_id}_"))
        st.info(f"Working directory: `{workdir}`")

        asm_path = _save_upload(assembly_upload, workdir)
        pro_path = _save_upload(protein_upload, workdir)
        gff_path = _save_upload(gff_upload, workdir)

        analyser = IntegratedAMRAnalyser(
            amrfinder_db_dir=Path(amrfinder_db) if amrfinder_db else None,
            custom_mcr_db=Path(mcr_db) if mcr_db else None,
            custom_vanp_db=Path(vanp_db) if vanp_db else None,
            threads=int(threads),
        )

        with st.spinner("Running AMRFinderPlus + custom mcr/vanP screens…"):
            try:
                profile = asyncio.run(
                    analyser.analyse(
                        sample_id=sample_id,
                        assembly_fasta=asm_path,
                        protein_fasta=pro_path,
                        gff_file=gff_path,
                        species=species_arg,
                        output_dir=workdir / "results",
                    )
                )
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")
                st.stop()

        st.success(f"Done — {profile.total_resistance_genes} AMR genes detected.")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("AMR genes", profile.total_resistance_genes)
        m2.metric("mcr hits", len(profile.mcr_hits))
        m3.metric("vanP hits", len(profile.vanP_hits))
        m4.metric("Colistin call", profile.colistin_resistance_call)
        m5.metric("Vancomycin call", profile.vancomycin_resistance_call)

        st.markdown(
            f"**AMRFinderPlus**  software=`{profile.amrfinderplus_software}` · "
            f"db=`{profile.amrfinderplus_database}` · "
            f"organism=`{profile.organism_used or 'none'}` · "
            f"confidence={profile.confidence_score}"
        )

        if profile.drug_class_summary:
            st.subheader("Drug-class summary")
            st.bar_chart(profile.drug_class_summary)

        tab_amr, tab_mcr, tab_van, tab_pmut, tab_vir = st.tabs(
            ["All AMR hits", "mcr", "van*", "Point mutations", "Virulence"]
        )
        with tab_amr:
            if profile.integrated_hits:
                st.dataframe(_hits_to_records(profile.integrated_hits),
                             use_container_width=True)
            else:
                st.info("No AMR hits.")
        with tab_mcr:
            if profile.mcr_hits:
                st.dataframe(_hits_to_records(profile.mcr_hits),
                             use_container_width=True)
            else:
                st.info("No mcr hits.")
        with tab_van:
            if profile.van_hits:
                st.dataframe(_hits_to_records(profile.van_hits),
                             use_container_width=True)
            else:
                st.info("No van* hits.")
        with tab_pmut:
            if profile.point_mutations:
                st.dataframe(_hits_to_records(profile.point_mutations),
                             use_container_width=True)
            else:
                st.info("No point mutations called. (Set --organism for this.)")
        with tab_vir:
            if profile.virulence_factors:
                st.dataframe(_hits_to_records(profile.virulence_factors),
                             use_container_width=True)
            else:
                st.info("No virulence factors reported.")

        st.subheader("Downloads")
        profile_json = json.dumps(dataclasses.asdict(profile), indent=2, default=str)
        st.download_button(
            "Integrated AMR profile (JSON)",
            profile_json,
            file_name=f"{sample_id}.integrated_amr.json",
            mime="application/json",
        )
        afp_tsv = workdir / "results" / "amrfinderplus" / f"{sample_id}.amrfinder.tsv"
        if afp_tsv.exists():
            st.download_button(
                "Raw AMRFinderPlus TSV",
                afp_tsv.read_bytes(),
                file_name=afp_tsv.name,
                mime="text/tab-separated-values",
            )

    elif run_clicked and not tools["amrfinder"]:
        st.error("Cannot run — `amrfinder` is not installed on PATH.")

    else:
        st.info(
            "Upload an assembly FASTA on the left, then click **Run**. "
            "The analysis runs AMRFinderPlus and (if databases are provided) "
            "custom mcr / vanP BLAST screens."
        )


def main() -> None:
    """Console-script entry point (`bacpipe-gui`).

    Re-execs under `streamlit run` so the page body actually has a runtime.
    """
    if shutil.which("streamlit") is None:
        sys.stderr.write(
            "ERROR: streamlit not installed. "
            "Run: pip install 'bacpipe[gui]' or pip install streamlit\n"
        )
        sys.exit(1)
    sys.exit(subprocess.call(["streamlit", "run", __file__]))


if _streamlit_runtime_active():
    _render_page()
elif __name__ == "__main__":
    main()
