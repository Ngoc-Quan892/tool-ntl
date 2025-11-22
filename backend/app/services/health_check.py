"""
Comprehensive health check system
"""

from typing import Dict, List, Optional
import asyncio
import aiohttp
import psutil
import redis
import time
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.config import get_settings

settings = get_settings()


class HealthChecker:
    """
    System health monitoring
    """
    
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.settings = settings
        self.db = db
        self.redis_client = redis_client
        self.checks = {
            "database": self.check_database,
            "redis": self.check_redis,
            "disk": self.check_disk_space,
            "memory": self.check_memory,
            "cpu": self.check_cpu,
            "api": self.check_api_endpoints,
            "ml_model": self.check_ml_model,
            "external_services": self.check_external_services
        }
    
    async def check_health(self) -> Dict:
        """Run all health checks"""
        
        results = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "details": {}
        }
        
        # Run all checks
        for name, check_func in self.checks.items():
            try:
                check_result = await check_func()
                results["checks"][name] = check_result
                
                if check_result["status"] != "healthy":
                    results["status"] = "degraded"
                    
            except Exception as e:
                results["checks"][name] = {
                    "status": "error",
                    "message": str(e)
                }
                results["status"] = "unhealthy"
        
        # Calculate overall score
        healthy_checks = sum(
            1 for check in results["checks"].values()
            if check.get("status") == "healthy"
        )
        total_checks = len(results["checks"])
        results["health_score"] = (healthy_checks / total_checks) * 100 if total_checks > 0 else 0
        
        return results
    
    async def check_database(self) -> Dict:
        """Check database connectivity and performance"""
        
        try:
            # Test connection
            start_time = time.time()
            result = self.db.execute(text("SELECT 1"))
            result.fetchone()  # Actually fetch the result
            response_time = (time.time() - start_time) * 1000
            
            # Check response time
            if response_time > 100:  # >100ms is slow
                return {
                    "status": "degraded",
                    "response_time_ms": round(response_time, 2),
                    "message": "Database response slow"
                }
            
            # Check connection pool
            pool = self.db.bind.pool
            pool_status = {
                "size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "checked_in": pool.checkedin()
            }
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "pool": pool_status
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_redis(self) -> Dict:
        """Check Redis connectivity"""
        
        try:
            # Ping Redis
            start_time = time.time()
            self.redis_client.ping()
            response_time = (time.time() - start_time) * 1000
            
            # Get Redis info
            info = self.redis_client.info()
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "uptime_days": info.get("uptime_in_days")
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_disk_space(self) -> Dict:
        """Check available disk space"""
        
        try:
            # On Windows, use 'C:\\' instead of '/'
            import platform
            if platform.system() == 'Windows':
                disk_usage = psutil.disk_usage('C:\\')
            else:
                disk_usage = psutil.disk_usage('/')
            
            if disk_usage.percent > 90:
                status = "critical"
            elif disk_usage.percent > 80:
                status = "warning"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "used_percent": round(disk_usage.percent, 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "total_gb": round(disk_usage.total / (1024**3), 2)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def check_memory(self) -> Dict:
        """Check memory usage"""
        
        try:
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                status = "critical"
            elif memory.percent > 80:
                status = "warning"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "used_percent": round(memory.percent, 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def check_cpu(self) -> Dict:
        """Check CPU usage"""
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > 90:
                status = "critical"
            elif cpu_percent > 80:
                status = "warning"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "usage_percent": round(cpu_percent, 2),
                "core_count": psutil.cpu_count()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def check_api_endpoints(self) -> Dict:
        """Check critical API endpoints"""
        
        endpoints = [
            "/api/v2/health",
            "/api/v2/shoes",
            "/api/v2/predictions"
        ]
        
        results = {
            "status": "healthy",
            "endpoints": {}
        }
        
        base_url = f"http://{self.settings.HOST}:{self.settings.PORT}"
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    url = f"{base_url}{endpoint}"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        results["endpoints"][endpoint] = {
                            "status_code": response.status,
                            "healthy": response.status == 200
                        }
                        
                        if response.status != 200:
                            results["status"] = "degraded"
                            
                except Exception as e:
                    results["endpoints"][endpoint] = {
                        "error": str(e),
                        "healthy": False
                    }
                    results["status"] = "unhealthy"
        
        return results
    
    async def check_ml_model(self) -> Dict:
        """Check ML model availability"""
        
        try:
            # Check if model files exist
            model_path = Path(self.settings.ML_MODEL_PATH)
            
            if not model_path.exists():
                return {
                    "status": "unhealthy",
                    "error": "Model directory not found"
                }
            
            # Check if model files exist
            model_files = list(model_path.glob("*.pkl")) + list(model_path.glob("*.h5")) + list(model_path.glob("*.pb"))
            
            if not model_files:
                return {
                    "status": "warning",
                    "message": "Model directory exists but no model files found",
                    "model_path": str(model_path)
                }
            
            return {
                "status": "healthy",
                "model_path": str(model_path),
                "models_available": len(model_files),
                "model_files": [str(f.name) for f in model_files[:5]]  # Show first 5
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def check_external_services(self) -> Dict:
        """Check external service dependencies"""
        
        services = {
            # Add external services here if needed
            # "sentry": "https://sentry.io/api/0/heartbeat/",
        }
        
        if not services:
            # No external services configured
            return {
                "status": "healthy",
                "message": "No external services configured",
                "services": {}
            }
        
        results = {
            "status": "healthy",
            "services": {}
        }
        
        async with aiohttp.ClientSession() as session:
            for name, url in services.items():
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        results["services"][name] = {
                            "status": "up" if response.status < 500 else "down",
                            "response_code": response.status
                        }
                        
                        if response.status >= 500:
                            results["status"] = "degraded"
                            
                except Exception:
                    results["services"][name] = {
                        "status": "unreachable"
                    }
                    # Don't mark as unhealthy for external services
        
        return results

