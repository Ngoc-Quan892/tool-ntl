"""
Alerting system for monitoring performance metrics and triggering notifications.

This module provides:
- Configurable alert thresholds
- Background monitoring task
- Multiple notification channels (Slack, Email, Logging)
- Alert history tracking
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import time
from dataclasses import dataclass
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Callable, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.services.monitoring import capture_message

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class AlertThreshold:
    """Alert threshold configuration."""
    
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq", "gte", "lte"
    severity: str    # "warning", "critical"
    callback: Callable
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minutes cooldown between alerts


@dataclass
class Alert:
    """Alert record."""
    
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold: float
    severity: str
    message: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class NotificationService:
    """Service for sending notifications via multiple channels."""
    
    def __init__(self):
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.alert_email = os.getenv("ALERT_EMAIL", os.getenv("SMTP_USER"))
        
    async def send_slack(self, message: str, severity: str = "warning") -> bool:
        """
        Send alert to Slack via webhook.
        
        Args:
            message: Alert message
            severity: Alert severity (warning, critical)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.slack_webhook_url:
            return False
        
        try:
            color = "#FFA500" if severity == "warning" else "#FF0000"
            emoji = "⚠️" if severity == "warning" else "🚨"
            
            payload = {
                "text": f"{emoji} Alert: {settings.APP_NAME}",
                "attachments": [
                    {
                        "color": color,
                        "text": message,
                        "footer": f"{settings.APP_NAME} Alerting System",
                        "ts": int(time.time()),
                    }
                ],
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.slack_webhook_url, json=payload)
                response.raise_for_status()
                logger.info("Slack alert sent successfully")
                return True
        except Exception as exc:
            logger.error(f"Failed to send Slack alert: {exc}")
            return False
    
    async def send_email(self, subject: str, message: str, severity: str = "warning") -> bool:
        """
        Send alert via email.
        
        Args:
            subject: Email subject
            message: Email body
            severity: Alert severity
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.alert_email]):
            return False
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = self.alert_email
            msg["Subject"] = f"[{severity.upper()}] {subject}"
            
            body = f"""
            Alert from {settings.APP_NAME}
            
            Severity: {severity.upper()}
            Time: {datetime.utcnow().isoformat()}
            
            {message}
            
            ---
            This is an automated alert from the monitoring system.
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {self.alert_email}")
            return True
        except Exception as exc:
            logger.error(f"Failed to send email alert: {exc}")
            return False
    
    async def send_notification(self, message: str, severity: str = "warning") -> Dict[str, bool]:
        """
        Send notification via all available channels.
        
        Args:
            message: Alert message
            severity: Alert severity
            
        Returns:
            Dictionary with channel -> success status
        """
        results = {}
        
        # Send to Slack
        results["slack"] = await self.send_slack(message, severity)
        
        # Send email
        subject = f"Alert: {settings.APP_NAME}"
        results["email"] = await self.send_email(subject, message, severity)
        
        # Log to Sentry
        if severity == "critical":
            capture_message(
                message,
                level="error",
                context={"alert_type": "performance_threshold", "severity": severity}
            )
            results["sentry"] = True
        else:
            results["sentry"] = False
        
        # Always log to application logs
        log_level = logging.WARNING if severity == "warning" else logging.CRITICAL
        logger.log(log_level, f"ALERT [{severity.upper()}]: {message}")
        results["logging"] = True
        
        return results


