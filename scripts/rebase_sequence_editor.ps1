Param([string]$todoFile)

# Replace the specific 'pick' line for the offending commit with 'edit'
$commit = '3b593e292ab7b1c38c4101f6ef82cf411603c3ee'
$pattern = "^pick $commit"
$replacement = "edit $commit"

(Get-Content -Raw -LiteralPath $todoFile) -replace $pattern, $replacement | Set-Content -LiteralPath $todoFile

Write-Output "Updated rebase todo to edit commit $commit"
