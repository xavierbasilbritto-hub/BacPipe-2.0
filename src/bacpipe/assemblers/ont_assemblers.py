# BacPipe 2.0 - ONT Assembler Modules
# Long-read assembly support for Oxford Nanopore Technologies
# Basil Britto Xavier — DRAIGON Project

import os
import sys
import subprocess
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import tempfile
from enum import Enum

class ONTAssembler(Enum):
    FLYE = "flye"
    CANU = "canu"  
    RAVEN = "raven"
    MINIASM = "miniasm"

class PolishingTool(Enum):
    MEDAKA = "medaka"
    RACON = "racon"
    NANOPOLISH = "nanopolish"

@dataclass
class ONTAssemblyConfig:
    """Configuration for ONT assembly"""
    assembler: ONTAssembler
    genome_size: str = "5m"  # Estimated genome size (e.g., "5m" for 5Mb)
    min_read_length: int = 1000
    coverage_cutoff: int = 5
    polishing_rounds: int = 2
    polishing_tool: PolishingTool = PolishingTool.MEDAKA
    threads: int = 8
    memory: str = "32G"
    keep_intermediate: bool = False

class ONTAssemblyManager:
    """Manager for ONT assembly workflows"""
    
    def __init__(self, config: ONTAssemblyConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for ONT assembly"""
        logger = logging.getLogger("ONTAssembly")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    async def run_assembly(self, input_reads: str, output_dir: str, sample_id: str) -> Dict:
        """Main assembly workflow for ONT reads"""
        self.logger.info(f"🧬 Starting ONT assembly with {self.config.assembler.value} for {sample_id}")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Quality control and filtering
        filtered_reads = await self._quality_filter(input_reads, output_path, sample_id)
        
        # Step 2: Assembly
        raw_assembly = await self._run_assembler(filtered_reads, output_path, sample_id)
        
        # Step 3: Polishing (optional)
        if self.config.polishing_rounds > 0:
            polished_assembly = await self._polish_assembly(
                raw_assembly, filtered_reads, output_path, sample_id
            )
        else:
            polished_assembly = raw_assembly
        
        # Step 4: Assembly assessment
        assembly_stats = await self._assess_assembly(polished_assembly, output_path, sample_id)
        
        # Step 5: Generate report
        results = {
            "sample_id": sample_id,
            "assembler": self.config.assembler.value,
            "input_reads": input_reads,
            "filtered_reads": str(filtered_reads),
            "raw_assembly": str(raw_assembly),
            "final_assembly": str(polished_assembly),
            "assembly_stats": assembly_stats,
            "config": {
                "genome_size": self.config.genome_size,
                "min_read_length": self.config.min_read_length,
                "polishing_rounds": self.config.polishing_rounds,
                "polishing_tool": self.config.polishing_tool.value
            }
        }
        
        # Save results
        results_file = output_path / f"{sample_id}_ont_assembly_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"✅ ONT assembly completed for {sample_id}")
        return results
    
    async def _quality_filter(self, input_reads: str, output_dir: Path, sample_id: str) -> Path:
        """Quality filtering using filtlong"""
        filtered_file = output_dir / f"{sample_id}_filtered.fastq.gz"
        
        cmd = [
            "filtlong",
            "--min_length", str(self.config.min_read_length),
            "--keep_percent", "90",  # Keep top 90% of reads by quality
            "--target_bases", "500000000",  # Target ~500Mb for bacterial genomes
            input_reads
        ]
        
        self.logger.info(f"🔧 Running filtlong: {' '.join(cmd)}")
        
        with open(filtered_file, 'w') as outf:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=outf,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
        if process.returncode != 0:
            raise Exception(f"filtlong failed: {stderr.decode()}")
            
        return filtered_file
    
    async def _run_assembler(self, input_reads: Path, output_dir: Path, sample_id: str) -> Path:
        """Run the specified ONT assembler"""
        if self.config.assembler == ONTAssembler.FLYE:
            return await self._run_flye(input_reads, output_dir, sample_id)
        elif self.config.assembler == ONTAssembler.CANU:
            return await self._run_canu(input_reads, output_dir, sample_id)
        elif self.config.assembler == ONTAssembler.RAVEN:
            return await self._run_raven(input_reads, output_dir, sample_id)
        elif self.config.assembler == ONTAssembler.MINIASM:
            return await self._run_miniasm(input_reads, output_dir, sample_id)
        else:
            raise ValueError(f"Unsupported assembler: {self.config.assembler}")
    
    async def _run_flye(self, input_reads: Path, output_dir: Path, sample_id: str) -> Path:
        """Run Flye assembler - excellent for bacterial genomes"""
        flye_dir = output_dir / f"{sample_id}_flye"
        
        cmd = [
            "flye",
            "--nano-raw", str(input_reads),  # For raw ONT reads
            "--out-dir", str(flye_dir),
            "--genome-size", self.config.genome_size,
            "--threads", str(self.config.threads),
            "--iterations", "2",  # Assembly iterations
            "--min-overlap", "5000",  # Minimum overlap for bacterial genomes
        ]
        
        self.logger.info(f"🔧 Running Flye: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Flye failed: {stderr.decode()}")
        
        assembly_file = flye_dir / "assembly.fasta"
        final_assembly = output_dir / f"{sample_id}_flye_assembly.fasta"
        
        # Copy and rename assembly
        import shutil
        shutil.copy2(assembly_file, final_assembly)
        
        return final_assembly
    
    async def _run_canu(self, input_reads: Path, output_dir: Path, sample_id: str) -> Path:
        """Run Canu assembler - high quality but slower"""
        canu_dir = output_dir / f"{sample_id}_canu"
        canu_dir.mkdir(exist_ok=True)
        
        cmd = [
            "canu",
            "-p", sample_id,  # Prefix for output files
            "-d", str(canu_dir),  # Output directory
            f"genomeSize={self.config.genome_size}",
            f"maxThreads={self.config.threads}",
            f"maxMemory={self.config.memory}",
            "correctedErrorRate=0.16",  # For bacterial genomes
            "minOverlapLength=500",
            f"-nanopore", str(input_reads)
        ]
        
        self.logger.info(f"🔧 Running Canu: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Canu failed: {stderr.decode()}")
        
        assembly_file = canu_dir / f"{sample_id}.contigs.fasta"
        final_assembly = output_dir / f"{sample_id}_canu_assembly.fasta"
        
        import shutil
        shutil.copy2(assembly_file, final_assembly)
        
        return final_assembly
    
    async def _run_raven(self, input_reads: Path, output_dir: Path, sample_id: str) -> Path:
        """Run Raven assembler - fast and memory efficient"""
        final_assembly = output_dir / f"{sample_id}_raven_assembly.fasta"
        
        cmd = [
            "raven",
            "--threads", str(self.config.threads),
            "--disable-checkpoints",  # For faster assembly
            str(input_reads)
        ]
        
        self.logger.info(f"🔧 Running Raven: {' '.join(cmd)}")
        
        with open(final_assembly, 'w') as outf:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=outf,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
        if process.returncode != 0:
            raise Exception(f"Raven failed: {stderr.decode()}")
        
        return final_assembly
    
    async def _run_miniasm(self, input_reads: Path, output_dir: Path, sample_id: str) -> Path:
        """Run miniasm assembler - ultra-fast but requires polishing"""
        miniasm_dir = output_dir / f"{sample_id}_miniasm"
        miniasm_dir.mkdir(exist_ok=True)
        
        # Step 1: Find overlaps with minimap2
        paf_file = miniasm_dir / f"{sample_id}.paf"
        overlap_cmd = [
            "minimap2",
            "-x", "ava-ont",  # ONT all-vs-all preset
            "-t", str(self.config.threads),
            str(input_reads),
            str(input_reads)
        ]
        
        with open(paf_file, 'w') as outf:
            process = await asyncio.create_subprocess_exec(
                *overlap_cmd,
                stdout=outf,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"minimap2 overlap detection failed: {stderr.decode()}")
        
        # Step 2: Assembly with miniasm
        gfa_file = miniasm_dir / f"{sample_id}.gfa"
        assembly_cmd = [
            "miniasm",
            "-f", str(input_reads),
            str(paf_file)
        ]
        
        with open(gfa_file, 'w') as outf:
            process = await asyncio.create_subprocess_exec(
                *assembly_cmd,
                stdout=outf,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"miniasm assembly failed: {stderr.decode()}")
        
        # Convert GFA to FASTA
        final_assembly = output_dir / f"{sample_id}_miniasm_assembly.fasta"
        await self._gfa_to_fasta(gfa_file, final_assembly)
        
        return final_assembly
    
    async def _gfa_to_fasta(self, gfa_file: Path, fasta_file: Path):
        """Convert GFA format to FASTA"""
        with open(gfa_file, 'r') as inf, open(fasta_file, 'w') as outf:
            for line in inf:
                if line.startswith('S'):  # Sequence line in GFA
                    parts = line.strip().split('\t')
                    seq_id = parts[1]
                    sequence = parts[2]
                    outf.write(f">{seq_id}\n{sequence}\n")
    
    async def _polish_assembly(self, assembly: Path, reads: Path, output_dir: Path, sample_id: str) -> Path:
        """Polish assembly using medaka or racon"""
        if self.config.polishing_tool == PolishingTool.MEDAKA:
            return await self._polish_with_medaka(assembly, reads, output_dir, sample_id)
        elif self.config.polishing_tool == PolishingTool.RACON:
            return await self._polish_with_racon(assembly, reads, output_dir, sample_id)
        else:
            self.logger.warning("Polishing tool not implemented, returning unpolished assembly")
            return assembly
    
    async def _polish_with_medaka(self, assembly: Path, reads: Path, output_dir: Path, sample_id: str) -> Path:
        """Polish assembly using medaka"""
        medaka_dir = output_dir / f"{sample_id}_medaka"
        
        cmd = [
            "medaka_consensus",
            "-i", str(reads),
            "-d", str(assembly),
            "-o", str(medaka_dir),
            "-t", str(self.config.threads),
            "-m", "r941_min_hac_g507",  # Default ONT model, should be configurable
        ]
        
        self.logger.info(f"🔧 Running medaka polishing: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Medaka polishing failed: {stderr.decode()}")
        
        polished_assembly = medaka_dir / "consensus.fasta"
        final_assembly = output_dir / f"{sample_id}_polished_assembly.fasta"
        
        import shutil
        shutil.copy2(polished_assembly, final_assembly)
        
        return final_assembly
    
    async def _polish_with_racon(self, assembly: Path, reads: Path, output_dir: Path, sample_id: str) -> Path:
        """Polish assembly using racon"""
        racon_dir = output_dir / f"{sample_id}_racon"
        racon_dir.mkdir(exist_ok=True)
        
        current_assembly = assembly
        
        for round_num in range(self.config.polishing_rounds):
            self.logger.info(f"🔧 Running racon polishing round {round_num + 1}")
            
            # Map reads to current assembly
            sam_file = racon_dir / f"round_{round_num + 1}.sam"
            mapping_cmd = [
                "minimap2",
                "-ax", "map-ont",
                "-t", str(self.config.threads),
                str(current_assembly),
                str(reads)
            ]
            
            with open(sam_file, 'w') as outf:
                process = await asyncio.create_subprocess_exec(
                    *mapping_cmd,
                    stdout=outf,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Minimap2 mapping failed: {stderr.decode()}")
            
            # Polish with racon
            polished_file = racon_dir / f"round_{round_num + 1}_polished.fasta"
            racon_cmd = [
                "racon",
                str(reads),
                str(sam_file),
                str(current_assembly)
            ]
            
            with open(polished_file, 'w') as outf:
                process = await asyncio.create_subprocess_exec(
                    *racon_cmd,
                    stdout=outf,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Racon polishing failed: {stderr.decode()}")
            
            current_assembly = polished_file
        
        final_assembly = output_dir / f"{sample_id}_racon_polished_assembly.fasta"
        import shutil
        shutil.copy2(current_assembly, final_assembly)
        
        return final_assembly
    
    async def _assess_assembly(self, assembly: Path, output_dir: Path, sample_id: str) -> Dict:
        """Assess assembly quality using basic metrics"""
        stats = {
            "assembly_file": str(assembly),
            "total_length": 0,
            "num_contigs": 0,
            "largest_contig": 0,
            "n50": 0,
            "gc_content": 0.0
        }
        
        # Parse assembly file
        contig_lengths = []
        total_bases = 0
        gc_count = 0
        
        try:
            with open(assembly, 'r') as f:
                current_seq = ""
                for line in f:
                    if line.startswith('>'):
                        if current_seq:
                            length = len(current_seq)
                            contig_lengths.append(length)
                            total_bases += length
                            gc_count += current_seq.count('G') + current_seq.count('C')
                        current_seq = ""
                    else:
                        current_seq += line.strip().upper()
                
                # Handle last sequence
                if current_seq:
                    length = len(current_seq)
                    contig_lengths.append(length)
                    total_bases += length
                    gc_count += current_seq.count('G') + current_seq.count('C')
            
            # Calculate statistics
            if contig_lengths:
                stats["total_length"] = total_bases
                stats["num_contigs"] = len(contig_lengths)
                stats["largest_contig"] = max(contig_lengths)
                stats["gc_content"] = round((gc_count / total_bases) * 100, 2) if total_bases > 0 else 0
                
                # Calculate N50
                sorted_lengths = sorted(contig_lengths, reverse=True)
                cumulative = 0
                for length in sorted_lengths:
                    cumulative += length
                    if cumulative >= total_bases / 2:
                        stats["n50"] = length
                        break
        
        except Exception as e:
            self.logger.error(f"Error calculating assembly statistics: {e}")
        
        self.logger.info(f"📊 Assembly statistics for {sample_id}:")
        self.logger.info(f"   Total length: {stats['total_length']:,} bp")
        self.logger.info(f"   Number of contigs: {stats['num_contigs']}")
        self.logger.info(f"   Largest contig: {stats['largest_contig']:,} bp")
        self.logger.info(f"   N50: {stats['n50']:,} bp")
        self.logger.info(f"   GC content: {stats['gc_content']}%")
        
        return stats

# Example usage and testing
async def main():
    """Example usage of ONT assembly pipeline"""
    
    # Configure ONT assembly
    config = ONTAssemblyConfig(
        assembler=ONTAssembler.FLYE,
        genome_size="5m",
        min_read_length=1000,
        polishing_rounds=1,
        polishing_tool=PolishingTool.MEDAKA,
        threads=8
    )
    
    # Create assembly manager
    manager = ONTAssemblyManager(config)
    
    # Example assembly (would need real files)
    sample_id = "DEMO_MRSA_ONT_001"
    input_reads = "/path/to/ont_reads.fastq.gz"  # Would be real path
    output_dir = f"output/{sample_id}"
    
    print("🧬 BacPipe 2.0 - ONT Assembly Module")
    print(f"📋 Sample: {sample_id}")
    print(f"🔧 Assembler: {config.assembler.value}")
    print(f"🛠️ Polishing: {config.polishing_tool.value}")
    print(f"💾 Output: {output_dir}")
    
    # Note: Actual assembly would require real input files
    # results = await manager.run_assembly(input_reads, output_dir, sample_id)

if __name__ == "__main__":
    asyncio.run(main())
