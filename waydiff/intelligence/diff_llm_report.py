import os
import json
import requests
import logging

logger = logging.getLogger(__name__)

MAX_ENDPOINTS = 15
MAX_SCRIPTS = 10
MAX_INPUTS = 10


# ==========================================================
# SUMMARY EXTRACTION
# ==========================================================

def build_summary(output_folder):

    structured_files = [
        f for f in os.listdir(output_folder)
        if (
            f.startswith("snapshot_") or
            f.startswith("structured_diff_")
        ) and f.endswith(".json")
    ]

    endpoints = set()
    scripts = set()
    inputs = set()

    for file in structured_files:

        path = os.path.join(output_folder, file)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for key in ["authentication_routes", "admin_routes", "api_routes"]:
                for item in data.get(key, {}).get("added", []):
                    if isinstance(item, str):
                        endpoints.add(item)

            for item in data.get("external_scripts", {}).get("added", []):
                if isinstance(item, str):
                    scripts.add(item)

            for item in data.get("sensitive_inputs", {}).get("added", []):
                if isinstance(item, dict):
                    name = item.get("name") or item.get("type", "unknown")
                    inputs.add(f"{item.get('type','input')}:{name}")
                elif isinstance(item, str):
                    inputs.add(item)

            for item in data.get("file_inputs", {}).get("added", []):
                if isinstance(item, dict):
                    inputs.add(f"file:{item.get('name','unknown')}")
                elif isinstance(item, str):
                    inputs.add(item)

        except Exception as e:
            logger.warning(f"Error reading {file}: {e}")

    summary = "=== SECURITY SURFACE DRIFT SUMMARY ===\n\n"

    if endpoints:
        summary += "New Endpoints:\n"
        for e in list(endpoints)[:MAX_ENDPOINTS]:
            summary += f"- {e}\n"
        summary += "\n"

    if scripts:
        summary += "New External Scripts:\n"
        for s in list(scripts)[:MAX_SCRIPTS]:
            summary += f"- {s}\n"
        summary += "\n"

    if inputs:
        summary += "New Sensitive Inputs:\n"
        for i in list(inputs)[:MAX_INPUTS]:
            summary += f"- {i}\n"
        summary += "\n"

    summary += "=== END SUMMARY ===\n"

    return summary, bool(endpoints or scripts or inputs)


# ==========================================================
# HEURISTIC FALLBACK
# ==========================================================

def generate_heuristic_analysis(summary_text):

    report = "HEURISTIC SECURITY ANALYSIS\n"
    report += "=" * 60 + "\n\n"
    report += summary_text + "\n"
    report += "\nSECURITY RECOMMENDATIONS:\n"
    report += "-" * 60 + "\n"
    report += "1. Test new endpoints\n"
    report += "2. Review authentication routes\n"
    report += "3. Test file uploads\n"
    report += "4. Check authorization\n"
    report += "5. Review security headers\n"

    return report


# ==========================================================
# MAIN REPORT GENERATOR
# ==========================================================

def generate_llm_report(output_folder, backend="heuristic", model=None, timeout=60):

    try:

        summary_text, has_changes = build_summary(output_folder)

        if not has_changes:
            logger.info("No changes detected")
            return None

        llm_output = generate_heuristic_analysis(summary_text)

        report_path = os.path.join(output_folder, "llm_security_report.txt")

        with open(report_path, "w", encoding="utf-8") as report:
            report.write("LLM SECURITY INTELLIGENCE REPORT\n")
            report.write("=" * 60 + "\n\n")
            report.write(llm_output)

        logger.info(f"✓ Report saved: {report_path}")

        return report_path

    except Exception as e:
        logger.exception("Error generating LLM report")
        return None