<#
.SYNOPSIS
  Tạo file replacements.txt chứa mapping để git-filter-repo thay thế secret.

.DESCRIPTION
  Script sẽ yêu cầu bạn dán secret (ví dụ Slack webhook URL) NHƯNG KHÔNG gửi secret
  ra ngoài. File `replacements.txt` sẽ được ghi vào thư mục gốc của repository.

.USAGE
  Chạy từ thư mục repo:
    .\scripts\cleanup\create_replacements.ps1

  Hoặc truyền tham số:
    .\scripts\cleanup\create_replacements.ps1 -OutFile "C:\temp\replacements.txt"
#>

param(
    [string]$OutFile = "$(Get-Location)\replacements.txt"
)

Write-Host "Tạo file replacements để dùng với git-filter-repo" -ForegroundColor Cyan
Write-Host "LƯU Ý: KHÔNG dán giá trị secret vào chat. Secret chỉ lưu cục bộ trên máy bạn." -ForegroundColor Yellow

$secret = Read-Host -Prompt 'Dán secret (ví dụ Slack webhook URL) và nhấn Enter'
if (-not $secret) {
    Write-Host 'Không có secret được nhập. Hủy.' -ForegroundColor Red
    exit 1
}

$replacement = Read-Host -Prompt 'Nhập chuỗi thay thế hiển thị (mặc định: [REDACTED_SLACK_WEBHOOK])'
if (-not $replacement) { $replacement = '[REDACTED_SLACK_WEBHOOK]' }

$line = "$secret==>$replacement"

Set-Content -Path $OutFile -Value $line -Encoding UTF8
Write-Host "Đã tạo file replacements tại: $OutFile" -ForegroundColor Green
Write-Host "Hãy kiểm tra file này (nội dung sẽ là một dòng: secret==>replacement)." -ForegroundColor Yellow
Write-Host "Tiếp theo chạy script remove_secret_full.ps1 để thực hiện rewrite và push." -ForegroundColor Cyan