class AlertManager:
    """
    Monitor metrics and trigger alerts based on configured thresholds.
    
    Features:
    - Check thresholds every minute (configurable)
    - Send notifications (Slack, email, logging)
    - Track alert history
    - Cooldown periods to prevent alert spam
    """
    
    def __init__(self, optimizer=None):
        """
        Initialize AlertManager.
        
        Args:
            optimizer: OptimizationStack instance for accessing metrics
        """
        self.optimizer = optimizer
        self.thresholds: List[AlertThreshold] = []
        self.alert_history: List[Alert] = []
        self.last_alert_times: Dict[str, float] = {}  # metric_name -> last_alert_time
        self.notification_service = NotificationService()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._check_interval = 60  # Check every minute
        self._enabled = True
        
        self.setup_default_thresholds()
    
    def setup_default_thresholds(self):
        """Configure critical thresholds."""
        # Cache performance
        self.add_threshold(
            metric_name="cache_hit_rate",
            threshold=0.7,  # 70%
            comparison="lt",
            severity="warning",
            callback=self.alert_low_cache_hit_rate,
            cooldown_seconds=300,  # 5 minutes
        )
        
        # Query performance
        self.add_threshold(
            metric_name="avg_query_time_ms",
            threshold=200,  # 200ms
            comparison="gt",
            severity="critical",
            callback=self.alert_slow_queries,
            cooldown_seconds=180,  # 3 minutes
        )
        
        # Connection pool
        self.add_threshold(
            metric_name="connection_pool_utilization",
            threshold=0.9,  # 90% utilization
            comparison="gt",
            severity="critical",
            callback=self.alert_connection_exhaustion,
            cooldown_seconds=300,  # 5 minutes
        )
        
        # System memory
        self.add_threshold(
            metric_name="memory_percent",
            threshold=90.0,  # 90% memory usage
            comparison="gt",
            severity="warning",
            callback=self.alert_high_memory,
            cooldown_seconds=600,  # 10 minutes
        )
    
    def add_threshold(
        self,
        metric_name: str,
        threshold: float,
        comparison: str,
        severity: str,
        callback: Callable,
        enabled: bool = True,
        cooldown_seconds: int = 300,
    ) -> None:
        """
        Add an alert threshold.
        
        Args:
            metric_name: Name of the metric to monitor
            threshold: Threshold value
            comparison: Comparison operator ("gt", "lt", "eq", "gte", "lte")
            severity: Alert severity ("warning", "critical")
            callback: Callback function to execute when threshold is breached
            enabled: Whether this threshold is enabled
            cooldown_seconds: Cooldown period between alerts (seconds)
        """
        threshold_obj = AlertThreshold(
            metric_name=metric_name,
            threshold=threshold,
            comparison=comparison,
            severity=severity,
            callback=callback,
            enabled=enabled,
            cooldown_seconds=cooldown_seconds,
        )
        self.thresholds.append(threshold_obj)
        logger.info(
            f"Added alert threshold: {metric_name} {comparison} {threshold} "
            f"(severity: {severity})"
        )
    
    def _check_threshold(self, threshold: AlertThreshold, current_value: float) -> bool:
        """
        Check if threshold is breached.
        
        Args:
            threshold: Alert threshold configuration
            current_value: Current metric value
            
        Returns:
            True if threshold is breached, False otherwise
        """
        if not threshold.enabled:
            return False
        
        comparison = threshold.comparison
        threshold_value = threshold.threshold
        
        if comparison == "gt":
            return current_value > threshold_value
        elif comparison == "lt":
            return current_value < threshold_value
        elif comparison == "eq":
            return current_value == threshold_value
        elif comparison == "gte":
            return current_value >= threshold_value
        elif comparison == "lte":
            return current_value <= threshold_value
        else:
            logger.warning(f"Unknown comparison operator: {comparison}")
            return False
    
    def _is_in_cooldown(self, metric_name: str, cooldown_seconds: int) -> bool:
        """Check if metric is in cooldown period."""
        last_alert_time = self.last_alert_times.get(metric_name, 0)
        return (time.time() - last_alert_time) < cooldown_seconds
    
    async def check_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        Check all thresholds against current metrics.
        
        Args:
            metrics: Dictionary of current metric values
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts: List[Alert] = []
        
        for threshold in self.thresholds:
            if not threshold.enabled:
                continue
            
            # Get current value for this metric
            current_value = self._extract_metric_value(metrics, threshold.metric_name)
            
            if current_value is None:
                continue
            
            # Check if threshold is breached
            if self._check_threshold(threshold, current_value):
                # Check cooldown
                if self._is_in_cooldown(threshold.metric_name, threshold.cooldown_seconds):
                    continue
                
                # Create alert
                alert = Alert(
                    timestamp=datetime.utcnow(),
                    metric_name=threshold.metric_name,
                    current_value=current_value,
                    threshold=threshold.threshold,
                    severity=threshold.severity,
                    message=f"{threshold.metric_name} = {current_value} "
                            f"({threshold.comparison} {threshold.threshold})",
                )
                
                triggered_alerts.append(alert)
                self.alert_history.append(alert)
                self.last_alert_times[threshold.metric_name] = time.time()
                
                # Execute callback
                try:
                    if asyncio.iscoroutinefunction(threshold.callback):
                        await threshold.callback(current_value, alert)
                    else:
                        threshold.callback(current_value, alert)
                except Exception as exc:
                    logger.error(f"Error executing alert callback: {exc}")
        
        return triggered_alerts
    
    def _extract_metric_value(self, metrics: Dict[str, Any], metric_name: str) -> Optional[float]:
        """
        Extract metric value from metrics dictionary.
        
        Args:
            metrics: Metrics dictionary
            metric_name: Name of metric to extract
            
        Returns:
            Metric value or None if not found
        """
        # Handle nested paths like "cache.hit_rate"
        parts = metric_name.split(".")
        value = metrics
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            
            if value is None:
                return None
        
        # Convert to float if possible
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    async def alert_low_cache_hit_rate(self, current_value: float, alert: Alert):
        """
        Investigate cache misses.
        
        Actions:
        - Check query patterns
        - Adjust TTL
        - Increase cache size
        """
        message = (
            f"⚠️ Cache hit rate is low: {current_value:.2%} (threshold: 70%)\n\n"
            f"Recommended actions:\n"
            f"- Review query patterns and cache keys\n"
            f"- Consider increasing cache TTL\n"
            f"- Check cache size limits\n"
            f"- Review cache eviction policies"
        )
        
        await self.notification_service.send_notification(message, alert.severity)
    
    async def alert_slow_queries(self, current_value: float, alert: Alert):
        """
        Optimize slow queries.
        
        Actions:
        - Run EXPLAIN
        - Add indexes
        - Refactor query
        """
        message = (
            f"🚨 Queries are too slow: {current_value:.2f}ms average "
            f"(threshold: 200ms)\n\n"
            f"Recommended actions:\n"
            f"- Run EXPLAIN ANALYZE on slow queries\n"
            f"- Add database indexes\n"
            f"- Review query patterns\n"
            f"- Consider query optimization or refactoring"
        )
        
        await self.notification_service.send_notification(message, alert.severity)
    
    async def alert_connection_exhaustion(self, current_value: float, alert: Alert):
        """
        Scale connection pool.
        
        Actions:
        - Increase pool size
        - Check for connection leaks
        - Review query efficiency
        """
        message = (
            f"🚨 Connection pool is highly utilized: {current_value:.2%} "
            f"(threshold: 90%)\n\n"
            f"Recommended actions:\n"
            f"- Increase connection pool size\n"
            f"- Check for connection leaks\n"
            f"- Review query efficiency\n"
            f"- Consider connection pooling optimization"
        )
        
        await self.notification_service.send_notification(message, alert.severity)
    
    async def alert_high_memory(self, current_value: float, alert: Alert):
        """
        Alert on high memory usage.
        
        Actions:
        - Check for memory leaks
        - Review cache size
        - Consider scaling
        """
        message = (
            f"⚠️ Memory usage is high: {current_value:.2f}% "
            f"(threshold: 90%)\n\n"
            f"Recommended actions:\n"
            f"- Check for memory leaks\n"
            f"- Review cache size and eviction policies\n"
            f"- Consider scaling resources\n"
            f"- Monitor memory trends"
        )
        
        await self.notification_service.send_notification(message, alert.severity)
    
    async def _monitoring_loop(self):
        """Background task to check metrics periodically."""
        logger.info("Alert monitoring loop started")
        
        while self._enabled:
            try:
                # Get current metrics from optimizer
                if self.optimizer:
                    # This would need to be implemented to get metrics
                    # For now, we'll get metrics from monitoring endpoint
                    metrics = await self._get_current_metrics()
                    
                    if metrics:
                        alerts = await self.check_metrics(metrics)
                        if alerts:
                            logger.info(f"Triggered {len(alerts)} alerts")
                else:
                    logger.warning("Optimizer not available, skipping metric check")
                
                # Wait for next check
                await asyncio.sleep(self._check_interval)
                
            except asyncio.CancelledError:
                logger.info("Alert monitoring loop cancelled")
                break
            except Exception as exc:
                logger.error(f"Error in alert monitoring loop: {exc}", exc_info=True)
                await asyncio.sleep(self._check_interval)
    
    async def _get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get current metrics from monitoring system.
        
        Returns:
            Dictionary of current metrics or None if unavailable
        """
        if not self.optimizer:
            return None
        
        try:
            from app.models.database import db_manager
            
            # Get metrics from optimizer components
            metrics: Dict[str, Any] = {}
            
            # Get cache statistics
            cache_manager = self.optimizer.get_cache_manager()
            cache_stats = cache_manager.get_stats()
            
            local_hits = cache_stats.get("stats", {}).get("local_hits", 0)
            local_misses = cache_stats.get("stats", {}).get("local_misses", 0)
            redis_hits = cache_stats.get("stats", {}).get("redis_hits", 0)
            redis_misses = cache_stats.get("stats", {}).get("redis_misses", 0)
            
            total_hits = local_hits + redis_hits
            total_misses = local_misses + redis_misses
            total_requests = total_hits + total_misses
            
            cache_hit_rate = (total_hits / total_requests) if total_requests > 0 else 0.0
            
            metrics["cache"] = {
                "hit_rate": cache_hit_rate,
                "size_mb": cache_stats.get("local_cache_size", 0) * 0.001,
            }
            
            # Get query statistics
            with db_manager.get_session() as session:
                query_optimizer = self.optimizer.get_query_optimizer(session)
                query_stats = query_optimizer.get_query_statistics()
                
                total_queries = 0
                total_time_ms = 0.0
                
                for query_name, stats in query_stats.items():
                    count = stats.get("count", 0)
                    avg_time = stats.get("avg_time_ms", 0)
                    total_queries += count
                    total_time_ms += avg_time * count
                
                avg_query_time_ms = (total_time_ms / total_queries) if total_queries > 0 else 0.0
                
                metrics["queries"] = {
                    "avg_time_ms": avg_query_time_ms,
                    "total_queries": total_queries,
                }
            
            # Get connection pool status
            if hasattr(db_manager, "engine") and db_manager.engine:
                from app.services.performance_optimizer import ConnectionPoolManager
                pool_status = ConnectionPoolManager.get_pool_status(db_manager.engine)
                
                checked_out = pool_status.get("checked_out", 0)
                pool_size = pool_status.get("pool_size", 1)
                utilization = (checked_out / pool_size) if pool_size > 0 else 0.0
                
                metrics["connections"] = {
                    "active": checked_out,
                    "idle": pool_status.get("checked_in", 0),
                    "pool_size": pool_size,
                    "utilization": utilization,
                }
                metrics["connection_pool_utilization"] = utilization
            
            # Get system resources
            try:
                import psutil
                process = psutil.Process()
                metrics["system"] = {
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_percent": process.memory_percent(),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                }
                metrics["memory_percent"] = process.memory_percent()
            except ImportError:
                metrics["system"] = {}
                metrics["memory_percent"] = None
            
            # Flatten metrics for easier access
            flattened = {}
            flattened.update(metrics.get("cache", {}))
            flattened.update(metrics.get("queries", {}))
            flattened.update(metrics.get("connections", {}))
            flattened.update(metrics.get("system", {}))
            
            # Add nested paths
            flattened["cache.hit_rate"] = metrics.get("cache", {}).get("hit_rate", 0)
            flattened["queries.avg_time_ms"] = metrics.get("queries", {}).get("avg_time_ms", 0)
            flattened["connections.utilization"] = metrics.get("connections", {}).get("utilization", 0)
            
            return flattened
            
        except Exception as exc:
            logger.error(f"Failed to get current metrics: {exc}", exc_info=True)
            return None
    
    def start_monitoring(self):
        """Start background monitoring task."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._enabled = True
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Alert monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring task."""
        self._enabled = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            logger.info("Alert monitoring stopped")
    
    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> List[Alert]:
        """
        Get alert history.
        
        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity (optional)
            resolved: Filter by resolved status (optional)
            
        Returns:
            List of alerts
        """
        alerts = self.alert_history
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return alerts[:limit]
    
    def resolve_alert(self, alert: Alert) -> None:
        """Mark an alert as resolved."""
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        logger.info(f"Alert resolved: {alert.metric_name} at {alert.timestamp}")


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(optimizer=None) -> AlertManager:
    """
    Get or create AlertManager instance.
    
    Args:
        optimizer: OptimizationStack instance (optional)
        
    Returns:
        AlertManager instance
    """
    global _alert_manager
    
    if _alert_manager is None:
        _alert_manager = AlertManager(optimizer=optimizer)
    
    return _alert_manager

