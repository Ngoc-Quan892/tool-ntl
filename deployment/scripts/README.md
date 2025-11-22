# Deployment Scripts

Các scripts hỗ trợ cho việc triển khai và quản lý production deployment.

## 📋 Scripts

### 1. `deploy.sh` - Deployment Script

Script chính để triển khai ứng dụng lên production.

**Usage:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Chức năng:**
- Tạo backup tự động trước khi deploy
- Pull latest Docker images
- Build và deploy services
- Chạy health checks
- Clean up old images và backups

### 2. `rollback.sh` - Rollback Script

Rollback về version trước đó khi có vấn đề.

**Usage:**
```bash
# Rollback về version mới nhất
chmod +x rollback.sh
./rollback.sh

# Rollback về version cụ thể
./rollback.sh 20240101_120000
```

**Chức năng:**
- Liệt kê các backups có sẵn
- Restore từ backup được chỉ định
- Verify health checks sau rollback
- Backup trạng thái hiện tại trước khi rollback

### 3. `backup.sh` - Backup Script

Tạo backup thủ công của deployment hiện tại.

**Usage:**
```bash
chmod +x backup.sh
./backup.sh [backup_name]
```

**Chức năng:**
- Backup Docker Compose configuration
- Backup container status
- Backup image information
- Backup database (nếu có)
- Lưu git commit và branch info

### 4. `health-check.sh` - Health Check Script

Kiểm tra health của tất cả services.

**Usage:**
```bash
chmod +x health-check.sh
./health-check.sh
```

**Chức năng:**
- Kiểm tra Docker Compose
- Kiểm tra container status
- Kiểm tra PostgreSQL
- Kiểm tra Redis
- Kiểm tra Backend API
- Kiểm tra Frontend
- Kiểm tra Nginx
- Hiển thị summary

## 🔧 Setup

### 1. Cấp quyền thực thi cho scripts

```bash
cd deployment/scripts
chmod +x *.sh
```

### 2. Cấu hình environment

Đảm bảo file `deployment/.env.production` đã được tạo và cấu hình:

```bash
cd deployment
cp env.example .env.production
# Chỉnh sửa .env.production với các giá trị production
```

## 📝 Workflow

### Normal Deployment

```bash
# 1. Health check trước khi deploy
./health-check.sh

# 2. Tạo backup thủ công (optional)
./backup.sh

# 3. Deploy
./deploy.sh

# 4. Verify
./health-check.sh
```

### Rollback

```bash
# 1. List backups
ls -lt ../backups/

# 2. Rollback
./rollback.sh [backup_name]

# 3. Verify
./health-check.sh
```

## ⚠️ Lưu ý

1. **Backup tự động**: Script `deploy.sh` tự động tạo backup trước khi deploy
2. **Health checks**: Tất cả scripts đều có health checks để đảm bảo services hoạt động
3. **Error handling**: Scripts sẽ exit với error code nếu có vấn đề
4. **Logs**: Kiểm tra logs nếu có lỗi: `docker-compose -f ../docker-compose.prod.yml logs`

## 🆘 Troubleshooting

### Script không chạy được

```bash
# Kiểm tra quyền thực thi
ls -l *.sh

# Cấp quyền lại
chmod +x *.sh
```

### Health check fails

```bash
# Kiểm tra logs
docker-compose -f ../docker-compose.prod.yml logs

# Kiểm tra container status
docker-compose -f ../docker-compose.prod.yml ps
```

### Rollback fails

```bash
# Kiểm tra backup có tồn tại
ls -l ../backups/

# Kiểm tra backup contents
cat ../backups/[backup_name]/backup-info.txt
```

