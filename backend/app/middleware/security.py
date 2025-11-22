"""
Enterprise-grade security middleware with multi-layer protection
Implements OWASP Top 10 security best practices
"""

import hashlib
import hmac
import time
import json
import secrets
import re
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from sqlalchemy.orm import Session
import ipaddress
from collections import defaultdict
import logging
from functools import lru_cache

from app.core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

settings = get_settings()


class SecurityConfig:
    """Security configuration with sensible defaults"""
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 60  # seconds
    RATE_LIMIT_BAN_THRESHOLD = 10
    RATE_LIMIT_BAN_DURATION = 3600  # 1 hour
    
    # Request size limits
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    MAX_JSON_DEPTH = 10
    MAX_ARRAY_LENGTH = 1000
    MAX_STRING_LENGTH = 10000
    MAX_KEY_LENGTH = 100
    
    # Timeouts
    REQUEST_TIMEOUT = 30
    API_SIGNATURE_WINDOW = 300  # 5 minutes
    
    # CSRF
    CSRF_TOKEN_LENGTH = 32
    CSRF_TOKEN_TTL = 3600
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' wss: https:; "
            "frame-ancestors 'none';"
        ),
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
        "Expires": "0"
    }


class SecurityPatterns:
    """Compiled security patterns for performance"""
    
    # SQL Injection patterns (CRITICAL: Use raw strings)
    SQL_PATTERNS = [
        re.compile(r"\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b", re.IGNORECASE),
        re.compile(r"(--|#|\/\*|\*\/)", re.IGNORECASE),
        re.compile(r"\b(OR|AND)\b\s+\d+\s*=\s*\d+", re.IGNORECASE),
        re.compile(r";\s*(DROP|INSERT|UPDATE|DELETE|SELECT)", re.IGNORECASE),
        re.compile(r"\b(CAST|CONVERT|CHAR|CONCAT)\s*\(", re.IGNORECASE),
        re.compile(r"0x[0-9a-fA-F]+", re.IGNORECASE),
        re.compile(r"\b(WAITFOR|DELAY|SLEEP)\b", re.IGNORECASE),
        re.compile(r"(xp_cmdshell|sp_executesql)", re.IGNORECASE),
    ]
    
    # XSS patterns (CRITICAL: Use raw strings)
    XSS_PATTERNS = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),
        re.compile(r"<iframe[^>]*>", re.IGNORECASE),
        re.compile(r"<object[^>]*>", re.IGNORECASE),
        re.compile(r"<embed[^>]*>", re.IGNORECASE),
        re.compile(r"<applet[^>]*>", re.IGNORECASE),
        re.compile(r"eval\s*\(", re.IGNORECASE),
        re.compile(r"expression\s*\(", re.IGNORECASE),
        re.compile(r"vbscript:", re.IGNORECASE),
        re.compile(r"on(load|error|click|mouse\w+)\s*=", re.IGNORECASE),
        re.compile(r"<svg[^>]*on\w+", re.IGNORECASE),
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        re.compile(r"\.\./", re.IGNORECASE),
        re.compile(r"\.\./", re.IGNORECASE),
        re.compile(r"%2e%2e/", re.IGNORECASE),
        re.compile(r"\.\.\\", re.IGNORECASE),
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        re.compile(r"[;&|`$(){}[\]<>]", re.IGNORECASE),
        re.compile(r"\b(bash|sh|cmd|powershell)\b", re.IGNORECASE),
    ]


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Enterprise-grade security middleware
    """
    
    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self.redis_client = None
        
        if REDIS_AVAILABLE:
            try:
                redis_url = redis_url or settings.REDIS_URL
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                # Test connection
                self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis not available for security middleware: {e}")
                self.redis_client = None
        
        self.config = SecurityConfig()
        self.patterns = SecurityPatterns()
        
        # Rate limiting storage
        self.rate_limit_storage = defaultdict(lambda: {
            "count": 0,
            "window_start": time.time(),
            "violations": 0
        })
        
        # Blocked IPs cache (in-memory for performance)
        self._blocked_ips_cache: Set[str] = set()
        self._cache_last_update = time.time()
        self._cache_ttl = 60  # Refresh every minute
    
    async def dispatch(self, request: Request, call_next):
        """
        Main security processing pipeline
        """
        start_time = time.time()
        request.state.start_time = start_time
        
        try:
            # 1. IP Blocking Check (fastest check first)
            await self._check_ip_blocked(request)
            
            # 2. Rate Limiting
            await self._enforce_rate_limit(request)
            
            # 3. Request Size Validation
            await self._validate_request_size(request)
            
            # 4. Input Validation & Sanitization
            await self._validate_and_sanitize_input(request)
            
            # 5. SQL Injection Prevention
            await self._check_sql_injection(request)
            
            # 6. XSS Prevention
            await self._check_xss(request)
            
            # 7. Path Traversal Prevention
            await self._check_path_traversal(request)
            
            # 8. CSRF Protection (for state-changing operations)
            if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                await self._verify_csrf_token(request)
            
            # 9. API Signature Verification (for API endpoints)
            if request.url.path.startswith("/api/v2/"):
                await self._verify_api_signature(request)
            
            # Process request
            response = await call_next(request)
            
            # 10. Add Security Headers
            response = self._add_security_headers(response)
            
            # 11. Audit Logging
            await self._audit_log(request, response, time.time() - start_time)
            
            return response
            
        except HTTPException as e:
            # Log security exceptions
            await self._log_security_event(request, e, time.time() - start_time)
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            # Log unexpected errors (but don't expose details)
            logger.error(f"Unexpected security error: {str(e)}", exc_info=True)
            await self._log_security_event(request, e, time.time() - start_time)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
    
    async def _check_ip_blocked(self, request: Request):
        """Check if IP is blocked with caching"""
        client_ip = self._get_client_ip(request)
        
        # Refresh cache if needed
        if time.time() - self._cache_last_update > self._cache_ttl:
            self._refresh_blocked_ips_cache()
        
        # Check in-memory cache first
        if client_ip in self._blocked_ips_cache:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check suspicious IP patterns
        if self._is_suspicious_ip(client_ip):
            await self._flag_suspicious_activity(request, "Suspicious IP pattern detected")
    
    def _refresh_blocked_ips_cache(self):
        """Refresh blocked IPs cache from Redis"""
        if not self.redis_client:
            return
        
        try:
            blocked_ips = self.redis_client.smembers("blocked_ips")
            self._blocked_ips_cache = {ip.decode() if isinstance(ip, bytes) else ip for ip in blocked_ips}
            self._cache_last_update = time.time()
        except redis.RedisError as e:
            logger.error(f"Failed to refresh blocked IPs cache: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP with proxy header support"""
        # Check X-Forwarded-For header
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"
    
    def _is_suspicious_ip(self, ip: str) -> bool:
        """Check if IP matches suspicious patterns"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Check for private/reserved ranges (suspicious in production)
            # In development, allow private IPs
            if settings.DEBUG:
                return False
            
            if ip_obj.is_private or ip_obj.is_reserved or ip_obj.is_loopback:
                return True
            
            # Check against known malicious ranges (would integrate with threat intelligence)
            # For now, just basic checks
            
            return False
        except ValueError:
            # Invalid IP format is suspicious
            return True
    
    async def _enforce_rate_limit(self, request: Request):
        """
        Advanced rate limiting with per-endpoint limits
        """
        client_ip = self._get_client_ip(request)
        endpoint = request.url.path
        
        # Different limits for different endpoints
        endpoint_limits = {
            "/api/v2/predictions": {"requests": 100, "window": 60},
            "/api/v2/simulation": {"requests": 10, "window": 60},
            "/api/v2/hands/play": {"requests": 200, "window": 60},
            "default": {"requests": self.config.RATE_LIMIT_REQUESTS, "window": self.config.RATE_LIMIT_WINDOW}
        }
        
        # Get limit configuration
        limit_config = endpoint_limits.get(endpoint, endpoint_limits["default"])
        
        # Redis-based distributed rate limiting
        if self.redis_client:
            try:
                key = f"rate_limit:{client_ip}:{endpoint}"
                current = self.redis_client.incr(key)
                if current == 1:
                    self.redis_client.expire(key, limit_config["window"])
                
                if current > limit_config["requests"]:
                    # Log violation
                    await self._log_rate_limit_violation(request)
                    
                    # Track violations for IP blocking
                    violations_key = f"violations:{client_ip}"
                    violations = self.redis_client.incr(violations_key)
                    if violations == 1:
                        self.redis_client.expire(violations_key, 3600)
                    
                    # Block IP if too many violations
                    if violations > self.config.RATE_LIMIT_BAN_THRESHOLD:
                        await self._block_ip(
                            client_ip,
                            reason="rate_limit_abuse",
                            duration=self.config.RATE_LIMIT_BAN_DURATION
                        )
                    
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Try again in {limit_config['window']} seconds"
                    )
            except redis.RedisError as e:
                logger.error(f"Redis error in rate limiting: {e}")
                # Fallback to local rate limiting
                await self._local_rate_limit(request, client_ip, endpoint, limit_config)
        else:
            # Use local rate limiting
            await self._local_rate_limit(request, client_ip, endpoint, limit_config)
    
    async def _local_rate_limit(
        self,
        request: Request,
        client_ip: str,
        endpoint: str,
        limit_config: Dict
    ):
        """Fallback local rate limiting when Redis is unavailable"""
        key = f"{client_ip}:{endpoint}"
        current_time = time.time()
        
        if key in self.rate_limit_storage:
            data = self.rate_limit_storage[key]
            
            # Reset window if expired
            if current_time - data["window_start"] > limit_config["window"]:
                data["count"] = 0
                data["window_start"] = current_time
            
            data["count"] += 1
            
            if data["count"] > limit_config["requests"]:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )
        else:
            self.rate_limit_storage[key] = {
                "count": 1,
                "window_start": current_time
            }
    
    async def _validate_request_size(self, request: Request):
        """Validate request size limits"""
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > self.config.MAX_CONTENT_LENGTH:
                    raise HTTPException(
                        status_code=413,
                        detail="Request too large"
                    )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid content length")
    
    async def _validate_and_sanitize_input(self, request: Request):
        """
        Comprehensive input validation and sanitization
        """
        # Validate Content-Type
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            try:
                body = await request.body()
                if body:
                    json_data = json.loads(body)
                    self._validate_json_structure(json_data, depth=0)
                    # Store sanitized data for later use
                    request.state.sanitized_json = json_data
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format")
            except ValueError as e:
                raise HTTPException(status_code=400, detail="Invalid input")
    
    def _validate_json_structure(self, data: Any, depth: int = 0):
        """
        Recursively validate JSON structure
        """
        if depth > self.config.MAX_JSON_DEPTH:
            raise ValueError(f"JSON nested too deeply (max depth: {self.config.MAX_JSON_DEPTH})")
        
        if isinstance(data, dict):
            if len(data) > self.config.MAX_ARRAY_LENGTH:
                raise ValueError(f"Object has too many keys (max: {self.config.MAX_ARRAY_LENGTH})")
            
            for key, value in data.items():
                if not isinstance(key, str):
                    raise ValueError("JSON keys must be strings")
                if len(key) > self.config.MAX_KEY_LENGTH:
                    raise ValueError(f"Key too long (max: {self.config.MAX_KEY_LENGTH})")
                
                self._validate_json_structure(value, depth + 1)
        
        elif isinstance(data, list):
            if len(data) > self.config.MAX_ARRAY_LENGTH:
                raise ValueError(f"Array too large (max: {self.config.MAX_ARRAY_LENGTH})")
            
            for item in data:
                self._validate_json_structure(item, depth + 1)
        
        elif isinstance(data, str):
            if len(data) > self.config.MAX_STRING_LENGTH:
                raise ValueError(f"String too long (max: {self.config.MAX_STRING_LENGTH})")
    
    async def _check_sql_injection(self, request: Request):
        """
        Advanced SQL injection detection
        """
        # Check query parameters
        for param_name, param_value in request.query_params.items():
            if self._contains_sql_injection(param_value):
                await self._log_attack_attempt(request, "sql_injection", param_value)
                await self._block_ip(
                    self._get_client_ip(request),
                    reason="sql_injection_attempt",
                    duration=86400  # 24 hours
                )
                raise HTTPException(status_code=400, detail="Invalid input detected")
        
        # Check JSON body (if exists)
        if hasattr(request.state, "sanitized_json"):
            self._check_json_for_sql_injection(request.state.sanitized_json, request)
    
    def _contains_sql_injection(self, value: str) -> bool:
        """Check if value contains SQL injection patterns"""
        if not isinstance(value, str):
            return False
        
        for pattern in self.patterns.SQL_PATTERNS:
            if pattern.search(value):
                return True
        
        return False
    
    def _check_json_for_sql_injection(self, data: Any, request: Request):
        """Recursively check JSON for SQL injection"""
        if isinstance(data, dict):
            for value in data.values():
                self._check_json_for_sql_injection(value, request)
        elif isinstance(data, list):
            for item in data:
                self._check_json_for_sql_injection(item, request)
        elif isinstance(data, str):
            if self._contains_sql_injection(data):
                raise HTTPException(status_code=400, detail="Invalid input in JSON body")
    
    async def _check_xss(self, request: Request):
        """
        Advanced XSS detection
        """
        # Check query parameters
        for param_value in request.query_params.values():
            if self._contains_xss(param_value):
                await self._log_attack_attempt(request, "xss_attempt", param_value)
                raise HTTPException(status_code=400, detail="Invalid input detected")
        
        # Check suspicious headers (log but don't block)
        suspicious_headers = ["Referer", "User-Agent", "X-Forwarded-For"]
        for header in suspicious_headers:
            header_value = request.headers.get(header, "")
            if self._contains_xss(header_value):
                await self._log_attack_attempt(request, "xss_in_header", header_value)
                # Don't block for headers, just log
    
    def _contains_xss(self, value: str) -> bool:
        """Check if value contains XSS patterns"""
        if not isinstance(value, str):
            return False
        
        for pattern in self.patterns.XSS_PATTERNS:
            if pattern.search(value):
                return True
        
        return False
    
    async def _check_path_traversal(self, request: Request):
        """Check for path traversal attempts"""
        path = request.url.path
        
        for pattern in self.patterns.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(path):
                await self._log_attack_attempt(request, "path_traversal", path)
                raise HTTPException(status_code=400, detail="Invalid path")
    
    async def _verify_csrf_token(self, request: Request):
        """
        CSRF token verification for state-changing operations
        """
        # Skip for API endpoints with proper authentication
        if request.url.path.startswith("/api/") and "Authorization" in request.headers:
            return
        
        # Get token from header
        token_header = request.headers.get("X-CSRF-Token")
        
        if not token_header:
            raise HTTPException(status_code=403, detail="CSRF token missing")
        
        # Get session ID from cookie
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(status_code=403, detail="Session not found")
        
        # Verify token
        if not self.redis_client:
            # Fallback: skip CSRF if Redis unavailable (development)
            if settings.DEBUG:
                return
            raise HTTPException(status_code=500, detail="Security verification unavailable")
        
        try:
            expected_token_bytes = self.redis_client.get(f"csrf:{session_id}")
            if not expected_token_bytes:
                raise HTTPException(status_code=403, detail="CSRF token expired")
            
            expected_token = expected_token_bytes.decode() if isinstance(expected_token_bytes, bytes) else expected_token_bytes
            
            if not secrets.compare_digest(expected_token, token_header):
                raise HTTPException(status_code=403, detail="Invalid CSRF token")
        except redis.RedisError as e:
            logger.error(f"Redis error in CSRF verification: {e}")
            raise HTTPException(status_code=500, detail="Security verification failed")
    
    async def _verify_api_signature(self, request: Request):
        """
        Verify API request signature for authenticated endpoints
        """
        # Skip for public endpoints
        public_endpoints = [
            "/api/v2/health",
            "/api/v2/docs",
            "/api/v2/openapi.json",
            "/api/v2/redoc"
        ]
        
        if request.url.path in public_endpoints:
            return
        
        # Get signature headers
        signature = request.headers.get("X-API-Signature")
        api_key = request.headers.get("X-API-Key")
        timestamp = request.headers.get("X-Timestamp")
        
        if not all([signature, api_key, timestamp]):
            # No API key auth, skip (will rely on JWT)
            return
        
        # Verify timestamp (prevent replay attacks)
        try:
            req_timestamp = int(timestamp)
            current_timestamp = int(time.time())
            
            if abs(current_timestamp - req_timestamp) > self.config.API_SIGNATURE_WINDOW:
                raise HTTPException(status_code=401, detail="Request expired")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid timestamp")
        
        # Get API secret from Redis
        if not self.redis_client:
            return  # Skip if Redis unavailable
        
        try:
            api_secret_bytes = self.redis_client.get(f"api_key:{api_key}")
            if not api_secret_bytes:
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            # Parse stored data
            key_data = json.loads(api_secret_bytes.decode() if isinstance(api_secret_bytes, bytes) else api_secret_bytes)
            api_secret = key_data.get("secret_hash")
            
            if not api_secret:
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            # Calculate expected signature
            body = b""
            if hasattr(request.state, "sanitized_json"):
                body = json.dumps(request.state.sanitized_json).encode()
            else:
                body = await request.body()
            
            message = f"{request.method}:{request.url.path}:{timestamp}:{body.decode('utf-8', errors='ignore')}"
            expected_signature = hmac.new(
                api_secret.encode() if isinstance(api_secret, str) else api_secret,
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Constant time comparison
            if not hmac.compare_digest(signature, expected_signature):
                await self._log_attack_attempt(request, "invalid_api_signature", api_key)
                raise HTTPException(status_code=401, detail="Invalid signature")
                
        except json.JSONDecodeError:
            raise HTTPException(status_code=401, detail="Invalid API key")
        except redis.RedisError as e:
            logger.error(f"Redis error in API signature verification: {e}")
            raise HTTPException(status_code=500, detail="Security verification failed")
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add comprehensive security headers"""
        for header, value in self.config.SECURITY_HEADERS.items():
            response.headers[header] = value
        
        return response
    
    async def _audit_log(self, request: Request, response: Response, response_time: float):
        """
        Comprehensive audit logging
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "ip": self._get_client_ip(request),
            "method": request.method,
            "path": request.url.path,
            "query": dict(request.query_params),
            "status_code": response.status_code,
            "user_agent": request.headers.get("User-Agent", ""),
            "referer": request.headers.get("Referer", ""),
            "response_time_ms": round(response_time * 1000, 2),
            "request_id": request.headers.get("X-Request-ID", "")
        }
        
        if self.redis_client:
            try:
                # Log to Redis for real-time analysis
                self.redis_client.lpush("audit_log", json.dumps(log_entry))
                self.redis_client.ltrim("audit_log", 0, 9999)  # Keep last 10k entries
                
                # Log security-relevant events separately
                if response.status_code >= 400:
                    self.redis_client.lpush("security_log", json.dumps(log_entry))
                    self.redis_client.ltrim("security_log", 0, 999)  # Keep last 1k entries
            except redis.RedisError as e:
                logger.error(f"Failed to write audit log: {e}")
    
    async def _log_security_event(self, request: Request, exception: Exception, response_time: float):
        """Log security-related exceptions"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "security_exception",
            "ip": self._get_client_ip(request),
            "path": request.url.path,
            "exception_type": type(exception).__name__,
            "exception_message": "Security violation detected",  # Don't leak details
            "response_time_ms": round(response_time * 1000, 2),
            "user_agent": request.headers.get("User-Agent", ""),
        }
        
        if self.redis_client:
            try:
                self.redis_client.lpush("security_events", json.dumps(event))
                self.redis_client.ltrim("security_events", 0, 999)
                
                # Alert on critical events
                if isinstance(exception, HTTPException) and exception.status_code == 403:
                    await self._send_security_alert(event)
            except redis.RedisError as e:
                logger.error(f"Failed to log security event: {e}")
    
    async def _log_attack_attempt(self, request: Request, attack_type: str, payload: str):
        """Log attack attempts"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": attack_type,
            "ip": self._get_client_ip(request),
            "path": request.url.path,
            "payload": payload[:1000],  # Truncate for safety
            "user_agent": request.headers.get("User-Agent", "")
        }
        
        if self.redis_client:
            try:
                self.redis_client.lpush(f"attack_{attack_type}", json.dumps(event))
                self.redis_client.ltrim(f"attack_{attack_type}", 0, 99)
            except redis.RedisError as e:
                logger.error(f"Failed to log attack attempt: {e}")
    
    async def _log_rate_limit_violation(self, request: Request):
        """Log rate limit violations"""
        client_ip = self._get_client_ip(request)
        if self.redis_client:
            try:
                self.redis_client.hincrby("rate_limit_violations", client_ip, 1)
            except redis.RedisError as e:
                logger.error(f"Failed to log rate limit violation: {e}")
    
    async def _block_ip(self, ip: str, reason: str, duration: int = 3600):
        """Block an IP address"""
        try:
            if self.redis_client:
                self.redis_client.sadd("blocked_ips", ip)
                self.redis_client.setex(f"block_reason:{ip}", duration, reason)
            
            # Update cache
            self._blocked_ips_cache.add(ip)
            
            # Log the blocking
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "ip_blocked",
                "ip": ip,
                "reason": reason,
                "duration": duration
            }
            
            if self.redis_client:
                self.redis_client.lpush("security_actions", json.dumps(log_entry))
            
            logger.warning(f"Blocked IP {ip} for {reason} ({duration}s)")
        except Exception as e:
            logger.error(f"Failed to block IP: {e}")
    
    async def _flag_suspicious_activity(self, request: Request, reason: str):
        """Flag suspicious activity for monitoring"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "suspicious_activity",
            "ip": self._get_client_ip(request),
            "path": request.url.path,
            "reason": reason,
            "user_agent": request.headers.get("User-Agent", "")
        }
        
        if self.redis_client:
            try:
                self.redis_client.lpush("suspicious_activity", json.dumps(event))
                self.redis_client.ltrim("suspicious_activity", 0, 999)
            except redis.RedisError as e:
                logger.error(f"Failed to flag suspicious activity: {e}")
    
    async def _send_security_alert(self, event: Dict):
        """Send security alert to administrators"""
        alert = {
            "timestamp": event.get("timestamp"),
            "type": "SECURITY_ALERT",
            "severity": "HIGH",
            "event": event
        }
        
        if self.redis_client:
            try:
                # Queue for alert processing
                self.redis_client.lpush("security_alerts", json.dumps(alert))
                
                # In production, integrate with:
                # - Slack/Discord webhooks
                # - PagerDuty
                # - Email notifications
                # - SMS alerts
                
                logger.critical(f"Security alert: {json.dumps(alert)}")
            except redis.RedisError as e:
                logger.error(f"Failed to send security alert: {e}")
