# Production Deployment Guide

Hướng dẫn triển khai ứng dụng Baccarat Predictor Pro lên production environment.

## 📋 Mục lục

- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Chuẩn bị](#chuẩn-bị)
- [Cấu hình môi trường](#cấu-hình-môi-trường)
- [Triển khai](#triển-khai)
- [Health Checks](#health-checks)
- [Rollback](#rollback)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## 🖥️ Yêu cầu hệ thống

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM tối thiểu (khuyến nghị 8GB+)
- 20GB disk space
- Ubuntu 20.04+ hoặc tương đương

## 🔧 Chuẩn bị

### 1. Clone repository

```bash
git clone <repository-url>
cd "Tool NTL"
```

### 2. Cài đặt dependencies

```bash
# Backend dependencies (nếu build local)
cd backend
pip install -r requirements.txt

# Frontend dependencies (nếu build local)
cd ../frontend
npm ci
```

## ⚙️ Cấu hình môi trường

### 1. Tạo file environment

```bash
cd deployment
cp env.example .env.production
```

### 2. Cấu hình các biến môi trường

Chỉnh sửa `deployment/.env.production` với các giá trị production:

```bash
# Database
POSTGRES_PASSWORD=<strong-password>
POSTGRES_USER=baccarat_user
POSTGRES_DB=baccarat

# Redis
REDIS_PASSWORD=<strong-redis-password>

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256

# CORS
CORS_ORIGINS=["https://yourdomain.com"]

# Frontend API URL
VITE_API_URL=https://yourdomain.com/api
```

### 3. Tạo Secret Key

```bash
openssl rand -hex 32
```

## 🚀 Triển khai

### Phương pháp 1: Sử dụng deployment script (Khuyến nghị)

```bash
chmod +x deployment/scripts/deploy.sh
./deployment/scripts/deploy.sh
```

### Phương pháp 2: Sử dụng Docker Compose trực tiếp

```bash
cd deployment
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

### Phương pháp 3: Sử dụng CI/CD Pipeline

1. Push code lên branch `main`
2. GitHub Actions sẽ tự động:
   - Chạy tests
   - Build Docker images
   - Deploy lên server (nếu đã cấu hình secrets)

## 🏥 Health Checks

### Kiểm tra health của toàn bộ hệ thống

```bash
curl http://localhost/health
```

### Kiểm tra từng service

```bash
# Backend health
curl http://localhost/api/v2/health

# Database health
curl http://localhost/api/v2/health/db

# Container status
docker-compose -f deployment/docker-compose.prod.yml ps
```

### Health check endpoints

- `GET /health` - Root health check (cho Docker/Kubernetes)
- `GET /api/v2/health` - API health check
- `GET /api/v2/health/db` - Database health check

## 🔄 Rollback

### Phương pháp 1: Sử dụng rollback script (Khuyến nghị)

```bash
# Rollback về version mới nhất
chmod +x deployment/scripts/rollback.sh
./deployment/scripts/rollback.sh

# Rollback về version cụ thể
./deployment/scripts/rollback.sh 20240101_120000
```

### Phương pháp 2: Manual rollback

```bash
cd deployment

# Liệt kê các backups có sẵn
ls -lt backups/

# Restore từ backup
docker-compose -f docker-compose.prod.yml down backend frontend
# Restore images và config từ backup
docker-compose -f docker-compose.prod.yml up -d backend frontend
```

### Phương pháp 3: Sử dụng GitHub Actions

1. Vào GitHub Actions
2. Chọn workflow "CI/CD Pipeline"
3. Chọn "Run workflow"
4. Chọn action: "rollback"
5. Chọn environment và backup directory

## 📊 Monitoring

### Xem logs

```bash
# Tất cả services
docker-compose -f deployment/docker-compose.prod.yml logs -f

# Backend logs
docker-compose -f deployment/docker-compose.prod.yml logs -f backend

# Frontend logs
docker-compose -f deployment/docker-compose.prod.yml logs -f frontend

# Nginx logs
docker-compose -f deployment/docker-compose.prod.yml logs -f nginx
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost/api/v2/metrics/prometheus

# Metrics dashboard
curl http://localhost/api/v2/metrics
```

### Resource usage

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

## 🔍 Troubleshooting

### Service không start

```bash
# Kiểm tra logs
docker-compose -f deployment/docker-compose.prod.yml logs

# Kiểm tra container status
docker-compose -f deployment/docker-compose.prod.yml ps

# Restart service
docker-compose -f deployment/docker-compose.prod.yml restart <service-name>
```

### Database connection issues

```bash
# Kiểm tra PostgreSQL
docker-compose -f deployment/docker-compose.prod.yml exec postgres psql -U baccarat_user -d baccarat -c "SELECT 1;"

# Kiểm tra connection string
docker-compose -f deployment/docker-compose.prod.yml exec backend env | grep DATABASE_URL
```

### Redis connection issues

```bash
# Kiểm tra Redis
docker-compose -f deployment/docker-compose.prod.yml exec redis redis-cli ping

# Test với password
docker-compose -f deployment/docker-compose.prod.yml exec redis redis-cli -a <password> ping
```

### Health check fails

```bash
# Kiểm tra backend health trực tiếp
docker-compose -f deployment/docker-compose.prod.yml exec backend curl http://localhost:8000/health

# Kiểm tra nginx config
docker-compose -f deployment/docker-compose.prod.yml exec nginx nginx -t

# Kiểm tra network connectivity
docker-compose -f deployment/docker-compose.prod.yml exec backend ping postgres
docker-compose -f deployment/docker-compose.prod.yml exec backend ping redis
```

### Port conflicts

```bash
# Kiểm tra ports đang sử dụng
netstat -tulpn | grep -E "(80|443|8000|5432|6379)"

# Thay đổi ports trong .env.production
HTTP_PORT=8080
HTTPS_PORT=8443
```

## 🔐 Security Best Practices

1. **Never commit `.env.production`** - File này chứa secrets
2. **Use strong passwords** - Cho database và Redis
3. **Rotate secrets regularly** - Đặc biệt là SECRET_KEY
4. **Enable HTTPS** - Cấu hình SSL certificates trong nginx
5. **Limit CORS origins** - Chỉ cho phép domains cần thiết
6. **Use firewall** - Chỉ mở ports cần thiết
7. **Regular updates** - Cập nhật Docker images và dependencies

## 📝 Maintenance

### Backup database

```bash
docker-compose -f deployment/docker-compose.prod.yml exec postgres pg_dump -U baccarat_user baccarat > backup_$(date +%Y%m%d).sql
```

### Update dependencies

```bash
# Backend
cd backend
pip install --upgrade -r requirements.txt

# Frontend
cd frontend
npm update
```

### Clean up

```bash
# Remove old images
docker image prune -a

# Remove old backups (keep last 10)
cd deployment/backups
ls -t | tail -n +11 | xargs rm -rf
```

## 🆘 Support

Nếu gặp vấn đề, vui lòng:

1. Kiểm tra logs: `docker-compose -f deployment/docker-compose.prod.yml logs`
2. Kiểm tra health checks: `curl http://localhost/health`
3. Xem troubleshooting section ở trên
4. Tạo issue trên GitHub với logs và error messages

