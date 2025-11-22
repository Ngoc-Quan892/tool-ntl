<#
.SYNOPSIS
  Hỗ trợ thêm remote và push branch hiện tại lên remote (GitHub/GitLab).

.DESCRIPTION
  Script tương tác cho phép bạn nhập URL remote (HTTPS hoặc SSH), tự động thêm
  remote `origin` (hoặc ghi đè nếu bạn đồng ý) và push branch hiện tại.
  Nếu bạn chọn SSH và chưa có SSH key, script sẽ đề xuất tạo key mới.

.USAGE
  PowerShell (chạy trong thư mục repo):
    .\scripts\push_remote.ps1
  Hoặc truyền URL:
    .\scripts\push_remote.ps1 -RemoteUrl "git@github.com:you/your-repo.git"

  Lưu ý: Script chạy cục bộ và sẽ yêu cầu bạn cung cấp xác thực (PAT/password hoặc
  nhập passphrase SSH) khi Git yêu cầu. KHÔNG dán token vào chat.
#>

param(
    [string]$RemoteUrl
)

function Write-ErrorExit($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

# Ensure git exists
try {
    git --version | Out-Null
} catch {
    Write-ErrorExit 'Git không được tìm thấy trong PATH. Vui lòng cài Git trước khi chạy script.'
}

Push-Location (Get-Location)
try {
    $branch = git rev-parse --abbrev-ref HEAD 2>$null
} catch {
    Write-ErrorExit 'Không phải một git repository hoặc có lỗi khi đọc branch hiện tại.'
}

if (-not $branch) {
    Write-ErrorExit 'Không xác định được branch hiện tại.'
}

Write-Host "Branch hiện tại: $branch" -ForegroundColor Cyan

if (-not $RemoteUrl) {
    $RemoteUrl = Read-Host 'Nhập remote URL (HTTPS hoặc SSH). Ví dụ: https://github.com/you/repo.git hoặc git@github.com:you/repo.git'
}

if (-not $RemoteUrl) {
    Write-ErrorExit 'Bạn phải cung cấp một remote URL để tiếp tục.'
}

# Check if origin exists
$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Remote 'origin' hiện tại: $existing" -ForegroundColor Yellow
    $ans = Read-Host 'Bạn muốn ghi đè remote origin bằng URL mới? (y/n)'
    if ($ans -ne 'y' -and $ans -ne 'Y') {
        Write-Host 'Không ghi đè remote. Sử dụng tên remote tạm: temp-remote' -ForegroundColor Yellow
        $remoteName = 'temp-remote'
        git remote remove $remoteName 2>$null | Out-Null
        git remote add $remoteName $RemoteUrl
    } else {
        git remote remove origin
        git remote add origin $RemoteUrl
        $remoteName = 'origin'
    }
} else {
    git remote add origin $RemoteUrl
    $remoteName = 'origin'
}

Write-Host "Đã thêm remote '$remoteName' -> $RemoteUrl" -ForegroundColor Green

# If SSH URL and no key, offer to create one
if ($RemoteUrl -match '^git@' -or $RemoteUrl -match '^ssh://') {
    $sshPub = Join-Path $env:USERPROFILE '.ssh\id_ed25519.pub'
    if (-not (Test-Path $sshPub)) {
        $create = Read-Host 'Không tìm thấy SSH public key (~/.ssh/id_ed25519.pub). Tạo mới? (y/n)'
        if ($create -eq 'y' -or $create -eq 'Y') {
            Write-Host 'Tạo SSH key (ed25519). Nếu script hỏi passphrase, bạn có thể để trống.'
            ssh-keygen -t ed25519 -C "$(whoami)@$(hostname)" -f $env:USERPROFILE\.ssh\id_ed25519
            Write-Host "SSH public key:`n" -NoNewline
            Get-Content $sshPub
            Write-Host "`nCopy key trên và dán vào phần SSH keys trên Git hosting (ví dụ: GitHub)." -ForegroundColor Yellow
            Read-Host 'Nhấn Enter khi bạn đã dán key vào trang web của remote và key đã sẵn sàng'
        }
    }
}

Write-Host "Bắt đầu push branch $branch lên remote $remoteName..." -ForegroundColor Cyan

try {
    git push -u $remoteName $branch
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Push thành công lên $remoteName/$branch" -ForegroundColor Green
    } else {
        Write-Host "Push thất bại. Mã lỗi: $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host "Lỗi khi push: $_" -ForegroundColor Red
    exit 1
}

Pop-Location

Write-Host 'Hoàn tất. Mở GitHub/Git hosting để kiểm tra PR/Actions.' -ForegroundColor Green
