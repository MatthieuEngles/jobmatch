#!/usr/bin/env python3
"""Integration test for cv-ingestion with Ollama."""

import os
import sys

# Set environment variables for Ollama BEFORE importing src modules
os.environ["LLM_TYPE"] = "ollama"
os.environ["LLM_ENDPOINT"] = "http://llm.molp.fr/v1"
os.environ["LLM_MODEL"] = "gemma3:4b"
os.environ["DEBUG"] = "true"

# Change to cv-ingestion directory (parent of scripts)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CV_INGESTION_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CV_INGESTION_DIR))
os.chdir(CV_INGESTION_DIR)

# Add paths for imports
sys.path.insert(0, CV_INGESTION_DIR)  # for 'src' package
sys.path.insert(0, PROJECT_ROOT)  # for 'shared' package


def test_pdf_extraction():
    """Test PDF text extraction without LLM."""
    from src.extractors import extract_text_from_pdf

    pdf_path = "data_test/CV_ENGLES_mai25.pdf"

    if not os.path.exists(pdf_path):
        print(f"ERROR: Test PDF not found at {pdf_path}")
        return False

    with open(pdf_path, "rb") as f:
        content = f.read()

    print(f"PDF size: {len(content)} bytes")

    try:
        text = extract_text_from_pdf(content)
        print(f"Extracted text length: {len(text)} chars")
        print("\n--- First 500 chars ---")
        print(text[:500])
        print("--- End preview ---\n")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_llm_analysis():
    """Test LLM analysis of extracted text."""
    return test_llm_analysis_with_output() is not None


def test_llm_analysis_with_output():
    """Test LLM analysis of extracted text and return output lines."""
    from src.extractors import extract_text_from_pdf
    from src.llm import analyze_cv_text

    output_lines = []

    pdf_path = "data_test/CV_ENGLES_mai25.pdf"

    if not os.path.exists(pdf_path):
        print(f"ERROR: Test PDF not found at {pdf_path}")
        return None

    with open(pdf_path, "rb") as f:
        content = f.read()

    # Extract text
    text = extract_text_from_pdf(content)
    output_lines.append(f"Extracted {len(text)} chars from PDF")
    print(output_lines[-1])

    # Analyze with LLM
    output_lines.append("\nSending to LLM for analysis...")
    output_lines.append(f"Using: {os.environ['LLM_TYPE']} / {os.environ['LLM_MODEL']}")
    output_lines.append(f"Endpoint: {os.environ['LLM_ENDPOINT']}")
    for line in output_lines[-3:]:
        print(line)

    try:
        extracted_lines = analyze_cv_text(text)
        output_lines.append(f"\nExtracted {len(extracted_lines)} lines from CV:")
        output_lines.append("-" * 50)
        print(output_lines[-2])
        print(output_lines[-1])

        # Group by content_type
        by_type: dict[str, list] = {}
        for line in extracted_lines:
            t = line.content_type.value
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(line.content)

        for content_type, items in by_type.items():
            header = f"\n[{content_type.upper()}] ({len(items)} items)"
            output_lines.append(header)
            print(header)
            for item in items:  # Show all items in output
                item_line = f"  - {item}"
                output_lines.append(item_line)
                # Print truncated version to console
                print(f"  - {item[:80]}{'...' if len(item) > 80 else ''}")

        return output_lines

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run integration tests."""
    output_lines = []

    def log(msg):
        print(msg)
        output_lines.append(msg)

    log("=" * 60)
    log("CV-INGESTION INTEGRATION TEST")
    log("=" * 60)

    # Already changed to script directory at module load

    log("\n[1/2] Testing PDF extraction...")
    if not test_pdf_extraction():
        log("FAILED: PDF extraction")
        return 1

    log("\n[2/2] Testing LLM analysis...")
    result = test_llm_analysis_with_output()
    if result is None:
        log("FAILED: LLM analysis")
        return 1

    # Add LLM results to output
    output_lines.extend(result)

    log("\n" + "=" * 60)
    log("ALL TESTS PASSED!")
    log("=" * 60)

    # Write output to file
    output_path = "data_test/output.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"\nOutput saved to {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
