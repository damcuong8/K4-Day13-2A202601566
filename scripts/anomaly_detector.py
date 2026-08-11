#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

LOG_PATH = Path("data/logs.jsonl")
EVIDENCE_PATH = Path("submission/evidence/anomaly_detection_report.txt")

PII_DETECTORS = {
    "email": re.compile(r"[\w.-]+@[\w.-]+\.\w+"),
    "phone_vn": re.compile(r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)"),
    "cccd": re.compile(r"\b\d{12}\b"),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
}


def run_anomaly_detector() -> None:
    if not LOG_PATH.exists():
        print(f"Error: {LOG_PATH} not found.")
        sys.exit(1)

    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except Exception:
                pass

    anomalies = []
    latencies = []
    total_received = 0
    total_failed = 0
    total_cost = 0.0

    for idx, r in enumerate(records, 1):
        event = r.get("event")
        raw = json.dumps(r, ensure_ascii=False)

        # 1. Check PII leaks
        detected_pii = [name for name, detector in PII_DETECTORS.items() if detector.search(raw)]
        if detected_pii:
            anomalies.append({
                "type": "PII_LEAK_ANOMALY",
                "severity": "CRITICAL",
                "record_index": idx,
                "correlation_id": r.get("correlation_id", "UNKNOWN"),
                "details": f"PII leak detected: {detected_pii}",
            })

        # 2. Check Latency
        if event == "response_sent" and "latency_ms" in r:
            lat = r["latency_ms"]
            latencies.append(lat)
            if lat > 3000:
                anomalies.append({
                    "type": "HIGH_LATENCY_ANOMALY",
                    "severity": "WARNING" if lat <= 5000 else "CRITICAL",
                    "record_index": idx,
                    "correlation_id": r.get("correlation_id", "UNKNOWN"),
                    "details": f"Single request latency {lat}ms exceeds threshold (3000ms)",
                })

        # 3. Check Traffic & Error
        if event == "request_received":
            total_received += 1
        elif event == "request_failed":
            total_failed += 1
            anomalies.append({
                "type": "REQUEST_FAILED_ANOMALY",
                "severity": "CRITICAL",
                "record_index": idx,
                "correlation_id": r.get("correlation_id", "UNKNOWN"),
                "details": f"Request failed with error: {r.get('error_type', 'UnknownError')}",
            })

        # 4. Check Cost
        if event == "response_sent" and "cost_usd" in r:
            total_cost += r["cost_usd"]

    # Calculate aggregate SLO metrics
    error_rate_pct = (total_failed / total_received * 100.0) if total_received > 0 else 0.0
    if error_rate_pct > 2.0:
        anomalies.append({
            "type": "HIGH_ERROR_RATE_ANOMALY",
            "severity": "CRITICAL",
            "details": f"Overall Error Rate {error_rate_pct:.2f}% exceeds SLO threshold (2.0%)",
        })

    if total_cost > 2.50:
        anomalies.append({
            "type": "HIGH_COST_ANOMALY",
            "severity": "WARNING",
            "details": f"Total accumulated cost ${total_cost:.4f} exceeds budget threshold ($2.50)",
        })

    # Format output report
    report_lines = []
    report_lines.append("=== AUTOMATED ANOMALY DETECTION REPORT ===")
    report_lines.append(f"Analyzed Records: {len(records)}")
    report_lines.append(f"Total Requests: {total_received} | Failed: {total_failed} ({error_rate_pct:.2f}%)")
    report_lines.append(f"Total Cost: ${total_cost:.4f}")
    report_lines.append(f"Total Anomalies Detected: {len(anomalies)}")
    report_lines.append("-" * 50)

    if not anomalies:
        report_lines.append("[SYSTEM HEALTHY] No anomalies detected. All metrics satisfy SLO thresholds.")
    else:
        for idx, anomaly in enumerate(anomalies, 1):
            sev = anomaly["severity"]
            atype = anomaly["type"]
            det = anomaly["details"]
            cid = anomaly.get("correlation_id", "N/A")
            report_lines.append(f"{idx}. [{sev}] {atype} (Correlation ID: {cid})")
            report_lines.append(f"   -> {det}")

    report_text = "\n".join(report_lines)
    print(report_text)

    # Save evidence report
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(report_text, encoding="utf-8")
    print(f"\n[OK] Anomaly report saved to: {EVIDENCE_PATH}")


if __name__ == "__main__":
    run_anomaly_detector()
