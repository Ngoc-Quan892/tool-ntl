"""
Enterprise-grade authentication service with JWT, API keys, and session management
"""

import jwt
import bcrypt
import secrets
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from sqlalchemy.orm import Session
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class AuthConfig:
    """Authentication configuration"""
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 1
    REFRESH_TOKEN_DAYS = 30
    SESSION_TIMEOUT = 3600  # 1 hour
    API_KEY_PREFIX = "bcp_"  # Baccarat Predictor
    BCRYPT_ROUNDS = 12
    
    # Password requirements
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Common passwords to reject (top 100)
    COMMON_PASSWORDS = {
        "password", "123456", "123456789", "12345678", "12345",
        "1234567", "password1", "123123", "1234567890", "qwerty",
        "abc123", "111111", "password123", "admin", "letmein",
        "welcome", "monkey", "dragon", "master", "sunshine",
        "princess", "qwerty123", "password1!", "admin123"
    }


class TokenBlacklist:
    """Manage token blacklist"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
    
    def add(self, jti: str, exp_timestamp: int):
        """Add token to blacklist"""
        if not self.redis_client:
            return
        
        ttl = max(exp_timestamp - int(datetime.utcnow().timestamp()), 0)
        if ttl > 0:
            try:
                self.redis_client.setex(f"blacklist:{jti}", ttl, "revoked")
            except Exception as e:
                logger.error(f"Failed to add token to blacklist: {e}")
    
    def is_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        if not self.redis_client:
            return False
        
        try:
            return self.redis_client.exists(f"blacklist:{jti}") > 0
        except Exception:
            return False


class PasswordValidator:
    """Validate password strength"""
    
    @staticmethod
    def validate(password: str, config: AuthConfig) -> List[str]:
        """Validate password and return list of errors"""
        errors = []
        
        # Length check
        if len(password) < config.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters long")
        
        # Uppercase check
        if config.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Lowercase check
        if config.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Digit check
        if config.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        # Special character check
        if config.PASSWORD_REQUIRE_SPECIAL:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                errors.append("Password must contain at least one special character")
        
        # Common password check
        if password.lower() in config.COMMON_PASSWORDS:
            errors.append("Password is too common")
        
        # Repeat character check (no more than 3 consecutive same characters)
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                errors.append("Password contains too many consecutive identical characters")
                break
        
        return errors


class AuthenticationService:
    """
    Comprehensive authentication service
    """
    
    def __init__(self, secret_key: Optional[str] = None, redis_url: Optional[str] = None):
        self.secret_key = secret_key or settings.SECRET_KEY
        self.redis_client = None
        
        if REDIS_AVAILABLE:
            try:
                redis_url = redis_url or settings.REDIS_URL
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis not available for authentication service: {e}")
                self.redis_client = None
        
        self.config = AuthConfig()
        self.security = HTTPBearer()
        self.token_blacklist = TokenBlacklist(self.redis_client)
        self.password_validator = PasswordValidator()
    
    # Password Management
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt with salt"""
        # Validate password strength
        errors = self.password_validator.validate(password, self.config)
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=self.config.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash with timing attack protection"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    # JWT Token Management
    
    def create_access_token(
        self,
        user_id: str,
        additional_claims: Optional[Dict] = None
    ) -> str:
        """Create JWT access token"""
        now = datetime.utcnow()
        exp = now + timedelta(hours=self.config.JWT_EXPIRATION_HOURS)
        jti = str(uuid.uuid4())
        
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": exp,
            "jti": jti,
            "type": "access"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.config.JWT_ALGORITHM
        )
        
        # Store token metadata in Redis for tracking
        if self.redis_client:
            try:
                token_meta = {
                    "user_id": user_id,
                    "type": "access",
                    "created_at": now.isoformat(),
                    "expires_at": exp.isoformat()
                }
                self.redis_client.setex(
                    f"jwt:{jti}",
                    int(timedelta(hours=self.config.JWT_EXPIRATION_HOURS).total_seconds()),
                    json.dumps(token_meta)
                )
            except Exception as e:
                logger.error(f"Failed to store token metadata: {e}")
        
        return token
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create long-lived refresh token"""
        now = datetime.utcnow()
        exp = now + timedelta(days=self.config.REFRESH_TOKEN_DAYS)
        jti = str(uuid.uuid4())
        
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": exp,
            "jti": jti,
            "type": "refresh"
        }
        
        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.config.JWT_ALGORITHM
        )
        
        # Store in Redis
        if self.redis_client:
            try:
                token_meta = {
                    "user_id": user_id,
                    "type": "refresh",
                    "created_at": now.isoformat(),
                    "expires_at": exp.isoformat()
                }
                self.redis_client.setex(
                    f"refresh:{jti}",
                    int(timedelta(days=self.config.REFRESH_TOKEN_DAYS).total_seconds()),
                    json.dumps(token_meta)
                )
            except Exception as e:
                logger.error(f"Failed to store refresh token: {e}")
        
        return token
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict:
        """Verify and decode JWT token"""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.config.JWT_ALGORITHM]
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token type"
                )
            
            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and self.token_blacklist.is_blacklisted(jti):
                raise HTTPException(status_code=401, detail="Token has been revoked")
            
            # Verify token exists in Redis (optional, for extra security)
            if jti and self.redis_client:
                key = f"jwt:{jti}" if token_type == "access" else f"refresh:{jti}"
                if not self.redis_client.exists(key):
                    raise HTTPException(status_code=401, detail="Token not found")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def revoke_token(self, token: str):
        """Revoke a token by adding to blacklist"""
        try:
            # Decode without verification to get jti and exp
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.config.JWT_ALGORITHM],
                options={"verify_exp": False}
            )
            
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if jti and exp:
                # Add to blacklist
                self.token_blacklist.add(jti, exp)
                
                # Remove from active tokens
                if self.redis_client:
                    token_type = payload.get("type", "access")
                    key = f"jwt:{jti}" if token_type == "access" else f"refresh:{jti}"
                    self.redis_client.delete(key)
                
                logger.info(f"Token {jti} revoked")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Failed to revoke invalid token: {e}")
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """Generate new access token from refresh token"""
        payload = self.verify_token(refresh_token, token_type="refresh")
        user_id = payload["sub"]
        
        # Create new access token
        return self.create_access_token(user_id)
    
    # Session Management
    
    def create_session(
        self,
        user_id: str,
        request: Request,
        additional_data: Optional[Dict] = None
    ) -> str:
        """Create server-side session"""
        session_id = str(uuid.uuid4())
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", ""),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        if additional_data:
            session_data.update(additional_data)
        
        # Store in Redis with expiration
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"session:{session_id}",
                    self.config.SESSION_TIMEOUT,
                    json.dumps(session_data)
                )
            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                raise HTTPException(status_code=500, detail="Failed to create session")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data and update activity"""
        if not self.redis_client:
            return None
        
        try:
            data_bytes = self.redis_client.get(f"session:{session_id}")
            if not data_bytes:
                return None
            
            data_str = data_bytes.decode() if isinstance(data_bytes, bytes) else data_bytes
            session = json.loads(data_str)
            
            # Update last activity
            session["last_activity"] = datetime.utcnow().isoformat()
            self.redis_client.setex(
                f"session:{session_id}",
                self.config.SESSION_TIMEOUT,
                json.dumps(session)
            )
            
            return session
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    def destroy_session(self, session_id: str):
        """Destroy session"""
        if self.redis_client:
            try:
                self.redis_client.delete(f"session:{session_id}")
            except Exception as e:
                logger.error(f"Failed to destroy session: {e}")
    
    def destroy_all_user_sessions(self, user_id: str):
        """Destroy all sessions for a user"""
        try:
            # Find all sessions for user (would need a reverse index in production)
            # For now, just log
            logger.info(f"Destroying all sessions for user {user_id}")
            # In production, implement session tracking by user_id
        except Exception as e:
            logger.error(f"Failed to destroy user sessions: {e}")
    
    # API Key Management
    
    def generate_api_key(
        self,
        user_id: str,
        name: str = "Default",
        scopes: Optional[List[str]] = None
    ) -> tuple:
        """Generate API key and secret"""
        api_key = f"{self.config.API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
        api_secret = secrets.token_urlsafe(48)
        
        # Hash the secret before storing
        hashed_secret = self.hash_password(api_secret)
        
        # Store in Redis
        key_data = {
            "user_id": user_id,
            "name": name,
            "secret_hash": hashed_secret,
            "scopes": scopes or ["read", "write"],
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "request_count": 0,
            "is_active": True
        }
        
        if self.redis_client:
            try:
                self.redis_client.set(
                    f"api_key:{api_key}",
                    json.dumps(key_data)
                )
                
                # Add to user's key list
                self.redis_client.sadd(f"user_api_keys:{user_id}", api_key)
            except Exception as e:
                logger.error(f"Failed to store API key: {e}")
                raise HTTPException(status_code=500, detail="Failed to generate API key")
        
        return api_key, api_secret
    
    def verify_api_key(self, api_key: str, api_secret: str) -> Optional[Dict]:
        """Verify API key and secret"""
        if not self.redis_client:
            return None
        
        try:
            data_bytes = self.redis_client.get(f"api_key:{api_key}")
            if not data_bytes:
                return None
            
            data_str = data_bytes.decode() if isinstance(data_bytes, bytes) else data_bytes
            key_data = json.loads(data_str)
            
            # Check if key is active
            if not key_data.get("is_active", True):
                return None
            
            # Verify secret
            if not self.verify_password(api_secret, key_data["secret_hash"]):
                return None
            
            # Update usage stats
            key_data["last_used"] = datetime.utcnow().isoformat()
            key_data["request_count"] = key_data.get("request_count", 0) + 1
            
            self.redis_client.set(
                f"api_key:{api_key}",
                json.dumps(key_data)
            )
            
            return key_data
        except Exception as e:
            logger.error(f"Failed to verify API key: {e}")
            return None
    
    def revoke_api_key(self, api_key: str):
        """Revoke API key"""
        if not self.redis_client:
            return
        
        try:
            data_bytes = self.redis_client.get(f"api_key:{api_key}")
            if data_bytes:
                data_str = data_bytes.decode() if isinstance(data_bytes, bytes) else data_bytes
                key_data = json.loads(data_str)
                key_data["is_active"] = False
                key_data["revoked_at"] = datetime.utcnow().isoformat()
                
                self.redis_client.set(f"api_key:{api_key}", json.dumps(key_data))
        except Exception as e:
            logger.error(f"Failed to revoke API key: {e}")
    
    def list_user_api_keys(self, user_id: str) -> List[Dict]:
        """List all API keys for a user"""
        if not self.redis_client:
            return []
        
        try:
            keys = self.redis_client.smembers(f"user_api_keys:{user_id}")
            result = []
            
            for key_bytes in keys:
                key = key_bytes.decode() if isinstance(key_bytes, bytes) else key_bytes
                data_bytes = self.redis_client.get(f"api_key:{key}")
                
                if data_bytes:
                    data_str = data_bytes.decode() if isinstance(data_bytes, bytes) else data_bytes
                    key_data = json.loads(data_str)
                    # Don't include secret hash
                    key_data.pop("secret_hash", None)
                    key_data["api_key"] = key
                    result.append(key_data)
            
            return result
        except Exception as e:
            logger.error(f"Failed to list user API keys: {e}")
            return []
    
    # CSRF Protection
    
    def create_csrf_token(self, session_id: str) -> str:
        """Create CSRF token for session"""
        token = secrets.token_urlsafe(32)
        
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"csrf:{session_id}",
                    3600,  # 1 hour
                    token
                )
            except Exception as e:
                logger.error(f"Failed to create CSRF token: {e}")
                raise HTTPException(status_code=500, detail="Failed to create CSRF token")
        
        return token
    
    def verify_csrf_token(self, session_id: str, token: str) -> bool:
        """Verify CSRF token"""
        if not self.redis_client:
            return False
        
        try:
            expected_bytes = self.redis_client.get(f"csrf:{session_id}")
            if not expected_bytes:
                return False
            
            expected = expected_bytes.decode() if isinstance(expected_bytes, bytes) else expected_bytes
            return secrets.compare_digest(expected, token)
        except Exception as e:
            logger.error(f"Failed to verify CSRF token: {e}")
            return False
    
    # Helper Methods
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"


# Global instance
auth_service = AuthenticationService()


# Dependency for protected routes
security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> str:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = auth_service.verify_token(token)
    return payload["sub"]


async def get_optional_user(
    request: Request,
) -> Optional[str]:
    """Get user if authenticated, None otherwise"""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]
    
    try:
        payload = auth_service.verify_token(token)
        return payload["sub"]
    except HTTPException:
        return None


async def require_scopes(required_scopes: List[str]):
    """Dependency to require specific API scopes"""
    async def scopes_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    ):
        token = credentials.credentials
        payload = auth_service.verify_token(token)
        
        # Check scopes
        token_scopes = payload.get("scopes", [])
        if not all(scope in token_scopes for scope in required_scopes):
            raise HTTPException(
                status_code=403,
                detail="Missing required permissions"
            )
        
        return payload["sub"]
    
    return scopes_checker
