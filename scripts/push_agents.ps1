<#
.SYNOPSIS
  Regenerate and push the two agents (Briefing Note Writer, Briefing Assistant), then optionally publish them.
.DESCRIPTION
  pac copilot pull sometimes crashes with System.FormatException. With -Fresh, each workspace is re-synced from a
  fresh 'pac copilot clone' (settings + .mcs state) before the generated YAML is re-applied and pushed.
.EXAMPLE
  .\scripts\push_agents.ps1 -Publish
#>
param([switch]$Fresh, [switch]$Publish, [switch]$FirstPush, [string[]]$Only = @("writer", "assistant"))

$ErrorActionPreference = "Stop"
$env:TERM = "dumb"
$root = Split-Path $PSScriptRoot -Parent
$envUrl = (Get-Content (Join-Path $root ".env") | Where-Object { $_ -match "^DATAVERSE_URL=" }) -replace "^DATAVERSE_URL=", ""
$agents = @{ writer = "brn_BriefingNoteWriter"; assistant = "brn_BriefingAssistant" }

if ($Fresh) {
    foreach ($key in $Only) {
        $tmp = Join-Path $env:TEMP "brnclone-$key"
        if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
        New-Item -ItemType Directory $tmp | Out-Null
        pac copilot clone --bot $agents[$key] --output-dir $tmp --environment $envUrl | Out-Null
        $clone = Get-ChildItem $tmp -Directory | Select-Object -First 1
        $dest = Join-Path $root "agent\$key"
        Copy-Item (Join-Path $clone.FullName "settings.mcs.yml") $dest -Force
        Remove-Item (Join-Path $dest ".mcs") -Recurse -Force -ErrorAction SilentlyContinue
        Copy-Item (Join-Path $clone.FullName ".mcs") $dest -Recurse -Force
        Write-Host "[OK]   re-synced $key from a fresh clone"
    }
}

if ($FirstPush) { python (Join-Path $root "scripts\build_agents.py") --first-push } else { python (Join-Path $root "scripts\build_agents.py") }
if ($LASTEXITCODE) { throw "build_agents.py failed" }

foreach ($key in $Only) {
    Write-Host "=== push $key"
    pac copilot push --project-dir (Join-Path $root "agent\$key")
    if ($LASTEXITCODE) { throw "push failed for $key" }
    if ($Publish) {
        pac copilot publish --bot $agents[$key] --environment $envUrl
        if ($LASTEXITCODE) { throw "publish failed for $key" }
    }
}
