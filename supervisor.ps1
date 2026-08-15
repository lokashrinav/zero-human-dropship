# Zero Human Dropship — external supervisor. THE engine of full autonomy.
# No agent session is the engine: this dumb loop revives the backend and tunnel,
# and re-prompts a FRESH headless Claude CEO cycle forever. Sessions die; this doesn't.
# Start: start_autonomous.bat   (or: powershell -ExecutionPolicy Bypass -File supervisor.ps1)

$ErrorActionPreference = "Continue"
$Repo = $PSScriptRoot
$Backend = Join-Path $Repo "agent_backend"
$TunnelUrlFile = Join-Path $Backend "tunnel_url.txt"
$TunnelLog = Join-Path $Backend "tunnel.log"
$CycleMinutes = 15
$CycleTimeoutMinutes = 12

# Quote-proof: the real instructions live in AUTONOMY_CYCLE.md (repo root).
$CyclePrompt = "Read AUTONOMY_CYCLE.md in the repo root and execute exactly one cycle per its instructions."

function Log-Supervisor([string]$msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] SUPERVISOR: $msg"
    try {
        Push-Location $Backend
        $env:PYTHONIOENCODING = "utf-8"
        python log_decision.py Supervisor $msg 2>$null | Out-Null
        Pop-Location
    } catch { try { Pop-Location } catch {} }
}

function Ensure-Backend {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
        if ($r.StatusCode -eq 200) { return }
    } catch {}
    Log-Supervisor "backend dead - restarting uvicorn"
    try {
        Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    } catch {}
    $env:PYTHONIOENCODING = "utf-8"
    Start-Process -WindowStyle Hidden -WorkingDirectory $Backend python -ArgumentList "-m", "uvicorn", "main:app", "--port", "8000"
    Start-Sleep -Seconds 6
}

function Ensure-Tunnel {
    $url = ""
    if (Test-Path $TunnelUrlFile) { $url = (Get-Content $TunnelUrlFile -Raw).Trim() }
    if ($url) {
        try {
            $r = Invoke-WebRequest -Uri "$url/health" -TimeoutSec 12 -UseBasicParsing
            if ($r.StatusCode -eq 200) { return }
        } catch {}
    }
    Log-Supervisor "tunnel dead - relaunching cloudflared"
    try { Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force } catch {}
    if (Test-Path $TunnelLog) { Remove-Item $TunnelLog -Force -ErrorAction SilentlyContinue }
    $cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
    if (-not (Test-Path $cf)) { $cf = "cloudflared" }
    Start-Process -WindowStyle Hidden -RedirectStandardError $TunnelLog $cf -ArgumentList "tunnel", "--url", "http://localhost:8000"
    # quick tunnels print the URL to stderr within ~10s
    $newUrl = ""
    foreach ($i in 1..12) {
        Start-Sleep -Seconds 3
        if (Test-Path $TunnelLog) {
            $m = Select-String -Path $TunnelLog -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -AllMatches -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($m) { $newUrl = $m.Matches[0].Value; break }
        }
    }
    if ($newUrl) {
        Set-Content -Path $TunnelUrlFile -Value $newUrl
        Log-Supervisor "tunnel rotated: $newUrl"
        try {
            Push-Location $Backend
            python -m tools.escalation_tools raise Supervisor "public tunnel URL changed to $newUrl" "update CEO_DECISIONS_URL on the dashboard Vercel env to $newUrl/api/decisions and redeploy" 2>$null | Out-Null
            Pop-Location
        } catch { try { Pop-Location } catch {} }
    } else {
        Log-Supervisor "tunnel relaunch failed to yield a URL - will retry next iteration"
    }
}

function Ensure-FulfillmentDaemon {
    $running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*fulfillment*pipeline.py*daemon*" }
    if ($running) { return }
    Log-Supervisor "fulfillment daemon dead - restarting"
    $env:PYTHONIOENCODING = "utf-8"
    Start-Process -WindowStyle Hidden -WorkingDirectory $Repo python -ArgumentList "fulfillment\pipeline.py", "daemon"
}

function Run-OpsCycle {
    Log-Supervisor "starting headless Ops cycle"
    try {
        $prompt = "Read OPS_CYCLE.md in the repo root and execute exactly one cycle per its instructions."
        $p = Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory $Repo claude -ArgumentList "-p", "`"$prompt`"", "--dangerously-skip-permissions"
        if (-not ($p.WaitForExit($CycleTimeoutMinutes * 60 * 1000))) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            Log-Supervisor "ops cycle timed out - killed, continuing"
        } else {
            Log-Supervisor "ops cycle finished (exit $($p.ExitCode))"
        }
    } catch {
        Log-Supervisor "ops cycle launch failed: $($_.Exception.Message)"
    }
}

function Run-CeoCycle {
    Log-Supervisor "starting headless CEO cycle"
    try {
        # Start-Process joins -ArgumentList with spaces WITHOUT quoting, so a multi-word
        # prompt reaches claude as separate argv words and -p sees only "Read".
        # Embed explicit quotes around the prompt.
        $p = Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory $Repo claude -ArgumentList "-p", "`"$CyclePrompt`"", "--dangerously-skip-permissions"
        if (-not ($p.WaitForExit($CycleTimeoutMinutes * 60 * 1000))) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            Log-Supervisor "cycle timed out after $CycleTimeoutMinutes min - killed, continuing"
        } else {
            Log-Supervisor "cycle finished (exit $($p.ExitCode))"
        }
    } catch {
        Log-Supervisor "cycle launch failed: $($_.Exception.Message)"
    }
}

Log-Supervisor "SUPERVISOR ONLINE - cycle every $CycleMinutes min. The business does not stop."
while ($true) {
    try { Ensure-Backend } catch { Log-Supervisor "Ensure-Backend error: $($_.Exception.Message)" }
    try { Ensure-Tunnel } catch { Log-Supervisor "Ensure-Tunnel error: $($_.Exception.Message)" }
    try { Ensure-FulfillmentDaemon } catch { Log-Supervisor "Ensure-FulfillmentDaemon error: $($_.Exception.Message)" }
    try { Run-CeoCycle } catch { Log-Supervisor "Run-CeoCycle error: $($_.Exception.Message)" }
    try { Run-OpsCycle } catch { Log-Supervisor "Run-OpsCycle error: $($_.Exception.Message)" }
    Start-Sleep -Seconds ($CycleMinutes * 60)
}
