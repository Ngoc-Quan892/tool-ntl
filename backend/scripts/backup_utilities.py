"""
Backup utilities for production deployment.

Provides:
- Cache backup before deploy
- Database backup helpers
- Config backup
- Restore procedures
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.performance_optimizer import OptimizationStack, new_redis_client
from app.models.database import db_manager
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def backup_cache(optimizer: OptimizationStack, output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    TODO: Save critical cache entries
    
    - Popular game results
    - Pattern statistics
    - User sessions
    
    Args:
        optimizer: OptimizationStack instance
        output_file: Output file path (default: cache_backup_{timestamp}.json)
        
    Returns:
        Backup summary dictionary
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"cache_backup_{timestamp}.json"
    
    cache_manager = optimizer.get_cache_manager()
    backup: Dict[str, Any] = {}
    
    # Critical cache patterns
    critical_patterns = [
        "game_results:*",
        "pattern_stats:*",
        "user_session:*",
        "predictions:*",
    ]
    
    print(f"📦 Backing up cache entries...")
    total_keys = 0
    
    for pattern in critical_patterns:
        try:
            if cache_manager.redis_client:
                # Get all keys matching pattern
                keys = list(cache_manager.redis_client.scan_iter(match=pattern))
                
                for key in keys:
                    try:
                        value = cache_manager.get(key.decode() if isinstance(key, bytes) else key)
                        if value is not None:
                            backup[key.decode() if isinstance(key, bytes) else key] = value
                            total_keys += 1
                    except Exception as e:
                        logger.warning(f"Failed to backup key {key}: {e}")
        except Exception as e:
            logger.warning(f"Failed to scan pattern {pattern}: {e}")
    
    # Also backup local cache
    local_cache = cache_manager.local_cache
    for key, value in local_cache.items():
        if any(pattern.replace("*", "") in key for pattern in critical_patterns):
            backup[f"local:{key}"] = value
            total_keys += 1
    
    # Save to file
    output_path = Path(output_file)
    with open(output_path, "w") as f:
        json.dump(backup, f, indent=2, default=str)
    
    print(f"✅ Backed up {total_keys} cache entries to {output_path}")
    
    return {
        "total_keys": total_keys,
        "output_file": str(output_path),
        "timestamp": datetime.now().isoformat(),
        "patterns": critical_patterns,
    }


def restore_cache(optimizer: OptimizationStack, backup_file: str) -> Dict[str, Any]:
    """
    Restore cache from backup file.
    
    Args:
        optimizer: OptimizationStack instance
        backup_file: Path to backup file
        
    Returns:
        Restore summary dictionary
    """
    backup_path = Path(backup_file)
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")
    
    print(f"📦 Restoring cache from {backup_path}...")
    
    with open(backup_path, "r") as f:
        backup = json.load(f)
    
    cache_manager = optimizer.get_cache_manager()
    restored = 0
    failed = 0
    
    for key, value in backup.items():
        try:
            if key.startswith("local:"):
                # Restore to local cache
                actual_key = key.replace("local:", "")
                cache_manager.local_cache[actual_key] = value
            else:
                # Restore to Redis
                cache_manager.set(key, value, ttl=300)
            restored += 1
        except Exception as e:
            logger.warning(f"Failed to restore key {key}: {e}")
            failed += 1
    
    print(f"✅ Restored {restored} cache entries ({failed} failed)")
    
    return {
        "restored": restored,
        "failed": failed,
        "total": len(backup),
        "timestamp": datetime.now().isoformat(),
    }


def backup_database(output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Backup database using pg_dump or mysqldump.
    
    Args:
        output_dir: Output directory (default: ./backups)
        
    Returns:
        Backup summary dictionary
    """
    if output_dir is None:
        output_dir = "./backups"
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_url = settings.DATABASE_URL
    
    print(f"📦 Backing up database...")
    
    # Determine database type
    if db_url.startswith("postgresql"):
        # PostgreSQL backup
        backup_file = output_path / f"postgres_backup_{timestamp}.sql"
        cmd = [
            "pg_dump",
            db_url,
            "-F", "c",  # Custom format
            "-f", str(backup_file),
        ]
    elif db_url.startswith("mysql"):
        # MySQL backup
        backup_file = output_path / f"mysql_backup_{timestamp}.sql"
        # Parse MySQL URL
        # mysql://user:pass@host:port/dbname
        import re
        match = re.match(r"mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)
        if match:
            user, password, host, port, database = match.groups()
            cmd = [
                "mysqldump",
                f"-h{host}",
                f"-P{port}",
                f"-u{user}",
                f"-p{password}",
                database,
            ]
            with open(backup_file, "w") as f:
                subprocess.run(cmd, stdout=f, check=True)
        else:
            raise ValueError(f"Invalid MySQL URL format: {db_url}")
    else:
        raise ValueError(f"Unsupported database type: {db_url}")
    
    print(f"✅ Database backup saved to {backup_file}")
    
    return {
        "backup_file": str(backup_file),
        "timestamp": datetime.now().isoformat(),
        "database_url": db_url.split("@")[-1] if "@" in db_url else db_url,
    }


def backup_config(output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Backup configuration files and environment variables.
    
    Args:
        output_file: Output file path
        
    Returns:
        Backup summary dictionary
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"config_backup_{timestamp}.json"
    
    print(f"📦 Backing up configuration...")
    
    config_backup: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "settings": {
            "APP_NAME": settings.APP_NAME,
            "DATABASE_URL": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "***",
            "REDIS_URL": settings.REDIS_URL.split("@")[-1] if "@" in settings.REDIS_URL else "***",
            "DB_POOL_SIZE": settings.DB_POOL_SIZE,
            "DB_MAX_OVERFLOW": settings.DB_MAX_OVERFLOW,
            "REDIS_CACHE_TTL": settings.REDIS_CACHE_TTL,
        },
        "env_vars": {},
    }
    
    # Backup non-sensitive env vars
    safe_env_vars = [
        "APP_NAME",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "REDIS_CACHE_TTL",
        "HOST",
        "PORT",
    ]
    
    for var in safe_env_vars:
        value = os.getenv(var)
        if value:
            config_backup["env_vars"][var] = value
    
    # Save to file
    output_path = Path(output_file)
    with open(output_path, "w") as f:
        json.dump(config_backup, f, indent=2)
    
    print(f"✅ Configuration backup saved to {output_path}")
    
    return {
        "output_file": str(output_path),
        "timestamp": datetime.now().isoformat(),
    }


def warm_up_cache(optimizer: OptimizationStack) -> Dict[str, Any]:
    """
    Warm up cache after deployment/restart.
    
    Pre-loads critical cache entries:
    - Popular game results
    - Pattern statistics
    - Common queries
    
    Args:
        optimizer: OptimizationStack instance
        
    Returns:
        Warm-up summary dictionary
    """
    print(f"🔥 Warming up cache...")
    
    cache_manager = optimizer.get_cache_manager()
    warmed = 0
    
    # Warm up pattern statistics
    try:
        from app.api.endpoints.game_analysis import get_pattern_statistics
        from app.models.database import db_manager
        
        with db_manager.get_session() as session:
            query_optimizer = optimizer.get_query_optimizer(session)
            
            # Warm up common patterns
            patterns = ["B", "P", "T", "all"]
            days_list = [7, 14, 30]
            
            for pattern in patterns:
                for days in days_list:
                    try:
                        query_optimizer.get_pattern_statistics(pattern, days)
                        warmed += 1
                    except Exception as e:
                        logger.warning(f"Failed to warm up pattern {pattern}, days={days}: {e}")
    except Exception as e:
        logger.warning(f"Failed to warm up cache: {e}")
    
    print(f"✅ Warmed up {warmed} cache entries")
    
    return {
        "warmed": warmed,
        "timestamp": datetime.now().isoformat(),
    }


def main():
    """Main entry point for backup utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backup utilities for production")
    parser.add_argument(
        "action",
        choices=["backup-cache", "restore-cache", "backup-db", "backup-config", "warm-cache"],
        help="Action to perform",
    )
    parser.add_argument("--file", help="File path for backup/restore")
    parser.add_argument("--output-dir", help="Output directory for backups")
    
    args = parser.parse_args()
    
    # Initialize optimizer
    redis_client = new_redis_client()
    optimizer = OptimizationStack(
        db_connection=db_manager,
        redis_client=redis_client,
    )
    
    if args.action == "backup-cache":
        result = backup_cache(optimizer, args.file)
        print(json.dumps(result, indent=2))
    
    elif args.action == "restore-cache":
        if not args.file:
            print("Error: --file required for restore-cache")
            return
        result = restore_cache(optimizer, args.file)
        print(json.dumps(result, indent=2))
    
    elif args.action == "backup-db":
        result = backup_database(args.output_dir)
        print(json.dumps(result, indent=2))
    
    elif args.action == "backup-config":
        result = backup_config(args.file)
        print(json.dumps(result, indent=2))
    
    elif args.action == "warm-cache":
        result = warm_up_cache(optimizer)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

