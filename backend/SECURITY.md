# Security Implementation Guide

Tài liệu về security implementation cho Baccarat Predictor Pro.

## 📋 Overview

Hệ thống đã được bảo vệ với nhiều lớp security:

1. **Security Middleware** - Multi-layer protection
2. **Authentication Service** - JWT và session management
3. **Rate Limiting** - Distributed rate limiting
4. **Input Validation** - Comprehensive validation
5. **SQL Injection Prevention** - Pattern detection
6. **XSS Prevention** - XSS pattern blocking
7. **CSRF Protection** - Token-based protection
8. **Security Headers** - Comprehensive headers
9. **Audit Logging** - Security event logging

## 🔒 Security Middleware

### Features

- **IP Blocking**: Block suspicious IPs
- **Rate Limiting**: Per-endpoint rate limits
- **CSRF Protection**: Token verification
- **Input Validation**: JSON structure validation
- **SQL Injection Prevention**: Pattern detection
- **XSS Prevention**: XSS pattern blocking
- **Request Signing**: API key signature verification
- **Security Headers**: Comprehensive headers
- **Audit Logging**: All requests logged

### Configuration

Middleware tự động được thêm vào app trong `main.py`:

```python
app.add_middleware(SecurityMiddleware)
```

### Rate Limits

Default rate limits:

- `/api/v2/predictions`: 100 requests/minute
- `/api/v2/simulation`: 10 requests/minute
- `/api/v2/hands`: 200 requests/minute
- Default: 1000 requests/minute

## 🔐 Authentication Service

### Features

- **Password Hashing**: bcrypt với salt
- **JWT Tokens**: Access và refresh tokens
- **Session Management**: Server-side sessions
- **API Keys**: API key generation và verification
- **CSRF Tokens**: CSRF protection
- **Password Validation**: Strength requirements

### Usage

```python
from app.services.authentication import auth_service, get_current_user

# Hash password
hashed = auth_service.hash_password("SecureP@ssw0rd123")

# Verify password
is_valid = auth_service.verify_password(password, hashed)

# Create JWT token
token = auth_service.create_access_token(user_id="user123")

# Verify token
payload = auth_service.verify_token(token)

# Protected route
@router.get("/protected")
async def protected_route(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id}
```

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
- Not a common password

## 🛡️ Security Headers

Tự động thêm các headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: ...`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: ...`

## 📊 Audit Logging

Tất cả requests được log với:

- Timestamp
- IP address
- Method và path
- Query parameters
- Status code
- User agent
- Response time

Security events được log riêng:

- SQL injection attempts
- XSS attempts
- Rate limit violations
- Invalid signatures
- Security exceptions

## 🧪 Testing

### Run Security Tests

```bash
# Run all security tests
pytest backend/tests/security/ -v

# Run specific test
pytest backend/tests/security/test_security.py::TestSecurityMiddleware::test_sql_injection_prevention -v
```

### Security Scans

```bash
# Install security tools
pip install safety bandit

# Check dependencies
safety check

# Scan code
bandit -r backend/app/
```

### Rate Limiting Test

```bash
# Install hey
# brew install hey  # macOS
# Or download from https://github.com/rakyll/hey

# Test rate limiting
hey -n 200 -c 10 http://localhost:8000/api/v2/predictions
```

## ⚙️ Configuration

### Environment Variables

```bash
# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Redis (for distributed rate limiting)
REDIS_URL=redis://localhost:6379/0
```

### Disable Security (Development Only)

Không khuyến nghị, nhưng có thể disable trong development:

```python
# In main.py
if not settings.DEBUG:
    app.add_middleware(SecurityMiddleware)
```

## 🔍 Monitoring

### Security Events

Check Redis cho security events:

```bash
# Connect to Redis
redis-cli

# View security events
LRANGE security_events 0 10

# View SQL injection attempts
LRANGE sql_injection_attempts 0 10

# View rate limit violations
HGETALL rate_limit_violations
```

### Blocked IPs

```bash
# View blocked IPs
SMEMBERS blocked_ips

# Check block reason
GET block_reason:IP_ADDRESS
```

## 🚨 Alerts

Security alerts được gửi đến Redis queue `security_alerts`.

Trong production, cấu hình để gửi đến:
- Slack webhook
- Email
- PagerDuty
- Custom alerting system

## 📝 Best Practices

1. **Always use HTTPS** trong production
2. **Rotate SECRET_KEY** regularly
3. **Monitor security logs** regularly
4. **Review blocked IPs** và adjust rules
5. **Update rate limits** based on usage
6. **Keep dependencies updated** với `safety check`
7. **Run security scans** regularly với `bandit`

## 🔗 Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [bcrypt Documentation](https://github.com/pyca/bcrypt/)

