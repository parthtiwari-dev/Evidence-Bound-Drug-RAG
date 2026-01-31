import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


# Locked drug set from Phase 0
LOCKED_DRUGS = {
    "atorvastatin", "lisinopril", "amoxicillin", "ciprofloxacin",
    "ibuprofen", "paracetamol", "acetaminophen", "metformin", "warfarin"
}

# Source folders
SOURCE_FOLDERS = ["fda", "nice", "who"]

# Keywords for document type classification
DRUG_CENTRIC_KEYWORDS = ["guideline", "label", "highlights", "bnf", "prescribing"]
CONDITION_GUIDELINE_KEYWORDS = ["management", "diagnosis", "bleeding", "osteoarthritis", "cardiovascular", "diabetes", "hypertension"]


def extract_year(filename: str) -> int | None:
    """Extract 4-digit year from filename."""
    match = re.search(r'\d{4}', filename)
    return int(match.group()) if match else None


def bucket_year(year: int | None) -> str:
    """Bucket year into timeframe categories."""
    if year is None:
        return "unknown"
    if year < 2015:
        return "pre_2015"
    elif 2015 <= year <= 2019:
        return "2015_2019"
    elif 2020 <= year <= 2024:
        return "2020_2024"
    else:
        return "post_2024"


def classify_document_type(filename: str) -> str:
    """Classify document based on filename keywords."""
    lower_name = filename.lower()
    
    if any(kw in lower_name for kw in DRUG_CENTRIC_KEYWORDS):
        return "drug_centric"
    elif any(kw in lower_name for kw in CONDITION_GUIDELINE_KEYWORDS):
        return "condition_guideline"
    else:
        return "other"


def check_naming_violations(filename: str, source: str) -> List[str]:
    """Check for naming convention violations."""
    violations = []
    
    # Check for spaces
    if ' ' in filename:
        violations.append("contains_spaces")
    
    # Check for year
    if not re.search(r'\d{4}', filename):
        violations.append("missing_year")
    
    # Check prefix
    expected_prefix = f"{source}_"
    if not filename.lower().startswith(expected_prefix):
        violations.append(f"missing_{source}_prefix")
    
    return violations


def check_non_locked_drugs(filename: str) -> List[str]:
    """Check for drug names not in locked set."""
    lower_name = filename.lower()
    detected_non_locked = []
    
    # Simple heuristic: look for common drug name patterns
    # This is intentionally conservative; false negatives are okay
    potential_drugs = re.findall(r'\b[a-z]{6,15}\b', lower_name)
    
    for word in potential_drugs:
        if word not in LOCKED_DRUGS and word not in ["guideline", "highlights", "label", "essential", "medicines", "management", "diagnosis"]:
            # Only flag if it looks like it could be a drug name (not too common a word)
            if word not in ["cardiovascular", "diabetes", "hypertension", "bleeding", "osteoarthritis", "prescribing", "antimicrobial", "antibiotics"]:
                detected_non_locked.append(word)
    
    return detected_non_locked


