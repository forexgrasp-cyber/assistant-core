<#
.SYNOPSIS
    Build + install the private shared-canonical-services wheel into this project.

.DESCRIPTION
    The shared library is NOT published to a public package index. It is
    distributed as a private wheel built from the canonical repo:

        C:\Users\IhorLeshchuk\PycharmProjects\shared-canonical-services

    This script:
      1. Builds the wheel from the canonical repo (version 2026.11.4).
      2. Copies it into this project's .\dist\ staging folder.
      3. Installs it into the active Python environment.

.PARAMETER CanonicalRepo
    Path to the shared-canonical-services repo. Defaults to the sibling folder.

.PARAMETER SkipBuild
    Use an already-built wheel from the canonical repo's .\dist folder.

.EXAMPLE
    .\install_shared_wheel.ps1
    .\install_shared_wheel.ps1 -SkipBuild
#>
[CmdletBinding()]
param(
    [string]$CanonicalRepo = "C:\Users\IhorLeshchuk\PycharmProjects\shared-canonical-services",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DistDir = Join-Path $ProjectRoot "dist"

Write-Host "[START] Installing shared-canonical-services into $ProjectRoot"

if (-not (Test-Path $CanonicalRepo)) {
    Write-Host "[STOP] Canonical repo not found: $CanonicalRepo"
    exit 1
}

# ── 1. Build the wheel ────────────────────────────────────────────────────
if (-not $SkipBuild) {
    Push-Location $CanonicalRepo
    try {
        Write-Host "[START] Building wheel from $CanonicalRepo"
        python -m pip install --upgrade pip build | Out-Host
        python -m build --wheel | Out-Host

        # Guard against the nested-repo pitfall: an empty wheel means the
        # build ran against a nested shared-canonical-services/shared-canonical-services.
        $wheels = Get-ChildItem -Path "dist" -Filter "shared_canonical_services-*.whl" |
                  Sort-Object LastWriteTime -Descending
        if (-not $wheels) {
            Write-Host "[STOP] No wheel produced in $CanonicalRepo\dist"
            exit 1
        }

        $wheel = $wheels[0]
        if ($wheel.Length -lt 100000) {
            Write-Host "[STOP] Wheel '$($wheel.Name)' is only $($wheel.Length) bytes - nested build pitfall?"
            exit 1
        }
        Write-Host "[OK] Built $($wheel.Name) ($([math]::Round($wheel.Length/1MB, 2)) MB)"
    }
    finally {
        Pop-Location
    }
} else {
    $wheels = Get-ChildItem -Path (Join-Path $CanonicalRepo "dist") -Filter "shared_canonical_services-*.whl" |
              Sort-Object LastWriteTime -Descending
    if (-not $wheels) {
        Write-Host "[STOP] No wheel found in $CanonicalRepo\dist"
        exit 1
    }
    $wheel = $wheels[0]
}

# ── 2. Stage the wheel for Docker ─────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
Copy-Item -Path $wheel.FullName -Destination $DistDir -Force
Write-Host "[OK] Staged $($wheel.Name) -> $DistDir"

# ── 3. Install into the active environment ────────────────────────────────
python -m pip install --upgrade --force-reinstall $wheel.FullName | Out-Host
Write-Host "[OK] Installed $wheel.Name"

# ── 4. Verify the canonical import surface ────────────────────────────────
$verify = @'
import shared
from shared.agent_runtime.capabilities import Capability, resolve_capability
from shared.agent_runtime.universal import AGENT_DEFINITIONS, create_agent
from shared.agent_runtime.spec import VERTICAL_SPECS
from shared.agent_apps.app_factory import create_vertical_app
from shared.platform.app_factory import create_unified_platform_app
print("[OK] shared imports resolve; agents =", sorted(AGENT_DEFINITIONS))
print("[OK] verticals =", sorted(VERTICAL_SPECS))
print("[OK] alias 'voice' ->", resolve_capability("voice").value)
'@
$verify | python -

Write-Host "[OK] Done. Run: uvicorn app.main:app --port 8000"
