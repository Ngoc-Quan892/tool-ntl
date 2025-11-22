"""
Advanced error recovery with circuit breaker and fallback strategies
"""

import asyncio
import json
import time
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
import traceback
from functools import wraps
import redis
from dataclasses import dataclass

from app.core.config import get_settings

settings = get_settings()


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type = Exception
    

class CircuitBreaker:
    """
    Circuit breaker pattern for fault tolerance
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        # Check if circuit should be opened
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")
        
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                # For async functions, we need to handle differently
                # This is a sync wrapper, so we'll run in event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, we can't use run_until_complete
                        # In this case, we'll just call it and let the caller handle
                        result = func(*args, **kwargs)
                    else:
                        result = loop.run_until_complete(func(*args, **kwargs))
                except RuntimeError:
                    # No event loop, create new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(func(*args, **kwargs))
                    finally:
                        loop.close()
            else:
                result = func(*args, **kwargs)
            
            # Success - update state
            self._on_success()
            
            return result
            
        except self.config.expected_exception as e:
            # Failure - update state
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True
        
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:  # Need 2 successes to close
                self.state = CircuitState.CLOSED
                self.success_count = 0
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.success_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
    
    def get_state(self) -> Dict:
        """Get circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time
        }


class RetryPolicy:
    """
    Retry policy with exponential backoff
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            result = func(*args, **kwargs)
                        else:
                            result = loop.run_until_complete(func(*args, **kwargs))
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(func(*args, **kwargs))
                        finally:
                            loop.close()
                else:
                    result = func(*args, **kwargs)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.base_delay * (self.exponential_base ** attempt),
                        self.max_delay
                    )
                    time.sleep(delay)
        
        # All retries failed
        raise last_exception


class FallbackStrategy:
    """
    Fallback strategies for service failures
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.cache_ttl = 3600  # 1 hour
    
    def with_cache_fallback(
        self,
        func: Callable,
        cache_key: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute with cache fallback"""
        
        try:
            # Try primary function
            if asyncio.iscoroutinefunction(func):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        result = func(*args, **kwargs)
                    else:
                        result = loop.run_until_complete(func(*args, **kwargs))
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(func(*args, **kwargs))
                    finally:
                        loop.close()
            else:
                result = func(*args, **kwargs)
            
            # Update cache on success
            try:
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(result)
                )
            except Exception:
                # Cache update failed, but function succeeded
                pass
            
            return result
            
        except Exception as e:
            # Try cache fallback
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
            
            # No cache available
            raise e
    
    def with_default_fallback(
        self,
        func: Callable,
        default_value: Any,
        *args,
        **kwargs
    ) -> Any:
        """Execute with default value fallback"""
        
        try:
            if asyncio.iscoroutinefunction(func):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        return func(*args, **kwargs)
                    else:
                        return loop.run_until_complete(func(*args, **kwargs))
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(func(*args, **kwargs))
                    finally:
                        loop.close()
            else:
                return func(*args, **kwargs)
        except Exception:
            return default_value
    
    def with_degraded_service(
        self,
        primary_func: Callable,
        degraded_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute with degraded service fallback"""
        
        try:
            if asyncio.iscoroutinefunction(primary_func):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        return primary_func(*args, **kwargs)
                    else:
                        return loop.run_until_complete(primary_func(*args, **kwargs))
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(primary_func(*args, **kwargs))
                    finally:
                        loop.close()
            else:
                return primary_func(*args, **kwargs)
        except Exception:
            # Fall back to degraded service
            if asyncio.iscoroutinefunction(degraded_func):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        return degraded_func(*args, **kwargs)
                    else:
                        return loop.run_until_complete(degraded_func(*args, **kwargs))
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(degraded_func(*args, **kwargs))
                    finally:
                        loop.close()
            else:
                return degraded_func(*args, **kwargs)


class ErrorRecoveryManager:
    """
    Centralized error recovery management
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        redis_url = redis_url or settings.REDIS_URL
        try:
            self.redis_client = redis.from_url(redis_url)
        except Exception:
            # Fallback to basic Redis client if from_url fails
            self.redis_client = redis.Redis.from_url(redis_url)
        self.circuit_breakers = {}
        self.retry_policy = RetryPolicy()
        self.fallback_strategy = FallbackStrategy(self.redis_client)
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker"""
        
        if name not in self.circuit_breakers:
            config = CircuitBreakerConfig()
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        
        return self.circuit_breakers[name]
    
    def resilient_call(
        self,
        func: Callable,
        circuit_name: str,
        cache_key: Optional[str] = None,
        fallback_func: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Make resilient function call with all protection mechanisms
        """
        
        circuit_breaker = self.get_circuit_breaker(circuit_name)
        
        try:
            # Circuit breaker protection
            def protected_call():
                # Retry policy
                return self.retry_policy.execute(func, *args, **kwargs)
            
            result = circuit_breaker.call(protected_call)
            
            # Cache result if key provided
            if cache_key:
                try:
                    self.redis_client.setex(
                        cache_key,
                        3600,
                        json.dumps(result)
                    )
                except Exception:
                    # Cache update failed, but function succeeded
                    pass
            
            return result
            
        except Exception as e:
            # Try fallback strategies
            
            # 1. Cache fallback
            if cache_key:
                try:
                    cached = self.redis_client.get(cache_key)
                    if cached:
                        return json.loads(cached)
                except Exception:
                    pass
            
            # 2. Fallback function
            if fallback_func:
                try:
                    if asyncio.iscoroutinefunction(fallback_func):
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                return fallback_func(*args, **kwargs)
                            else:
                                return loop.run_until_complete(fallback_func(*args, **kwargs))
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                return loop.run_until_complete(fallback_func(*args, **kwargs))
                            finally:
                                loop.close()
                    else:
                        return fallback_func(*args, **kwargs)
                except Exception:
                    pass
            
            # No recovery possible
            raise e
    
    def get_system_health(self) -> Dict:
        """Get overall system health status"""
        
        health = {
            "status": "healthy",
            "circuit_breakers": {},
            "errors_last_hour": 0,
            "degraded_services": []
        }
        
        # Check circuit breakers
        for name, breaker in self.circuit_breakers.items():
            state = breaker.get_state()
            health["circuit_breakers"][name] = state
            
            if state["state"] != "closed":
                health["status"] = "degraded"
                health["degraded_services"].append(name)
        
        # Check error rate
        try:
            errors = self.redis_client.llen("error_log")
            health["errors_last_hour"] = errors
            
            if errors > 100:
                health["status"] = "unhealthy"
        except Exception:
            # Redis unavailable, but don't mark as unhealthy
            pass
        
        return health


# Decorators for easy use

def with_circuit_breaker(circuit_name: str):
    """Decorator to add circuit breaker to function"""
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = ErrorRecoveryManager()
            breaker = manager.get_circuit_breaker(circuit_name)
            return await breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = ErrorRecoveryManager()
            breaker = manager.get_circuit_breaker(circuit_name)
            return breaker.call(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def with_retry(max_retries: int = 3):
    """Decorator to add retry logic"""
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            policy = RetryPolicy(max_retries=max_retries)
            return await policy.execute(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            policy = RetryPolicy(max_retries=max_retries)
            return policy.execute(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def with_fallback(fallback_func: Callable):
    """Decorator to add fallback function"""
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func(*args, **kwargs)
                else:
                    return fallback_func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                return fallback_func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

