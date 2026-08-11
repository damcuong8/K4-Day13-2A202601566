from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from fastapi.responses import HTMLResponse

LOG_PATH = Path("data/logs.jsonl")


def compute_dashboard_stats() -> dict[str, Any]:
    if not LOG_PATH.exists():
        return {
            "latency": {"p50": 0, "p95": 0, "p99": 0, "threshold_p95": 3000, "status": "NO_DATA"},
            "traffic": {"total_requests": 0, "rate_per_minute": 0, "threshold_rate": 1.0, "status": "NO_DATA"},
            "errors": {"error_rate_pct": 0, "total_failed": 0, "breakdown": {}, "threshold_rate": 2.0, "status": "NO_DATA"},
            "cost": {"total_usd": 0, "threshold_total": 2.50, "status": "NO_DATA"},
            "tokens": {"tokens_in": 0, "tokens_out": 0, "total_tokens": 0, "threshold_total": 50000, "status": "NO_DATA"},
            "quality": {"mean_score": 0, "threshold_mean": 0.75, "status": "NO_DATA"},
            "records_count": 0,
        }

    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except Exception:
                pass

    # Latencies
    latencies = [r["latency_ms"] for r in records if r.get("event") == "response_sent" and "latency_ms" in r]
    latencies.sort()

    def percentile(lst: list[float | int], p: float) -> float:
        if not lst:
            return 0.0
        k = (len(lst) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(lst[int(k)])
        d0 = lst[int(f)] * (c - k)
        d1 = lst[int(c)] * (k - f)
        return float(d0 + d1)

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)

    # Traffic
    requests_received = [r for r in records if r.get("event") == "request_received"]
    requests_failed = [r for r in records if r.get("event") == "request_failed"]
    total_received = len(requests_received)
    total_failed = len(requests_failed)

    # Error rate & breakdown
    error_rate_pct = (total_failed / total_received * 100.0) if total_received > 0 else 0.0
    error_breakdown = {}
    for r in requests_failed:
        err = r.get("error_type", "UnknownError")
        error_breakdown[err] = error_breakdown.get(err, 0) + 1

    # Cost
    costs = [r.get("cost_usd", 0.0) for r in records if r.get("event") == "response_sent"]
    total_cost = sum(costs)

    # Tokens
    tokens_in = sum(r.get("tokens_in", 0) for r in records if r.get("event") == "response_sent")
    tokens_out = sum(r.get("tokens_out", 0) for r in records if r.get("event") == "response_sent")

    # Quality
    quality_scores = [
        r.get("quality_score")
        for r in records
        if r.get("event") == "response_sent" and r.get("quality_score") is not None
    ]
    mean_quality = (sum(quality_scores) / len(quality_scores)) if quality_scores else 0.0

    return {
        "latency": {
            "p50": round(p50, 1),
            "p95": round(p95, 1),
            "p99": round(p99, 1),
            "threshold_p95": 3000,
            "status": "PASS" if p95 <= 3000 else "EXCEEDED",
        },
        "traffic": {
            "total_requests": total_received,
            "rate_per_minute": round(total_received / 60.0, 2) if total_received > 0 else 0.0,
            "threshold_rate": 1.0,
            "status": "PASS" if total_received >= 1 else "EXCEEDED",
        },
        "errors": {
            "error_rate_pct": round(error_rate_pct, 2),
            "total_failed": total_failed,
            "breakdown": error_breakdown,
            "threshold_rate": 2.0,
            "status": "PASS" if error_rate_pct <= 2.0 else "EXCEEDED",
        },
        "cost": {
            "total_usd": round(total_cost, 6),
            "threshold_total": 2.50,
            "status": "PASS" if total_cost <= 2.50 else "EXCEEDED",
        },
        "tokens": {
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "threshold_total": 50000,
            "status": "PASS" if (tokens_in + tokens_out) <= 50000 else "EXCEEDED",
        },
        "quality": {
            "mean_score": round(mean_quality, 3),
            "threshold_mean": 0.75,
            "status": "PASS" if mean_quality >= 0.75 else "EXCEEDED",
        },
        "records_count": len(records),
    }


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Day 13 AI Observability Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-card: #151c2c;
            --border-color: #242f47;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-cyan: #06b6d4;
            --accent-emerald: #10b981;
            --accent-rose: #f43f5e;
            --accent-amber: #f59e0b;
            --accent-purple: #a855f7;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            padding: 24px;
            min-height: 100vh;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-title h1 {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .live-badge {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-emerald);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid rgba(16, 185, 129, 0.3);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-emerald);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 20px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s, border-color 0.2s;
        }

        .card:hover {
            border-color: rgba(56, 189, 248, 0.4);
            transform: translateY(-2px);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .card-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .badge-pass {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-emerald);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-warn {
            background: rgba(244, 63, 94, 0.15);
            color: var(--accent-rose);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            border: 1px solid rgba(244, 63, 94, 0.3);
        }

        .stat-value {
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 8px;
            display: flex;
            align-items: baseline;
            gap: 8px;
        }

        .stat-unit {
            font-size: 14px;
            font-weight: 500;
            color: var(--text-secondary);
        }

        .threshold-text {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 16px;
        }

        .metric-subgrid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            background: rgba(15, 23, 42, 0.6);
            padding: 10px;
            border-radius: 8px;
            margin-top: 12px;
        }

        .submetric {
            text-align: center;
        }

        .submetric-title {
            font-size: 11px;
            color: var(--text-secondary);
        }

        .submetric-val {
            font-size: 15px;
            font-weight: 700;
            color: var(--text-primary);
        }

        .chart-container {
            height: 180px;
            position: relative;
            margin-top: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">
            <h1>Day 13 Observability Dashboard</h1>
            <div class="live-badge">
                <div class="pulse-dot"></div>
                LIVE REFRESH (15s)
            </div>
        </div>
        <div style="font-size: 13px; color: var(--text-secondary);">
            Contract: <span style="color: var(--accent-emerald); font-weight: 600;">6/6 Panels Active</span>
        </div>
    </div>

    <div class="grid">
        <!-- 1. Latency -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">1. Latency Percentiles</span>
                <span id="latency-badge" class="badge-pass">PASS</span>
            </div>
            <div class="stat-value">
                <span id="p95-val">0</span>
                <span class="stat-unit">ms (P95)</span>
            </div>
            <div class="threshold-text">Ngưỡng SLO: P95 &le; 3000ms</div>
            <div class="metric-subgrid">
                <div class="submetric">
                    <div class="submetric-title">P50</div>
                    <div class="submetric-val" id="p50-val">0 ms</div>
                </div>
                <div class="submetric">
                    <div class="submetric-title">P95</div>
                    <div class="submetric-val" id="p95-sub">0 ms</div>
                </div>
                <div class="submetric">
                    <div class="submetric-title">P99</div>
                    <div class="submetric-val" id="p99-val">0 ms</div>
                </div>
            </div>
        </div>

        <!-- 2. Traffic -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">2. Request Traffic</span>
                <span id="traffic-badge" class="badge-pass">PASS</span>
            </div>
            <div class="stat-value">
                <span id="traffic-reqs">0</span>
                <span class="stat-unit">total requests</span>
            </div>
            <div class="threshold-text">Ngưỡng: Rate &ge; 1 req/phút</div>
            <div class="metric-subgrid">
                <div class="submetric" style="grid-column: span 3;">
                    <div class="submetric-title">Tần suất trung bình</div>
                    <div class="submetric-val" id="traffic-rate">0 req/min</div>
                </div>
            </div>
        </div>

        <!-- 3. Errors -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">3. Error Rate & Breakdown</span>
                <span id="errors-badge" class="badge-pass">PASS</span>
            </div>
            <div class="stat-value">
                <span id="error-rate">0.0%</span>
                <span class="stat-unit">error rate</span>
            </div>
            <div class="threshold-text">Ngưỡng SLO: Error rate &le; 2%</div>
            <div class="metric-subgrid">
                <div class="submetric">
                    <div class="submetric-title">Failed</div>
                    <div class="submetric-val" id="failed-count">0</div>
                </div>
                <div class="submetric" style="grid-column: span 2;">
                    <div class="submetric-title">Error Breakdown</div>
                    <div class="submetric-val" id="error-breakdown">None</div>
                </div>
            </div>
        </div>

        <!-- 4. Cost -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">4. Cost Over Time</span>
                <span id="cost-badge" class="badge-pass">PASS</span>
            </div>
            <div class="stat-value">
                <span id="cost-total">$0.000</span>
                <span class="stat-unit">USD</span>
            </div>
            <div class="threshold-text">Ngưỡng: Total &le; $2.50 USD</div>
        </div>

        <!-- 5. Tokens -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">5. Tokens Consumption</span>
                <span id="tokens-badge" class="badge-pass">PASS</span>
            </div>
            <div class="stat-value">
                <span id="tokens-total">0</span>
                <span class="stat-unit">tokens</span>
            </div>
            <div class="threshold-text">Ngưỡng: Total &le; 50,000 tokens</div>
            <div class="metric-subgrid">
                <div class="submetric" style="grid-column: span 1.5;">
                    <div class="submetric-title">Tokens In</div>
                    <div class="submetric-val" id="tokens-in">0</div>
                </div>
                <div class="submetric" style="grid-column: span 1.5;">
                    <div class="submetric-title">Tokens Out</div>
                    <div class="submetric-val" id="tokens-out">0</div>
                </div>
            </div>
        </div>

        <!-- 6. Quality -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">6. Quality Proxy</span>
                <span id="quality-badge" class="badge-pass">PASS</span>
            </div>
            <div class="stat-value">
                <span id="quality-mean">0.00</span>
                <span class="stat-unit">/ 1.0 score</span>
            </div>
            <div class="threshold-text">Ngưỡng SLO: Mean &ge; 0.75</div>
        </div>
    </div>

    <script>
        async function updateDashboard() {
            try {
                const res = await fetch('/api/dashboard/stats');
                const data = await res.json();

                // Latency
                document.getElementById('p95-val').innerText = data.latency.p95;
                document.getElementById('p50-val').innerText = data.latency.p50 + ' ms';
                document.getElementById('p95-sub').innerText = data.latency.p95 + ' ms';
                document.getElementById('p99-val').innerText = data.latency.p99 + ' ms';
                setBadge('latency-badge', data.latency.status);

                // Traffic
                document.getElementById('traffic-reqs').innerText = data.traffic.total_requests;
                document.getElementById('traffic-rate').innerText = data.traffic.rate_per_minute + ' req/min';
                setBadge('traffic-badge', data.traffic.status);

                // Errors
                document.getElementById('error-rate').innerText = data.errors.error_rate_pct + '%';
                document.getElementById('failed-count').innerText = data.errors.total_failed;
                const errTypes = Object.keys(data.errors.breakdown);
                document.getElementById('error-breakdown').innerText = errTypes.length ? errTypes.join(', ') : 'None';
                setBadge('errors-badge', data.errors.status);

                // Cost
                document.getElementById('cost-total').innerText = '$' + data.cost.total_usd.toFixed(4);
                setBadge('cost-badge', data.cost.status);

                // Tokens
                document.getElementById('tokens-total').innerText = data.tokens.total_tokens.toLocaleString();
                document.getElementById('tokens-in').innerText = data.tokens.tokens_in.toLocaleString();
                document.getElementById('tokens-out').innerText = data.tokens.tokens_out.toLocaleString();
                setBadge('tokens-badge', data.tokens.status);

                // Quality
                document.getElementById('quality-mean').innerText = data.quality.mean_score.toFixed(2);
                setBadge('quality-badge', data.quality.status);

            } catch (err) {
                console.error('Failed to update dashboard:', err);
            }
        }

        function setBadge(id, status) {
            const badge = document.getElementById(id);
            if (status === 'PASS') {
                badge.className = 'badge-pass';
                badge.innerText = 'PASS';
            } else {
                badge.className = 'badge-warn';
                badge.innerText = 'EXCEEDED';
            }
        }

        updateDashboard();
        setInterval(updateDashboard, 15000);
    </script>
</body>
</html>
"""
