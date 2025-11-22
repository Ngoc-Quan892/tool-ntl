# Production Deployment

Thư mục chứa các file cấu hình và scripts cho production deployment.

## 📁 Cấu trúc thư mục

```
deployment/
├── docker-compose.prod.yml    # Docker Compose config cho production
├── env.example                 # Template cho environment variables
├── .env.production            # Production environment (không commit)
├── nginx/
│   └── nginx.conf             # Nginx configuration
├── scripts/
│   ├── deploy.sh              # Deployment script
│   ├── rollback.sh           # Rollback script
│   ├── backup.sh             # Backup script
│   └── health-check.sh       # Health check script
├── backups/                   # Backup directory (tự động tạo)
└── README.md                  # File này
```

## 🚀 Quick Start

### 1. Cấu hình môi trường

```bash
cd deployment
cp env.example .env.production
# Chỉnh sửa .env.production với các giá trị production
```

### 2. Deploy

```bash
chmod +x scripts/*.sh
./scripts/deploy.sh
```

### 3. Kiểm tra

```bash
./scripts/health-check.sh
curl http://localhost/health
```

## 📚 Tài liệu

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Hướng dẫn chi tiết về deployment
- [scripts/README.md](./scripts/README.md) - Hướng dẫn sử dụng scripts

## 🔐 Security

⚠️ **QUAN TRỌNG**: 
- **KHÔNG BAO GIỜ** commit file `.env.production` lên git
- File này chứa passwords và secrets
- Đã được thêm vào `.gitignore`

## 🏥 Health Checks

Tất cả services đều có health checks:

- **PostgreSQL**: `pg_isready`
- **Redis**: `redis-cli ping`
- **Backend**: `GET /health`
- **Frontend**: `GET /`
- **Nginx**: `GET /health`

## 🔄 Rollback

Nếu có vấn đề sau khi deploy:

```bash
# Xem các backups có sẵn
ls -lt backups/

# Rollback
./scripts/rollback.sh [backup_name]
```

## 📊 Monitoring

### Logs

```bash
# Tất cả services
docker-compose -f docker-compose.prod.yml logs -f

# Backend
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost/api/v2/metrics/prometheus

# Metrics dashboard
curl http://localhost/api/v2/metrics
```

## 🆘 Support

Xem [DEPLOYMENT.md](./DEPLOYMENT.md) để biết thêm chi tiết về troubleshooting và best practices.

