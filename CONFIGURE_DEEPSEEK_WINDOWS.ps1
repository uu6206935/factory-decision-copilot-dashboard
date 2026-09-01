Set-Location $PSScriptRoot
Write-Host ""
Write-Host "Factory Decision Copilot - DeepSeek V4 Flash setup" -ForegroundColor Cyan
Write-Host "The API key is stored only in .env.local on this PC." -ForegroundColor Yellow
Write-Host "Never share or commit .env.local." -ForegroundColor Yellow
Write-Host ""
$secure = Read-Host "Paste DEEPSEEK_API_KEY" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
if ([string]::IsNullOrWhiteSpace($key)) {
    Write-Host "No key entered. DeepSeek remains OFF; local analysis still works." -ForegroundColor Yellow
    exit 0
}
Write-Host ""
Write-Host "Data policy:" -ForegroundColor Cyan
Write-Host "  Metadata-only is the safe default: no sample values, document text, or structured evidence are sent." -ForegroundColor Gray
Write-Host "  Full mode should be used ONLY for dummy/public data or when your organization explicitly approves external DeepSeek API use." -ForegroundColor Yellow
$answer = Read-Host "Type FULL to allow full data for this local demo, otherwise press Enter for metadata-only"
$full = $answer.Trim().ToUpper() -eq "FULL"
if ($full) {
    $sample="true"; $docs="true"; $structured="true"
    Write-Host "FULL mode selected. Use only with dummy/public/explicitly approved data." -ForegroundColor Yellow
} else {
    $sample="false"; $docs="false"; $structured="false"
    Write-Host "Metadata-only mode selected." -ForegroundColor Green
}
@"
# Local secret file. Never commit/share this file.
DEEPSEEK_ENABLED=true
DEEPSEEK_API_KEY=$key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_SEND_SAMPLE_VALUES=$sample
DEEPSEEK_SEND_DOCUMENT_TEXT=$docs
DEEPSEEK_SEND_STRUCTURED_EVIDENCE=$structured
DEEPSEEK_QUERY_REWRITE=true
DEEPSEEK_JOIN_REASONING=true
DEEPSEEK_SCHEMA_REASONING=true
"@ | Set-Content -Path ".env.local" -Encoding UTF8
Write-Host "Configured model: deepseek-v4-flash" -ForegroundColor Green