def inspect_dataset(data_dir: str = "./data/raw") -> Dict:
    """Inspect dataset and compute statistics."""
    
    # Initialize stats structure
    stats = {
        "total_files": 0,
        "total_pdfs": 0,
        "total_other_files": 0,
        "by_source": {},
        "size_stats": {"min_kb": float('inf'), "max_kb": 0, "avg_kb": 0},
        "estimated_tables": {"total_hits": 0, "by_source": {}},
        "document_types": {"drug_centric": 0, "condition_guideline": 0, "other": 0},
        "contract_checks": {
            "non_locked_drugs_detected": 0,
            "naming_violations": 0,
            "out_of_scope_docs": 0
        },
        "notes": [
            f"Inspection run on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "Table estimation uses heuristic keyword search in filenames",
            "Document type classification is filename- and folder-based",
            "Year extraction uses regex on filenames only"
        ]
    }
    
    # Initialize per-source stats
    for source in SOURCE_FOLDERS:
        stats["by_source"][source] = {
            "file_count": 0,
            "pdf_count": 0,
            "total_size_kb": 0.0,
            "avg_size_kb": 0.0,
            "min_size_kb": float('inf'),
            "max_size_kb": 0.0,
            "year_distribution": {
                "pre_2015": 0,
                "2015_2019": 0,
                "2020_2024": 0,
                "post_2024": 0
            }
        }
        stats["estimated_tables"]["by_source"][source] = 0

    
    all_sizes = []
    
    # Walk the data directory
    data_path = Path(data_dir)
    
    if not data_path.exists():
        print(f"Warning: {data_dir} does not exist")
        return stats
    
    for root, dirs, files in os.walk(data_path):
        root_path = Path(root)
        
        # Determine source from path
        source = None
        for src in SOURCE_FOLDERS:
            if src in root_path.parts:
                source = src
                break
        
        for filename in files:
            file_path = root_path / filename
            
            # Skip hidden files
            if filename.startswith('.'):
                continue
            
            stats["total_files"] += 1
            
            # Get file size in KB
            size_kb = file_path.stat().st_size / 1024
            all_sizes.append(size_kb)
            
            # Check if PDF
            is_pdf = filename.lower().endswith('.pdf')
            if is_pdf:
                stats["total_pdfs"] += 1
            else:
                stats["total_other_files"] += 1
                stats["contract_checks"]["out_of_scope_docs"] += 1
            
            # Update per-source stats
            if source:
                source_stats = stats["by_source"][source]
                source_stats["file_count"] += 1
                
                if is_pdf:
                    source_stats["pdf_count"] += 1
                
                source_stats["total_size_kb"] += size_kb
                source_stats["min_size_kb"] = min(source_stats["min_size_kb"], size_kb)
                source_stats["max_size_kb"] = max(source_stats["max_size_kb"], size_kb)
                
                # Year distribution
                year = extract_year(filename)
                year_bucket = bucket_year(year)
                if year_bucket != "unknown":
                    source_stats["year_distribution"][year_bucket] += 1
                
                # Estimated tables
                if "table" in filename.lower():
                    stats["estimated_tables"]["total_hits"] += 1
                    stats["estimated_tables"]["by_source"][source] += 1
                
                # Document type classification
                doc_type = classify_document_type(filename)
                stats["document_types"][doc_type] += 1
                
                # Contract checks
                violations = check_naming_violations(filename, source)
                if violations:
                    stats["contract_checks"]["naming_violations"] += 1
                
                non_locked = check_non_locked_drugs(filename)
                if non_locked:
                    stats["contract_checks"]["non_locked_drugs_detected"] += len(non_locked)
            else:
                stats["contract_checks"]["out_of_scope_docs"] += 1
    
    # Compute averages
    for source in SOURCE_FOLDERS:
        source_stats = stats["by_source"][source]
        if source_stats["pdf_count"] > 0:
            source_stats["avg_size_kb"] = source_stats["total_size_kb"] / source_stats["pdf_count"]
        
        # Handle edge case of no files
        if source_stats["min_size_kb"] == float('inf'):
            source_stats["min_size_kb"] = 0.0
    
    # Global size stats
    if all_sizes:
        stats["size_stats"]["min_kb"] = min(all_sizes)
        stats["size_stats"]["max_kb"] = max(all_sizes)
        stats["size_stats"]["avg_kb"] = sum(all_sizes) / len(all_sizes)
    else:
        stats["size_stats"]["min_kb"] = 0.0
    
    return stats


def print_summary(stats: Dict):
    """Print human-readable summary."""
    print("\n" + "="*60)
    print("DATASET INSPECTION SUMMARY")
    print("="*60)
    
    print(f"\n📊 Global Stats:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total PDFs: {stats['total_pdfs']}")
    print(f"  Other files: {stats['total_other_files']}")
    
    print(f"\n📁 By Source:")
    for source in SOURCE_FOLDERS:
        src_stats = stats["by_source"][source]
        print(f"  {source.upper()}: {src_stats['pdf_count']} PDFs, avg {src_stats['avg_size_kb']:.1f} KB")
    
    print(f"\n📏 Size Stats (all files):")
    print(f"  Min: {stats['size_stats']['min_kb']:.1f} KB")
    print(f"  Avg: {stats['size_stats']['avg_kb']:.1f} KB")
    print(f"  Max: {stats['size_stats']['max_kb']:.1f} KB")
    
    print(f"\n📋 Document Types:")
    print(f"  Drug-centric: {stats['document_types']['drug_centric']}")
    print(f"  Condition guidelines: {stats['document_types']['condition_guideline']}")
    print(f"  Other: {stats['document_types']['other']}")
    
    print(f"\n⚠️  Contract Checks:")
    print(f"  Naming violations: {stats['contract_checks']['naming_violations']}")
    print(f"  Non-locked drugs detected: {stats['contract_checks']['non_locked_drugs_detected']}")
    print(f"  Out-of-scope docs: {stats['contract_checks']['out_of_scope_docs']}")
    
    print("\n" + "="*60)
    print(f"✅ Stats written to: data/dataset_stats.json")
    print("="*60 + "\n")


def main():
    """Main execution."""
    print("Starting dataset inspection...")
    
    # Run inspection
    stats = inspect_dataset("./data/raw")
    
    # Write JSON
    output_path = Path("./data/dataset_stats.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    
    # Print summary
    print_summary(stats)


if __name__ == "__main__":
    main()
