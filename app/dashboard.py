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
            "traffic": {"total_requests": 0, "rate_per_minute": 0, "threshold_rate": 1.0, "status": "NO_DATA", "series_labels": [], "series_values": []},
            "errors": {"error_rate_pct": 0, "total_failed": 0, "breakdown": {}, "threshold_rate": 2.0, "status": "NO_DATA"},
            "cost": {"total_usd": 0, "threshold_total": 2.50, "status": "NO_DATA", "cumulative_series": []},
            "tokens": {"tokens_in": 0, "tokens_out": 0, "total_tokens": 0, "threshold_total": 50000, "status": "NO_DATA"},
            "quality": {"mean_score": 0, "threshold_mean": 0.75, "status": "NO_DATA", "scores_distribution": []},
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

    # Time series aggregation for traffic & cost
    minute_buckets: dict[str, int] = {}
    cost_buckets: dict[str, float] = {}

    for r in records:
        ts = r.get("ts", "")
        if len(ts) >= 16:  # e.g. "2026-08-11T08:26"
            minute_key = ts[11:16]  # "08:26"
            if r.get("event") == "request_received":
                minute_buckets[minute_key] = minute_buckets.get(minute_key, 0) + 1
            if r.get("event") == "response_sent" and "cost_usd" in r:
                cost_buckets[minute_key] = cost_buckets.get(minute_key, 0.0) + r["cost_usd"]

    sorted_minutes = sorted(minute_buckets.keys()) if minute_buckets else ["00:00"]
    traffic_values = [minute_buckets.get(m, 0) for m in sorted_minutes]

    # Cumulative cost
    cum_cost = 0.0
    cum_cost_series = []
    for m in sorted_minutes:
        cum_cost += cost_buckets.get(m, 0.0)
        cum_cost_series.append(round(cum_cost, 4))

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
            "series_labels": sorted_minutes,
            "series_values": traffic_values,
        },
        "errors": {
            "error_rate_pct": round(error_rate_pct, 2),
            "total_failed": total_failed,
            "total_success": max(0, total_received - total_failed),
            "breakdown": error_breakdown,
            "threshold_rate": 2.0,
            "status": "PASS" if error_rate_pct <= 2.0 else "EXCEEDED",
        },
        "cost": {
            "total_usd": round(total_cost, 6),
            "threshold_total": 2.50,
            "status": "PASS" if total_cost <= 2.50 else "EXCEEDED",
            "series_labels": sorted_minutes,
            "cumulative_series": cum_cost_series,
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
            "scores_list": [round(q, 2) for q in quality_scores],
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
    <title>Day 13 AI Observability Enterprise Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-primary: #f8fafc;
            --bg-card: #ffffff;
            --border-color: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #64748b;
            --brand-primary: #2563eb;
            --accent-emerald: #059669;
            --accent-rose: #dc2626;
            --accent-amber: #d97706;
            --accent-purple: #7c3aed;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.07);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }

        .navbar {
            background: #ffffff;
            border-bottom: 1px solid var(--border-color);
            padding: 16px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: var(--shadow-sm);
        }

        .navbar-brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .navbar-brand h1 {
            font-size: 20px;
            font-weight: 800;
            color: var(--text-primary);
            letter-spacing: -0.5px;
        }

        .navbar-brand .tag {
            background: #eff6ff;
            color: #1d4ed8;
            font-size: 12px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
            border: 1px solid #bfdbfe;
        }

        .live-badge {
            background: #ecfdf5;
            color: #047857;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            border: 1px solid #a7f3d0;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: #10b981;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        .main-container {
            max-width: 1280px;
            margin: 0 auto;
            padding: 32px 24px;
        }

        .page-header {
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }

        .page-title {
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 4px;
        }

        .page-subtitle {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
            gap: 24px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            box-shadow: var(--shadow-md);
            transition: box-shadow 0.2s, border-color 0.2s;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .card:hover {
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
            border-color: #cbd5e1;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .card-title {
            font-size: 13px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }

        .badge-pass {
            background: #ecfdf5;
            color: #047857;
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            border: 1px solid #a7f3d0;
        }

        .badge-warn {
            background: #fef2f2;
            color: #b91c1c;
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            border: 1px solid #fecaca;
        }

        .stat-value {
            font-size: 32px;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 4px;
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
            margin-bottom: 12px;
        }

        .chart-box {
            position: relative;
            height: 180px;
            width: 100%;
            margin-top: 10px;
        }

        .metric-subgrid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            background: #f8fafc;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #f1f5f9;
            margin-top: 12px;
        }

        .submetric {
            text-align: center;
        }

        .submetric-title {
            font-size: 10px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
        }

        .submetric-val {
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
            margin-top: 2px;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="navbar-brand">
            <h1>AI Observability Dashboard</h1>
            <span class="tag">Day 13 Lab</span>
        </div>
        <div class="live-badge">
            <div class="pulse-dot"></div>
            LIVE METRICS REFRESH (15s)
        </div>
    </div>

    <div class="main-container">
        <div class="page-header">
            <div>
                <div class="page-title">Hệ thống Biểu đồ Giám sát Realtime</div>
                <div class="page-subtitle">Nguồn dữ liệu chuẩn: data/logs.jsonl | Contract 6/6 Panels Visualized</div>
            </div>
            <div style="font-size: 13px; color: var(--text-secondary); background: #ffffff; padding: 8px 16px; border-radius: 8px; border: 1px solid var(--border-color);">
                Trạng thái Contract: <strong style="color: var(--accent-emerald);">6/6 Visual Panels Active</strong>
            </div>
        </div>

        <div class="grid">
            <!-- 1. Latency -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <span class="card-title">1. Latency Percentiles</span>
                        <span id="latency-badge" class="badge-pass">PASS</span>
                    </div>
                    <div class="stat-value">
                        <span id="p95-val">0</span>
                        <span class="stat-unit">ms (P95)</span>
                    </div>
                    <div class="threshold-text">&bull; Ngưỡng SLO: P95 &le; 3000 ms</div>
                </div>
                <div class="chart-box">
                    <canvas id="latencyChart"></canvas>
                </div>
            </div>

            <!-- 2. Traffic -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <span class="card-title">2. Request Traffic Over Time</span>
                        <span id="traffic-badge" class="badge-pass">PASS</span>
                    </div>
                    <div class="stat-value">
                        <span id="traffic-reqs">0</span>
                        <span class="stat-unit">total requests</span>
                    </div>
                    <div class="threshold-text">&bull; Ngưỡng: Rate &ge; 1 req/phút</div>
                </div>
                <div class="chart-box">
                    <canvas id="trafficChart"></canvas>
                </div>
            </div>

            <!-- 3. Errors -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <span class="card-title">3. Error Rate & Breakdown</span>
                        <span id="errors-badge" class="badge-pass">PASS</span>
                    </div>
                    <div class="stat-value">
                        <span id="error-rate">0.0%</span>
                        <span class="stat-unit">error rate</span>
                    </div>
                    <div class="threshold-text">&bull; Ngưỡng SLO: Error rate &le; 2%</div>
                </div>
                <div class="chart-box">
                    <canvas id="errorChart"></canvas>
                </div>
            </div>

            <!-- 4. Cost -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <span class="card-title">4. Cumulative Cost Over Time</span>
                        <span id="cost-badge" class="badge-pass">PASS</span>
                    </div>
                    <div class="stat-value">
                        <span id="cost-total">$0.0000</span>
                        <span class="stat-unit">USD</span>
                    </div>
                    <div class="threshold-text">&bull; Ngưỡng: Total &le; $2.50 USD</div>
                </div>
                <div class="chart-box">
                    <canvas id="costChart"></canvas>
                </div>
            </div>

            <!-- 5. Tokens -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <span class="card-title">5. Tokens Consumption Breakdown</span>
                        <span id="tokens-badge" class="badge-pass">PASS</span>
                    </div>
                    <div class="stat-value">
                        <span id="tokens-total">0</span>
                        <span class="stat-unit">tokens</span>
                    </div>
                    <div class="threshold-text">&bull; Ngưỡng: Total &le; 50,000 tokens</div>
                </div>
                <div class="chart-box">
                    <canvas id="tokensChart"></canvas>
                </div>
            </div>

            <!-- 6. Quality -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <span class="card-title">6. Quality Proxy Distribution</span>
                        <span id="quality-badge" class="badge-pass">PASS</span>
                    </div>
                    <div class="stat-value">
                        <span id="quality-mean">0.00</span>
                        <span class="stat-unit">/ 1.0 score</span>
                    </div>
                    <div class="threshold-text">&bull; Ngưỡng SLO: Mean &ge; 0.75</div>
                </div>
                <div class="chart-box">
                    <canvas id="qualityChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <script>
        let charts = {};

        function initCharts() {
            // Chart 1: Latency Bar Chart
            const ctx1 = document.getElementById('latencyChart').getContext('2d');
            charts.latency = new Chart(ctx1, {
                type: 'bar',
                data: {
                    labels: ['P50 Latency', 'P95 Latency', 'P99 Latency'],
                    datasets: [{
                        label: 'Thời gian (ms)',
                        data: [0, 0, 0],
                        backgroundColor: ['#3b82f6', '#2563eb', '#1d4ed8'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#f1f5f9' },
                            title: { display: true, text: 'ms', font: { size: 10 } }
                        }
                    }
                }
            });

            // Chart 2: Traffic Line Chart
            const ctx2 = document.getElementById('trafficChart').getContext('2d');
            charts.traffic = new Chart(ctx2, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Requests / min',
                        data: [],
                        borderColor: '#059669',
                        backgroundColor: 'rgba(5, 150, 105, 0.1)',
                        fill: true,
                        tension: 0.3,
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, grid: { color: '#f1f5f9' } } }
                }
            });

            // Chart 3: Error Doughnut Chart
            const ctx3 = document.getElementById('errorChart').getContext('2d');
            charts.error = new Chart(ctx3, {
                type: 'doughnut',
                data: {
                    labels: ['Success', 'Failed'],
                    datasets: [{
                        data: [100, 0],
                        backgroundColor: ['#10b981', '#ef4444'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { font: { size: 11 } } } }
                }
            });

            // Chart 4: Cost Cumulative Line Chart
            const ctx4 = document.getElementById('costChart').getContext('2d');
            charts.cost = new Chart(ctx4, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Cost cumulative ($)',
                        data: [],
                        borderColor: '#7c3aed',
                        backgroundColor: 'rgba(124, 58, 237, 0.1)',
                        fill: true,
                        tension: 0.3,
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, grid: { color: '#f1f5f9' } } }
                }
            });

            // Chart 5: Tokens Stacked Bar
            const ctx5 = document.getElementById('tokensChart').getContext('2d');
            charts.tokens = new Chart(ctx5, {
                type: 'bar',
                data: {
                    labels: ['Tokens Breakdown'],
                    datasets: [
                        { label: 'Tokens In (Prompt)', data: [0], backgroundColor: '#3b82f6' },
                        { label: 'Tokens Out (Output)', data: [0], backgroundColor: '#8b5cf6' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { font: { size: 10 } } } },
                    scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, grid: { color: '#f1f5f9' } } }
                }
            });

            // Chart 6: Quality Score Bar Chart
            const ctx6 = document.getElementById('qualityChart').getContext('2d');
            charts.quality = new Chart(ctx6, {
                type: 'bar',
                data: {
                    labels: ['Average Quality', 'SLO Target'],
                    datasets: [{
                        label: 'Score',
                        data: [0, 0.75],
                        backgroundColor: ['#059669', '#cbd5e1'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { min: 0, max: 1.0, grid: { color: '#f1f5f9' } } }
                }
            });
        }

        async function updateDashboard() {
            try {
                const res = await fetch('/api/dashboard/stats');
                const data = await res.json();

                // Latency
                document.getElementById('p95-val').innerText = data.latency.p95;
                setBadge('latency-badge', data.latency.status);
                charts.latency.data.datasets[0].data = [data.latency.p50, data.latency.p95, data.latency.p99];
                charts.latency.update();

                // Traffic
                document.getElementById('traffic-reqs').innerText = data.traffic.total_requests;
                setBadge('traffic-badge', data.traffic.status);
                charts.traffic.data.labels = data.traffic.series_labels || [];
                charts.traffic.data.datasets[0].data = data.traffic.series_values || [];
                charts.traffic.update();

                // Errors
                document.getElementById('error-rate').innerText = data.errors.error_rate_pct + '%';
                setBadge('errors-badge', data.errors.status);
                charts.error.data.datasets[0].data = [data.errors.total_success || 1, data.errors.total_failed || 0];
                charts.error.update();

                // Cost
                document.getElementById('cost-total').innerText = '$' + data.cost.total_usd.toFixed(4);
                setBadge('cost-badge', data.cost.status);
                charts.cost.data.labels = data.cost.series_labels || [];
                charts.cost.data.datasets[0].data = data.cost.cumulative_series || [];
                charts.cost.update();

                // Tokens
                document.getElementById('tokens-total').innerText = data.tokens.total_tokens.toLocaleString();
                setBadge('tokens-badge', data.tokens.status);
                charts.tokens.data.datasets[0].data = [data.tokens.tokens_in];
                charts.tokens.data.datasets[1].data = [data.tokens.tokens_out];
                charts.tokens.update();

                // Quality
                document.getElementById('quality-mean').innerText = data.quality.mean_score.toFixed(2);
                setBadge('quality-badge', data.quality.status);
                charts.quality.data.datasets[0].data = [data.quality.mean_score, 0.75];
                charts.quality.update();

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

        window.onload = function() {
            initCharts();
            updateDashboard();
            setInterval(updateDashboard, 15000);
        };
    </script>
</body>
</html>
"""
