"""FastAPI application entry point."""
from __future__ import annotations

import asyncio
import os
import json
from contextlib import asynccontextmanager
from typing import List, Optional
import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .middleware.performance import PerformanceMiddleware
from .middleware.security import SecurityMiddleware

from .api.routes import router as api_router
from .api.websocket import router as websocket_router, manager as ws_manager
from .api.websocket_manager import ws_manager as v2_ws_manager
from .api.v2.base import router as v2_base_router
from .api.v2.shoes import router as v2_shoes_router
from .api.v2.hands import router as v2_hands_router
from .api.v2.predictions import router as v2_predictions_router
from .api.v2.analysis import router as v2_analysis_router
from .api.v2.websocket import router as v2_websocket_router
from .api.v2.metrics import router as v2_metrics_router
from .api.v2 import ml_endpoints
from .api.v2.performance_endpoints import router as v2_performance_router
from .api.v2.cache import router as v2_cache_router
from .api.v2.profiling import router as v2_profiling_router
from .api.v2.monitoring_dashboard import router as v2_monitoring_dashboard_router
from .api.endpoints import game_analysis
from .api.endpoints import monitoring
from .api.endpoints import dashboard
from .core.predictor import Predictor
from .services.cache import cache_manager
from .core.simulator import SimulationManager
from .models.database import Base, db_manager
from .utils.helpers import AppState
from .utils.logger import configure_logging
from .core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Global optimizer instance
optimizer: Optional["OptimizationStack"] = None


def get_mysql_pool():
    """
    Get MySQL/PostgreSQL connection pool.
    
    Returns:
        DatabaseManager instance (acts as connection pool)
    """
    return db_manager


def get_redis_client():
    """
    Get Redis client for caching.
    
    Returns:
        Redis client instance or None if unavailable
    """
    from app.services.performance_optimizer import new_redis_client
    return new_redis_client()


async def warm_up_cache(optimizer_instance: "OptimizationStack") -> None:
    """
    Cache warming strategy - pre-load critical data into cache.
    
    This function:
    - Loads last 100 games
    - Pre-calculates popular patterns
    - Caches user session data
    
    Args:
        optimizer_instance: OptimizationStack instance
    """
    logger.info("🔥 Warming up cache...")
    
    try:
        # Get a database session for cache warming
        with db_manager.get_session() as session:
            query_optimizer = optimizer_instance.get_query_optimizer(session)
            cache_manager = optimizer_instance.get_cache_manager()
            
            # Top 10 most accessed games (you can customize this list)
            popular_games = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            
            for game_id in popular_games:
                try:
                    # Pre-fetch game results
                    results = query_optimizer.get_game_results(game_id, limit=100)
                    if results:
                        # Cache the results
                        cache_key = cache_manager._generate_key(
                            "game_results", "get_game_results", game_id, limit=100
                        )
                        cache_manager.set(cache_key, {
                            "game_id": game_id,
                            "results": results,
                            "count": len(results),
                            "limit": 100,
                        }, ttl=60)
                        logger.debug(f"Pre-cached game results for game_id={game_id}")
                except Exception as exc:
                    logger.warning(f"Failed to warm cache for game_id={game_id}: {exc}")
            
            # Common patterns
            patterns = ["B", "P", "T", "all"]
            for pattern in patterns:
                try:
                    # Pre-calculate pattern statistics
                    stats = query_optimizer.get_pattern_statistics(
                        pattern_type=pattern,
                        days=7,
                        limit=1000,
                        use_cache=True
                    )
                    if stats:
                        # Cache the statistics
                        cache_key = cache_manager._generate_key(
                            "pattern_stats", "get_pattern_statistics", pattern, days=7
                        )
                        cache_manager.set(cache_key, {
                            "pattern_type": pattern,
                            "days": 7,
                            "statistics": stats,
                            "count": len(stats),
                        }, ttl=300)
                        logger.debug(f"Pre-cached pattern statistics for pattern={pattern}")
                except Exception as exc:
                    logger.warning(f"Failed to warm cache for pattern={pattern}: {exc}")
        
        logger.info("✅ Cache warmed successfully!")
    except Exception as exc:
        logger.error(f"Cache warming failed: {exc}")
        logger.warning("Application will continue without pre-warmed cache")


