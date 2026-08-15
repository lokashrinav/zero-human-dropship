$ErrorActionPreference = "Stop"

$envPath = Join-Path $PSScriptRoot ".env"
$secureKey = Read-Host "Paste your NEW Stripe live key" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}

if ($key -notmatch '^(sk|rk)_live_[A-Za-z0-9]+$') {
    throw "That is not a Stripe live secret or restricted key. Expected sk_live_... or rk_live_..."
}

$lines = if (Test-Path -LiteralPath $envPath) {
    @(Get-Content -LiteralPath $envPath)
} else {
    @()
}

$replaced = $false
$updated = foreach ($line in $lines) {
    if ($line -match '^\s*STRIPE_SECRET_KEY\s*=') {
        $replaced = $true
        "STRIPE_SECRET_KEY=$key"
    } else {
        $line
    }
}

if (-not $replaced) {
    $updated = @($updated) + "STRIPE_SECRET_KEY=$key"
}

[IO.File]::WriteAllLines(
    $envPath,
    [string[]]$updated,
    [Text.UTF8Encoding]::new($false)
)

$key = $null
$secureKey.Dispose()
Write-Host "Saved a live Stripe key to $envPath" -ForegroundColor Green
