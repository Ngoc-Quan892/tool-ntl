#!/usr/bin/env python3
"""
Load test results analyzer and report generator.

Parses Locust CSV output files, calculates performance statistics,
identifies bottlenecks, and generates comprehensive reports.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

# Performance targets
PERFORMANCE_TARGETS = {
    "get_game_results": {"p95_ms": 50, "error_rate": 0.01},
    "get_pattern_statistics": {"p95_ms": 200, "error_rate": 0.02},
    "create_game_result": {"p95_ms": 100, "error_rate": 0.01},
    "system": {"req_per_sec": 1000, "error_rate": 0.05},
}


class LoadTestAnalyzer:
    """Analyze load test results from Locust output."""
    
    def __init__(
        self,
        results_dir: str,
        baseline_file: Optional[str] = None,
    ):
        """
        Initialize analyzer.
        
        Args:
            results_dir: Directory containing Locust CSV output files
            baseline_file: Optional path to baseline JSON for comparison
        """
        self.results_dir = Path(results_dir)
        self.baseline_file = Path(baseline_file) if baseline_file else None
        self.baseline_data: Optional[Dict[str, Any]] = None
        
        self.stats_df: Optional[pd.DataFrame] = None
        self.failures_df: Optional[pd.DataFrame] = None
        self.exceptions_df: Optional[pd.DataFrame] = None
        
        self.statistics: Optional[Dict[str, Any]] = None
        self.bottlenecks: List[str] = []
        self.recommendations: List[str] = []
        self.chart_files: Dict[str, str] = {}
        
        # Load baseline if provided
        if self.baseline_file and self.baseline_file.exists():
            with open(self.baseline_file, 'r') as f:
                self.baseline_data = json.load(f)
    
    def load_data(self) -> Dict[str, pd.DataFrame]:
        """
        Load and parse Locust output files.
        
        Returns:
            Dictionary with stats, failures, and exceptions DataFrames
        """
        if not self.results_dir.exists():
            raise FileNotFoundError(f"Results directory not found: {self.results_dir}")
        
        data = {}
        
        # Load stats.csv
        stats_file = self.results_dir / "stats.csv"
        if stats_file.exists():
            self.stats_df = pd.read_csv(stats_file)
            data["stats"] = self.stats_df
        else:
            raise FileNotFoundError(f"stats.csv not found in {self.results_dir}")
        
        # Load failures.csv if exists
        failures_file = self.results_dir / "failures.csv"
        if failures_file.exists():
            self.failures_df = pd.read_csv(failures_file)
            data["failures"] = self.failures_df
        else:
            self.failures_df = pd.DataFrame()
            data["failures"] = self.failures_df
        
        # Load exceptions.csv if exists
        exceptions_file = self.results_dir / "exceptions.csv"
        if exceptions_file.exists():
            self.exceptions_df = pd.read_csv(exceptions_file)
            data["exceptions"] = self.exceptions_df
        else:
            self.exceptions_df = pd.DataFrame()
            data["exceptions"] = self.exceptions_df
        
        return data
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Returns:
            Dictionary with summary, response_times, and by_endpoint statistics
        """
        if self.stats_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Filter out Total row if present
        stats = self.stats_df[self.stats_df["Type"] != "Total"].copy()
        
        # Calculate summary statistics
        total_requests = stats["Request Count"].sum()
        total_failures = stats["Failure Count"].sum()
        successful_requests = total_requests - total_failures
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        # Calculate average RPS (weighted by request count)
        if total_requests > 0:
            avg_rps = (stats["Requests/s"] * stats["Request Count"]).sum() / total_requests
        else:
            avg_rps = 0
        
        # Estimate test duration (if not directly available)
        # Duration = total requests / average RPS
        test_duration_seconds = total_requests / avg_rps if avg_rps > 0 else 0
        
        # Calculate response time statistics (weighted by request count)
        total_weight = stats["Request Count"].sum()
        if total_weight > 0:
            avg_response_time = (stats["Average Response Time"] * stats["Request Count"]).sum() / total_weight
            p50 = (stats["Median Response Time"] * stats["Request Count"]).sum() / total_weight
            p95 = (stats["95%"] * stats["Request Count"]).sum() / total_weight
            p99 = (stats["99%"] * stats["Request Count"]).sum() / total_weight
        else:
            avg_response_time = p50 = p95 = p99 = 0
        
        min_response_time = stats["Min Response Time"].min() if len(stats) > 0 else 0
        max_response_time = stats["Max Response Time"].max() if len(stats) > 0 else 0
        
        # Calculate p99.9 (approximate from max)
        p99_9 = max_response_time * 0.9  # Approximation
        
        # Calculate per-endpoint statistics
        by_endpoint = []
        for _, row in stats.iterrows():
            endpoint_name = row["Name"]
            requests = int(row["Request Count"])
            failures = int(row["Failure Count"])
            failure_rate = failures / requests if requests > 0 else 0
            
            by_endpoint.append({
                "name": endpoint_name,
                "requests": requests,
                "failures": failures,
                "failure_rate": failure_rate,
                "avg_response_time": row["Average Response Time"],
                "median_response_time": row["Median Response Time"],
                "p95_response_time": row["95%"],
                "p99_response_time": row["99%"],
                "min_response_time": row["Min Response Time"],
                "max_response_time": row["Max Response Time"],
                "rps": row["Requests/s"],
            })
        
        # Sort by slowest average response time
        by_endpoint.sort(key=lambda x: x["avg_response_time"], reverse=True)
        
        self.statistics = {
            "summary": {
                "total_requests": int(total_requests),
                "successful_requests": int(successful_requests),
                "failed_requests": int(total_failures),
                "success_rate": success_rate,
                "avg_rps": round(avg_rps, 2),
                "test_duration_seconds": round(test_duration_seconds, 2),
            },
            "response_times": {
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "p99_9": round(p99_9, 2),
                "avg": round(avg_response_time, 2),
                "min": round(min_response_time, 2),
                "max": round(max_response_time, 2),
            },
            "by_endpoint": by_endpoint,
        }
        
        return self.statistics
    
    def identify_bottlenecks(self) -> List[str]:
        """
        Automatically identify performance issues.
        
        Returns:
            List of identified bottleneck descriptions
        """
        if self.statistics is None:
            raise ValueError("Statistics not calculated. Call calculate_statistics() first.")
        
        bottlenecks = []
        stats = self.statistics
        
        # Check overall response times against targets
        p95 = stats["response_times"]["p95"]
        if p95 > 200:  # General target
            bottlenecks.append(
                f"❌ Overall p95 response time ({p95:.1f}ms) exceeds general target (200ms)"
            )
        
        # Check error rates
        failure_rate = 1 - stats["summary"]["success_rate"]
        if failure_rate > 0.05:  # 5% error rate threshold
            bottlenecks.append(
                f"❌ Error rate ({failure_rate*100:.2f}%) exceeds target (5%)"
            )
        elif failure_rate > 0.01:  # 1% warning threshold
            bottlenecks.append(
                f"⚠️  Error rate ({failure_rate*100:.2f}%) above recommended (1%)"
            )
        
        # Check throughput
        avg_rps = stats["summary"]["avg_rps"]
        if avg_rps < 100:  # Low throughput
            bottlenecks.append(
                f"⚠️  Throughput ({avg_rps:.1f} req/s) below expected (100 req/s)"
            )
        
        # Check endpoint-specific issues
        for endpoint in stats["by_endpoint"]:
            name = endpoint["name"]
            failure_rate = endpoint["failure_rate"]
            avg_time = endpoint["avg_response_time"]
            p95_time = endpoint["p95_response_time"]
            
            # High failure rate
            if failure_rate > 0.1:  # 10% failure rate
                bottlenecks.append(
                    f"❌ {name} has high failure rate ({failure_rate*100:.1f}%)"
                )
            elif failure_rate > 0.01:  # 1% warning
                bottlenecks.append(
                    f"⚠️  {name} failure rate ({failure_rate*100:.1f}%) above recommended"
                )
            
            # Slow response times
            # Check against endpoint-specific targets
            target_p95 = 200  # Default
            if "game" in name.lower() and "results" in name.lower():
                target_p95 = 50
            elif "statistics" in name.lower() or "pattern" in name.lower():
                target_p95 = 200
            elif "create" in name.lower() or "post" in name.lower():
                target_p95 = 100
            
            if p95_time > target_p95:
                bottlenecks.append(
                    f"❌ {name} p95 ({p95_time:.1f}ms) exceeds target ({target_p95}ms)"
                )
            
            # Response time >2x average
            overall_avg = stats["response_times"]["avg"]
            if avg_time > overall_avg * 2:
                bottlenecks.append(
                    f"⚠️  {name} average response time ({avg_time:.1f}ms) is >2x overall average ({overall_avg:.1f}ms)"
                )
        
        self.bottlenecks = bottlenecks
        return bottlenecks
    
    def generate_recommendations(self) -> List[str]:
        """
        Provide actionable optimization suggestions.
        
        Returns:
            List of prioritized recommendations
        """
        if self.statistics is None:
            raise ValueError("Statistics not calculated. Call calculate_statistics() first.")
        
        recommendations = []
        stats = self.statistics
        
        # Analyze bottlenecks to generate recommendations
        slow_endpoints = [
            ep for ep in stats["by_endpoint"]
            if ep["p95_response_time"] > 200
        ]
        
        high_error_endpoints = [
            ep for ep in stats["by_endpoint"]
            if ep["failure_rate"] > 0.01
        ]
        
        # Recommendations for slow queries
        if slow_endpoints:
            recommendations.append(
                "🔧 Add database indexes on frequently queried columns"
            )
            recommendations.append(
                "🔧 Consider query result caching for expensive operations"
            )
            recommendations.append(
                "🔧 Review and optimize slow SQL queries using EXPLAIN ANALYZE"
            )
        
        # Recommendations for high error rate
        if high_error_endpoints:
            recommendations.append(
                "🔧 Investigate error logs for root cause of failures"
            )
            recommendations.append(
                "🔧 Add circuit breaker to prevent cascading failures"
            )
            recommendations.append(
                "🔧 Implement retry logic with exponential backoff"
            )
        
        # Memory/performance recommendations
        if stats["response_times"]["p95"] > 200:
            recommendations.append(
                "🔧 Check for memory leaks using profiler (memory_profiler, py-spy)"
            )
            recommendations.append(
                "🔧 Increase cache eviction frequency if memory constrained"
            )
        
        # Throughput recommendations
        if stats["summary"]["avg_rps"] < 100:
            recommendations.append(
                "🔧 Optimize hot code paths identified in profiler"
            )
            recommendations.append(
                "🔧 Consider horizontal scaling (add more instances)"
            )
            recommendations.append(
                "🔧 Review connection pool settings (database, Redis)"
            )
        
        # Cache recommendations
        cache_effectiveness = stats["summary"]["success_rate"]
        if cache_effectiveness < 0.95:
            recommendations.append(
                "🔧 Increase cache TTL for frequently accessed data"
            )
            recommendations.append(
                "🔧 Implement cache warming on startup"
            )
            recommendations.append(
                "🔧 Review cache key strategy for better hit rates"
            )
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ Performance targets met. Continue monitoring.")
        
        self.recommendations = recommendations
        return recommendations
    
    def create_visualizations(self) -> None:
        """Generate charts for visual analysis."""
        if self.statistics is None:
            raise ValueError("Statistics not calculated. Call calculate_statistics() first.")
        
        stats = self.statistics
        
        # 1. Slowest endpoints (bar chart)
        fig, ax = plt.subplots(figsize=(12, 6))
        top_slowest = sorted(
            stats["by_endpoint"],
            key=lambda x: x["p95_response_time"],
            reverse=True
        )[:10]
        
        names = [ep["name"][:40] for ep in top_slowest]  # Truncate long names
        p95_times = [ep["p95_response_time"] for ep in top_slowest]
        
        ax.barh(names, p95_times)
        ax.set_xlabel("p95 Response Time (ms)")
        ax.set_title("Top 10 Slowest Endpoints (p95)")
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        
        chart_path = self.results_dir / "slowest_endpoints.png"
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        self.chart_files["slowest_endpoints"] = str(chart_path)
        
        # 2. Highest error rate endpoints
        fig, ax = plt.subplots(figsize=(12, 6))
        top_errors = sorted(
            stats["by_endpoint"],
            key=lambda x: x["failure_rate"],
            reverse=True
        )[:10]
        
        error_names = [ep["name"][:40] for ep in top_errors]
        error_rates = [ep["failure_rate"] * 100 for ep in top_errors]
        
        ax.barh(error_names, error_rates, color='red', alpha=0.7)
        ax.set_xlabel("Error Rate (%)")
        ax.set_title("Top 10 Highest Error Rate Endpoints")
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        
        chart_path = self.results_dir / "error_rates.png"
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        self.chart_files["error_rates"] = str(chart_path)
        
        # 3. Response time distribution (if we have detailed data)
        # This would require request-level data, so we'll create a summary chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        response_times = stats["response_times"]
        metrics = ["p50", "p95", "p99", "avg"]
        values = [
            response_times["p50"],
            response_times["p95"],
            response_times["p99"],
            response_times["avg"],
        ]
        
        ax.bar(metrics, values, color=['green', 'orange', 'red', 'blue'], alpha=0.7)
        ax.set_ylabel("Response Time (ms)")
        ax.set_title("Response Time Percentiles")
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_path = self.results_dir / "response_time_percentiles.png"
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        self.chart_files["response_time_percentiles"] = str(chart_path)
    
    def export_html_report(self, output_path: str) -> None:
        """Create comprehensive HTML report."""
        if self.statistics is None:
            raise ValueError("Statistics not calculated. Call calculate_statistics() first.")
        
        stats = self.statistics
        
        # Generate visualizations if not done
        if not self.chart_files:
            self.create_visualizations()
        
        # Read chart images as base64
        chart_base64 = {}
        for chart_name, chart_path in self.chart_files.items():
            if Path(chart_path).exists():
                with open(chart_path, 'rb') as f:
                    chart_base64[chart_name] = base64.b64encode(f.read()).decode('utf-8')
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Load Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            margin-bottom: 30px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric-card.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .metric-card.warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .metric-card h3 {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        .big-number {{
            font-size: 32px;
            font-weight: bold;
        }}
        .charts {{
            margin: 30px 0;
        }}
        .chart-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .bottlenecks, .recommendations {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .bottlenecks {{
            background: #f8d7da;
            border-left-color: #dc3545;
        }}
        .bottlenecks h2, .recommendations h2 {{
            margin-top: 0;
        }}
        ul, ol {{
            margin-left: 20px;
        }}
        li {{
            margin: 8px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .status-success {{
            background: #28a745;
            color: white;
        }}
        .status-warning {{
            background: #ffc107;
            color: #333;
        }}
        .status-danger {{
            background: #dc3545;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Load Test Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <div class="metric-card">
                <h3>Total Requests</h3>
                <p class="big-number">{stats['summary']['total_requests']:,}</p>
            </div>
            <div class="metric-card {'success' if stats['summary']['success_rate'] > 0.99 else 'warning' if stats['summary']['success_rate'] > 0.95 else ''}">
                <h3>Success Rate</h3>
                <p class="big-number">{stats['summary']['success_rate']*100:.1f}%</p>
            </div>
            <div class="metric-card">
                <h3>Average RPS</h3>
                <p class="big-number">{stats['summary']['avg_rps']:.1f}</p>
            </div>
            <div class="metric-card">
                <h3>p95 Response Time</h3>
                <p class="big-number">{stats['response_times']['p95']:.1f}ms</p>
            </div>
        </div>
        
        <div class="charts">
            <h2>Performance Charts</h2>
"""
        
        # Add charts
        for chart_name, chart_b64 in chart_base64.items():
            html += f"""
            <div class="chart-container">
                <h3>{chart_name.replace('_', ' ').title()}</h3>
                <img src="data:image/png;base64,{chart_b64}" alt="{chart_name}">
            </div>
"""
        
        html += """
        </div>
        
        <div class="bottlenecks">
            <h2>⚠️ Identified Issues</h2>
            <ul>
"""
        
        for bottleneck in self.bottlenecks:
            html += f"                <li>{bottleneck}</li>\n"
        
        html += """
            </ul>
        </div>
        
        <div class="recommendations">
            <h2>🔧 Recommendations</h2>
            <ol>
"""
        
        for recommendation in self.recommendations:
            html += f"                <li>{recommendation}</li>\n"
        
        html += """
            </ol>
        </div>
        
        <div class="details">
            <h2>Detailed Statistics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Endpoint</th>
                        <th>Requests</th>
                        <th>Failures</th>
                        <th>Failure Rate</th>
                        <th>Avg (ms)</th>
                        <th>p95 (ms)</th>
                        <th>p99 (ms)</th>
                        <th>RPS</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for endpoint in stats["by_endpoint"]:
            failure_rate_pct = endpoint["failure_rate"] * 100
            status_class = "status-success" if failure_rate_pct < 1 else "status-warning" if failure_rate_pct < 5 else "status-danger"
            
            html += f"""
                    <tr>
                        <td>{endpoint['name']}</td>
                        <td>{endpoint['requests']:,}</td>
                        <td>{endpoint['failures']}</td>
                        <td><span class="status-badge {status_class}">{failure_rate_pct:.2f}%</span></td>
                        <td>{endpoint['avg_response_time']:.1f}</td>
                        <td>{endpoint['p95_response_time']:.1f}</td>
                        <td>{endpoint['p99_response_time']:.1f}</td>
                        <td>{endpoint['rps']:.2f}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ HTML report saved to: {output_path}")
    
    def export_json_report(self, output_path: str) -> None:
        """Export structured data for programmatic access."""
        if self.statistics is None:
            raise ValueError("Statistics not calculated. Call calculate_statistics() first.")
        
        report = {
            "metadata": {
                "test_date": datetime.now().isoformat(),
                "test_duration_seconds": self.statistics["summary"]["test_duration_seconds"],
                "results_dir": str(self.results_dir),
            },
            "statistics": self.statistics,
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
            "charts": self.chart_files,
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"✅ JSON report saved to: {output_path}")
    
    def compare_with_baseline(self) -> Dict[str, Any]:
        """
        Compare current results with previous run.
        
        Returns:
            Dictionary with comparison data
        """
        if self.baseline_data is None:
            return {"error": "No baseline data available"}
        
        if self.statistics is None:
            raise ValueError("Statistics not calculated. Call calculate_statistics() first.")
        
        baseline_stats = self.baseline_data.get("statistics", {})
        current_stats = self.statistics
        
        comparison = {}
        regressions = []
        improvements = []
        
        # Compare response time p95
        baseline_p95 = baseline_stats.get("response_times", {}).get("p95", 0)
        current_p95 = current_stats["response_times"]["p95"]
        p95_change = ((current_p95 - baseline_p95) / baseline_p95 * 100) if baseline_p95 > 0 else 0
        
        comparison["response_time_p95"] = {
            "baseline": baseline_p95,
            "current": current_p95,
            "change_percent": round(p95_change, 2),
            "status": "improved" if p95_change < -5 else "degraded" if p95_change > 10 else "stable",
        }
        
        if p95_change > 15:
            regressions.append(f"p95 response time increased {p95_change:.1f}%")
        elif p95_change < -5:
            improvements.append(f"p95 response time improved {abs(p95_change):.1f}%")
        
        # Compare throughput
        baseline_rps = baseline_stats.get("summary", {}).get("avg_rps", 0)
        current_rps = current_stats["summary"]["avg_rps"]
        rps_change = ((current_rps - baseline_rps) / baseline_rps * 100) if baseline_rps > 0 else 0
        
        comparison["throughput"] = {
            "baseline": baseline_rps,
            "current": current_rps,
            "change_percent": round(rps_change, 2),
            "status": "improved" if rps_change > 5 else "degraded" if rps_change < -10 else "stable",
        }
        
        if rps_change < -10:
            regressions.append(f"Throughput decreased {abs(rps_change):.1f}%")
        elif rps_change > 5:
            improvements.append(f"Throughput improved {rps_change:.1f}%")
        
        # Compare error rate
        baseline_success = baseline_stats.get("summary", {}).get("success_rate", 1.0)
        current_success = current_stats["summary"]["success_rate"]
        baseline_error = 1 - baseline_success
        current_error = 1 - current_success
        error_change = current_error - baseline_error
        
        comparison["error_rate"] = {
            "baseline": baseline_error,
            "current": current_error,
            "change_percent": round(error_change * 100, 2),
            "status": "improved" if error_change < -0.005 else "degraded" if error_change > 0.005 else "stable",
        }
        
        if error_change > 0.005:  # 0.5% increase
            regressions.append(f"Error rate increased {error_change*100:.2f}%")
        elif error_change < -0.005:
            improvements.append(f"Error rate improved {abs(error_change)*100:.2f}%")
        
        comparison["regressions"] = regressions
        comparison["improvements"] = improvements
        
        return comparison
    
    def detect_regressions(self) -> bool:
        """
        Detect if performance has regressed compared to baseline.
        
        Returns:
            True if regressions detected, False otherwise
        """
        if self.baseline_data is None:
            return False
        
        comparison = self.compare_with_baseline()
        
        # Check for regressions
        if comparison.get("regressions"):
            return True
        
        # Check thresholds
        p95_change = comparison.get("response_time_p95", {}).get("change_percent", 0)
        if p95_change > 15:  # 15% increase
            return True
        
        rps_change = comparison.get("throughput", {}).get("change_percent", 0)
        if rps_change < -10:  # 10% decrease
            return True
        
        error_change = comparison.get("error_rate", {}).get("change_percent", 0)
        if error_change > 0.5:  # 0.5% increase
            return True
        
        return False


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Locust load test results and generate reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  python analyze_results.py --results-dir=./results/run_20240101
  
  # With baseline comparison
  python analyze_results.py --results-dir=./results/run_20240101 --baseline=./results/run_20231201/baseline.json
  
  # Custom output
  python analyze_results.py --results-dir=./results/run_20240101 --output=report.html --format=html
        """
    )
    
    parser.add_argument(
        "--results-dir",
        type=str,
        required=True,
        help="Path to Locust output directory (must contain stats.csv)"
    )
    parser.add_argument(
        "--baseline",
        type=str,
        help="Path to baseline JSON file for comparison"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="report.html",
        help="Output report path (default: report.html)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["html", "json", "both"],
        default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--charts",
        action="store_true",
        default=True,
        help="Generate charts (default: True)"
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Skip chart generation"
    )
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = LoadTestAnalyzer(
        results_dir=args.results_dir,
        baseline_file=args.baseline,
    )
    
    try:
        # Load data
        print("📊 Loading test results...")
        analyzer.load_data()
        
        # Calculate statistics
        print("📈 Calculating statistics...")
        analyzer.calculate_statistics()
        
        # Identify bottlenecks
        print("🔍 Identifying bottlenecks...")
        analyzer.identify_bottlenecks()
        
        # Generate recommendations
        print("💡 Generating recommendations...")
        analyzer.generate_recommendations()
        
        # Create visualizations
        if args.charts and not args.no_charts:
            print("📊 Creating visualizations...")
            analyzer.create_visualizations()
        
        # Compare with baseline
        if args.baseline:
            print("📊 Comparing with baseline...")
            comparison = analyzer.compare_with_baseline()
            if comparison.get("regressions"):
                print("⚠️  Regressions detected:")
                for reg in comparison["regressions"]:
                    print(f"   - {reg}")
            if comparison.get("improvements"):
                print("✅ Improvements:")
                for imp in comparison["improvements"]:
                    print(f"   - {imp}")
        
        # Export reports
        if args.format in ["html", "both"]:
            analyzer.export_html_report(args.output)
        
        if args.format in ["json", "both"]:
            json_output = Path(args.output).with_suffix('.json')
            analyzer.export_json_report(str(json_output))
        
        # Print summary
        stats = analyzer.statistics
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"Total Requests: {stats['summary']['total_requests']:,}")
        print(f"Success Rate: {stats['summary']['success_rate']*100:.1f}%")
        print(f"Average RPS: {stats['summary']['avg_rps']:.1f}")
        print(f"p95 Response Time: {stats['response_times']['p95']:.1f}ms")
        print(f"Bottlenecks Found: {len(analyzer.bottlenecks)}")
        print("=" * 60)
        
        # Check for regressions (for CI)
        if args.baseline and analyzer.detect_regressions():
            print("\n❌ Performance regressions detected!")
            sys.exit(1)
        
        print("\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