def save_metrics_to_file(metrics: dict, filepath: Optional[str] = None) -> None:
    """
    Save performance metrics to file before shutdown.
    
    Args:
        metrics: Performance metrics dictionary
        filepath: Optional file path. If None, uses default location
    """
    if filepath is None:
        # Create metrics directory if it doesn't exist
        metrics_dir = os.path.join(os.getcwd(), "metrics")
        os.makedirs(metrics_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(metrics_dir, f"performance_metrics_{timestamp}.json")
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, default=str)
        logger.info(f"Performance metrics saved to {filepath}")
    except Exception as exc:
        logger.error(f"Failed to save metrics to file: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    
    Handles:
    - Startup: Initialize all connections, warm up cache
    - Shutdown: Cleanup resources properly, save metrics
    """
    global optimizer
    
    # ========== STARTUP ==========
    logger.info("🚀 Starting application...")
    
    try:
        # Initialize WebSocket managers
        await v2_ws_manager.start()
        await cache_manager.connect()
        logger.info("WebSocket managers and cache connected")
    except Exception as exc:
        logger.warning(f"Failed to initialize WebSocket/cache: {exc}")
    
    # Initialize OptimizationStack
    try:
        from app.services.performance_optimizer import OptimizationStack
        from app.core.config import get_settings
        
        settings = get_settings()
        redis_client = get_redis_client()
        
        optimizer = OptimizationStack(
            db_connection=get_mysql_pool(),
            redis_client=redis_client,
            cache_ttl=settings.REDIS_CACHE_TTL or 300,
        )
        
        # Store optimizer in app state for access throughout the application
        app.state.optimizer = optimizer
        logger.info("✅ OptimizationStack initialized")
        
        # Pre-warm critical caches using CacheWarmer
        try:
            from app.services.cache_warmer import CacheWarmer
            
            warmer = CacheWarmer(
                optimizer=optimizer,
                strategy="moderate",  # Use moderate strategy for startup
                max_concurrent=10,
            )
            
            # Define callback to log warming completion
            async def log_warming_complete():
                try:
                    report = await warmer.warm_cache()
                    logger.info(
                        f"✅ Cache warming complete: {report['items_warmed']} items warmed "
                        f"in {report['time_taken_seconds']:.1f}s"
                    )
                    logger.info(
                        f"   Cache hit rate: {report['cache_hit_rate_before']:.1%} → "
                        f"{report['cache_hit_rate_after']:.1%} ({report.get('improvement', 'N/A')})"
                    )
                    if report.get('items_by_priority'):
                        logger.info("   Items by priority:")
                        for priority, count in report['items_by_priority'].items():
                            logger.info(f"     - {priority}: {count}")
                except Exception as exc:
                    logger.error(f"Cache warming failed: {exc}", exc_info=True)
            
            # Run warming in background to not block startup
            asyncio.create_task(log_warming_complete())
            logger.info("🔥 Cache warming started in background")
        except Exception as exc:
            logger.warning(f"Failed to start cache warming: {exc}, falling back to simple warm_up_cache")
            await warm_up_cache(optimizer)
        
    except Exception as exc:
        logger.error(f"Failed to initialize OptimizationStack: {exc}")
        logger.warning("Performance optimization features may be limited")
        optimizer = None
    
    # Initialize ML predictor
    try:
        from app.core.config import get_settings
        from app.ml.config import FeatureConfig, ModelConfig, PerformanceConfig
        from app.ml.predictor import get_predictor

        settings = get_settings()
        predictor = get_predictor(
            model_config=ModelConfig(),
            feature_config=FeatureConfig(),
            performance_config=PerformanceConfig(),
            redis_url=settings.REDIS_URL,
        )
        stats = predictor.get_performance_stats()
        logger.info(
            "ML system initialized. Models loaded: %s | Device: %s",
            stats["models_loaded"],
            stats["device"],
        )
    except Exception as exc:
        logger.error(f"Failed to initialize ML system: {exc}")
        logger.warning("ML predictions will operate in fallback mode")
    
    logger.info("✅ Application startup complete")
    
    yield
    
    # ========== SHUTDOWN ==========
    logger.info("🛑 Shutting down application...")
    
    try:
        # Stop WebSocket managers
        await v2_ws_manager.stop()
        await cache_manager.disconnect()
        logger.info("WebSocket managers and cache disconnected")
    except Exception as exc:
        logger.warning(f"Error during WebSocket/cache shutdown: {exc}")
    
    # Save metrics before shutdown
    if optimizer:
        try:
            # Clear cache if needed (optional - you may want to keep it)
            # optimizer.cache_manager.clear_all()
            
            # Get and save performance metrics
            monitor = optimizer.get_performance_monitor()
            metrics = monitor.get_metrics()
            
            # Add query statistics if available
            try:
                with db_manager.get_session() as session:
                    query_optimizer = optimizer.get_query_optimizer(session)
                    query_stats = query_optimizer.get_query_statistics()
                    metrics["query_statistics"] = query_stats
            except Exception as exc:
                logger.warning(f"Failed to get query statistics: {exc}")
            
            save_metrics_to_file(metrics)
            logger.info("Performance metrics saved")
            
        except Exception as exc:
            logger.error(f"Error saving metrics: {exc}")
        
        # Close database connection pool if needed
        try:
            if hasattr(db_manager, "engine") and db_manager.engine:
                db_manager.engine.dispose()
                logger.info("Database connection pool closed")
        except Exception as exc:
            logger.warning(f"Error closing database pool: {exc}")
    
    logger.info("✅ Application shutdown complete")


def _get_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "[\"http://localhost:5173\",\"http://localhost:3000\"]")
    try:
        import json

        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    configure_logging()
    
    # Initialize Sentry error tracking
    from app.services.monitoring import init_sentry
    init_sentry(
        dsn=os.getenv("SENTRY_DSN"),
        environment=os.getenv("ENVIRONMENT", "development")
    )
    
    # Note: In production, use Alembic migrations instead of create_all
    # Base.metadata.create_all(bind=db_manager.engine) is only for development
    if os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true":
        Base.metadata.create_all(bind=db_manager.engine)

    app = FastAPI(
        title=os.getenv("APP_NAME", "Baccarat Predictor Pro"),
        version=os.getenv("APP_VERSION", "1.0.0"),
        lifespan=lifespan,
        description="""
        ## Baccarat Predictor Pro API
        
        Professional Baccarat prediction engine với:
        
        - **Real 8-deck shoe simulation** với precise card removal
        - **Professional card counting** (Running/True Count với EOR values)
        - **Machine Learning predictions** với confidence scores
        - **Real-time WebSocket updates**
        - **Statistical analysis** và pattern detection
        - **Simulation capabilities** cho strategy testing
        
        ### Features
        
        - 🎲 Real-time game simulation
        - 📊 Advanced statistics và analysis
        - 🤖 ML-powered predictions
        - 📈 Roadmap visualization (Big Road, Small Road, Cockroach Pig)
        - 🔄 WebSocket real-time updates
        - 💾 Persistent storage với PostgreSQL
        - ⚡ Redis caching cho performance
        
        ### Authentication
        
        Hiện tại API không yêu cầu authentication. Trong production, sẽ thêm JWT authentication.
        
        ### Rate Limiting
        
        - API: 100 requests/minute per IP
        - WebSocket: 10 connections per IP
        
        ### Support
        
        - Interactive API docs: `/docs` (Swagger UI)
        - Alternative docs: `/redoc` (ReDoc)
        - OpenAPI spec: `/openapi.json`
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {
                "name": "v2",
                "description": "API v2 endpoints - Modern RESTful API",
            },
            {
                "name": "health",
                "description": "Health check endpoints",
            },
            {
                "name": "shoes",
                "description": "Shoe management - Create, reset, delete shoes",
            },
            {
                "name": "hands",
                "description": "Hand playing - Play hands, get history",
            },
            {
                "name": "predictions",
                "description": "Predictions - Get predictions, accuracy, confidence",
            },
            {
                "name": "analysis",
                "description": "Analysis - Statistics, patterns, edge calculation",
            },
            {
                "name": "metrics",
                "description": "Metrics - Prometheus metrics và performance stats",
            },
            {
                "name": "websocket",
                "description": "WebSocket - Real-time updates",
            },
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Security middleware (should be early in the stack)
    app.add_middleware(SecurityMiddleware, redis_url=settings.REDIS_URL)
    
    # Performance monitoring middleware
    app.add_middleware(PerformanceMiddleware)

    app.state.predictor = Predictor()
    app.state.app_state = AppState()
    app.state.simulation_manager = SimulationManager(app)
    app.state.ws_manager = ws_manager
    app.state.v2_ws_manager = v2_ws_manager

    # Root level health check for Docker/Kubernetes
    @app.get("/health")
    async def root_health_check():
        """Root level health check endpoint for Docker/Kubernetes."""
        from app.models.database import db_manager
        from app.core.config import get_settings
        
        settings = get_settings()
        db_healthy = db_manager.health_check()
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "version": settings.APP_VERSION,
            "database": "connected" if db_healthy else "disconnected",
        }

    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)
    
    # V2 API routers
    app.include_router(v2_base_router, prefix="/api")
    app.include_router(v2_shoes_router, prefix="/api/v2")
    app.include_router(v2_hands_router, prefix="/api/v2")
    app.include_router(v2_predictions_router, prefix="/api/v2")
    app.include_router(v2_analysis_router, prefix="/api/v2")
    app.include_router(v2_websocket_router)  # WebSocket endpoints at root level
    app.include_router(v2_metrics_router, prefix="/api/v2")  # Metrics endpoints
    app.include_router(ml_endpoints.router, prefix="/api/v2", tags=["ml"])
    app.include_router(v2_performance_router, prefix="/api/v2", tags=["performance"])
    app.include_router(v2_cache_router, prefix="/api/v2")  # Cache management endpoints
    app.include_router(v2_profiling_router, prefix="/api/v2")  # Performance profiling endpoints
    app.include_router(v2_monitoring_dashboard_router, prefix="/api/v2")  # Monitoring dashboard endpoints
    app.include_router(game_analysis.router)  # Game analysis endpoints
    app.include_router(monitoring.router)  # Monitoring endpoints
    app.include_router(dashboard.router)  # Dashboard endpoints

    return app


app = create_app()
