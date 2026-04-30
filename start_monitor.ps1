param(
    [ValidateSet("live", "paper")]
    [string]$Mode = "live",
    # Include at least one stock and one crypto symbol when validating mixed-symbol monitor behavior.
    [string]$Symbols = "SPY,BTC/USD,ETH/USD,SOL/USD,DOGE/USD",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8080,
    [switch]$Tray
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$venvActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvActivate)) {
    throw "Virtual environment activation script not found at $venvActivate"
}

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at $pythonExe"
}

. $venvActivate

$Host.UI.RawUI.WindowTitle = "AI Trading Bot - Monitor"

$env:SYMBOLS = $Symbols
$env:CRYPTO_SYMBOLS = ""
$env:ALPACA_CRYPTO_UNIVERSE = "none"
$env:RUNTIME_REGISTRY_PATH = "logs/runtime/runtime_registry.json"

if ($Mode -eq "live") {
    $env:PAPER_TRADING = "0"
    $env:BASE_URL = "https://api.alpaca.markets"
    $env:LIVE_TRADING_ENABLED = "1"
    $env:ALLOW_LIVE_TRADING = "1"
    if (-not $env:LIVE_CONFIRMATION_TOKEN) {
        $env:LIVE_CONFIRMATION_TOKEN = "CONFIRM"
    }
    if (-not $env:LIVE_RUN_CONFIRMATION) {
        $env:LIVE_RUN_CONFIRMATION = $env:LIVE_CONFIRMATION_TOKEN
    }
} else {
    $env:PAPER_TRADING = "1"
    $env:BASE_URL = "https://paper-api.alpaca.markets"
    $env:LIVE_TRADING_ENABLED = "0"
    $env:ALLOW_LIVE_TRADING = "0"
    $env:LIVE_RUN_CONFIRMATION = ""
}

$args = @("-m", "tradingbot.app.tray", "--host", $HostAddress, "--port", $Port.ToString())
if (-not $Tray) {
    $args = @("-m", "tradingbot.app.tray", "--no-tray", "--host", $HostAddress, "--port", $Port.ToString())
}

& $pythonExe @args
