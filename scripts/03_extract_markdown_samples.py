"""
Extract markdown from parsed_docs.json for manual inspection.

Creates readable .md files for the 5 sample documents.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings


def main():
    # Load parsed docs
    data_dir = Path(settings.data_dir)
    parsed_json = data_dir / "processed" / "parsed_docs.json"
    
    print("📂 Loading parsed documents...")
    with open(parsed_json, 'r', encoding='utf-8') as f:
        docs = json.load(f)
    
    print(f"✓ Loaded {len(docs)} documents")
    print()
    
    # 5 documents to inspect (from Task 6)
    sample_ids = [
        "fda_warfarin_label_2025",
        "fda_amoxicillin_highlights_2025",
        "fda_ibuprofen_label_2024",
        "nice_amoxicillin_guideline_antimicrobial_2021",
        "nice_atorvastatin_guideline_cardiovascular_2023"
    ]
    
    # Create output directory
    output_dir = data_dir / "inspection_samples"
    output_dir.mkdir(exist_ok=True)
    
    print(f"📝 Extracting markdown for {len(sample_ids)} samples...")
    print()
    
    for doc_id in sample_ids:
        # Find document
        doc = next((d for d in docs if d['document_id'] == doc_id), None)
        
        if not doc:
            print(f"⚠️  Document not found: {doc_id}")
            continue
        
        # Extract markdown
        markdown = doc['parsed_markdown']
        
        # Save to file
        output_file = output_dir / f"{doc_id}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            # Add header with metadata
            f.write(f"# {doc_id}\n\n")
            f.write(f"**Authority:** {doc['authority_family']}\n\n")
            f.write(f"**Pages:** {doc['page_count']}\n\n")
            f.write(f"**Estimated table rows:** {doc['estimated_table_count']}\n\n")
            f.write(f"**Parse time:** {doc['parse_duration_seconds']}s\n\n")
            f.write("---\n\n")
            f.write(markdown)
        
        print(f"✓ {doc_id}")
        print(f"   → {output_file}")
        print(f"   → {doc['page_count']} pages, {doc['estimated_table_count']} table rows")
        print()
    
    print("=" * 60)
    print("✅ Extraction complete!")
    print()
    print(f"📂 Files saved to: {output_dir}")
    print()
    print("Next steps:")
    print("  1. Open data/inspection_samples/ in VS Code")
    print("  2. Open original PDFs side-by-side from data/raw/")
    print("  3. Check table preservation quality")
    print("  4. Fill out inspection checklist")


if __name__ == "__main__":
    main()
