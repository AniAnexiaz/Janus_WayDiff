import os
import json
from collections import defaultdict


def safe_get(diff_data, key, field="added"):
    return diff_data.get(key, {}).get(field, [])


def calculate_risk_score(category, value):

    value_lower = str(value).lower()
    score = 3

    if category in ["admin_routes", "authentication_routes"]:
        score = 8

    if category in ["file_inputs", "sensitive_inputs"]:
        score = 8

    if category == "security_headers":
        score = 7

    high_keywords = [
        "admin","upload","reset","password",
        "token","secret","internal","debug",
        "config","backup"
    ]

    if any(k in value_lower for k in high_keywords):
        score = max(score,8)

    return min(score,10)


def classify_severity(score):

    if score >= 8:
        return "HIGH"
    elif score >= 5:
        return "MEDIUM"

    return "LOW"


def pentest_recommendation(category):

    mapping = {
        "admin_routes":"Test access control and forced browsing.",
        "authentication_routes":"Test brute force and MFA bypass.",
        "api_routes":"Test auth, rate limiting, injection.",
        "forms":"Test CSRF and input validation.",
        "file_inputs":"Test upload validation and RCE.",
        "sensitive_inputs":"Test credential handling.",
        "external_scripts":"Check supply chain risk.",
        "query_parameters":"Test parameter tampering.",
        "hidden_fields":"Test hidden field manipulation.",
        "client_fetch_calls":"Test backend exposure.",
        "business_logic_indicators":"Test workflow abuse.",
        "security_headers":"Review header policy."
    }

    return mapping.get(category,"Review security impact.")


def generate_security_report(output_folder):

    structured_files = sorted([
        f for f in os.listdir(output_folder)
        if (
            f.startswith("snapshot_") or
            f.startswith("structured_diff_")
        ) and f.endswith(".json")
    ])

    if not structured_files:
        return None

    findings_by_severity = defaultdict(set)
    all_findings = []

    snapshot_sections = []

    for file in structured_files:

        path = os.path.join(output_folder,file)

        with open(path,"r",encoding="utf-8") as f:
            diff_data = json.load(f)

        snapshot_name = (
            file.replace("snapshot_","")
                .replace("structured_diff_","")
                .replace(".json","")
        )

        snapshot_report = []

        for category,data in diff_data.items():

            if category == "security_headers":

                for header in data.get("removed",{}):
                    score = 9
                    severity = "HIGH"

                    text = f"[security_headers] Removed: {header}"
                    entry = f"{severity} (Risk {score}/10): {text}"

                    findings_by_severity[severity].add(entry)
                    all_findings.append((score,entry))
                    snapshot_report.append(entry)

                continue

            added_items = safe_get(diff_data,category,"added")

            for item in added_items:

                score = calculate_risk_score(category,item)
                severity = classify_severity(score)

                recommendation = pentest_recommendation(category)

                text = f"[{category}] {item}"
                entry = f"{severity} (Risk {score}/10): {text}\n  → {recommendation}"

                findings_by_severity[severity].add(entry)
                all_findings.append((score,entry))
                snapshot_report.append(entry)

        snapshot_sections.append((snapshot_name,snapshot_report))

    report_path = os.path.join(output_folder,"security_report.txt")

    with open(report_path,"w",encoding="utf-8") as report:

        report.write("SECURITY DRIFT INTELLIGENCE REPORT\n")
        report.write("="*70+"\n\n")

        top = sorted(all_findings,reverse=True)[:5]

        report.write("TOP TESTING PRIORITIES\n")
        report.write("-"*50+"\n")

        for _,finding in top:
            report.write(f"{finding}\n\n")

        report.write("="*70+"\n\n")

        for snapshot_name,findings in snapshot_sections:

            report.write(f"Snapshot: {snapshot_name}\n")
            report.write("-"*50+"\n")

            for finding in findings:
                report.write(f"{finding}\n")

            report.write("\n")

    return report_path