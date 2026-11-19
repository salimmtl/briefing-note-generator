<#
.SYNOPSIS
  Exports a solution as managed + unmanaged, unpacks the unmanaged source, generates the deployment
  settings template, and prints an inventory so you can check that nothing is missing.
.EXAMPLE
  .\export_solution.ps1 -SolutionName ContosoRequests
  .\export_solution.ps1 -SolutionName ContosoRequests -EnvironmentUrl https://contoso.crm.dynamics.com -RepoRoot C:\demos\contoso
#>
param(
    [Parameter(Mandatory = $true)][string]$SolutionName,
    [string]$EnvironmentUrl = "",
    [string]$RepoRoot = (Get-Location).Path,
    [string]$PackagesDir = "packages",
    [string]$SourceDir = "solution"
)

$ErrorActionPreference = "Stop"
$env:TERM = "dumb"

function Invoke-Pac {
    $envArgs = if ($EnvironmentUrl) { @("--environment", $EnvironmentUrl) } else { @() }
    & pac @args @envArgs
    if ($LASTEXITCODE -ne 0) { throw "pac $($args -join ' ') failed with exit code $LASTEXITCODE" }
}

$pkg = Join-Path $RepoRoot $PackagesDir
$src = Join-Path $RepoRoot "$SourceDir\$SolutionName"
New-Item -ItemType Directory -Force $pkg | Out-Null
$unmanaged = Join-Path $pkg "$SolutionName.zip"
$managed = Join-Path $pkg "${SolutionName}_managed.zip"

Write-Host "Target: $(if ($EnvironmentUrl) { $EnvironmentUrl } else { 'active pac profile' })" -ForegroundColor Cyan
pac org who | Select-String "Org URL|Friendly Name" | ForEach-Object { Write-Host "  $($_.Line.Trim())" }

Invoke-Pac solution publish
Invoke-Pac solution export --name $SolutionName --path $unmanaged --managed false --overwrite
Invoke-Pac solution export --name $SolutionName --path $managed --managed true --overwrite
& pac solution unpack --zipfile $unmanaged --folder $src --packagetype Unmanaged --allowDelete true
if ($LASTEXITCODE -ne 0) { throw "pac solution unpack failed" }
& pac solution create-settings --solution-zip $managed --settings-file (Join-Path $pkg "deploymentSettings.example.json")
if ($LASTEXITCODE -ne 0) { throw "pac solution create-settings failed" }

# ---- Inventory: what the package contains
$settings = Get-Content (Join-Path $pkg "deploymentSettings.example.json") -Raw | ConvertFrom-Json
$folders = Get-ChildItem $src -Directory | Select-Object -ExpandProperty Name
$checks = [ordered]@{
    "Tables (Entities)"              = "Entities"
    "Global choices (OptionSets)"    = "OptionSets"
    "Security roles"                 = "Roles"
    "Model-driven apps"              = "AppModules"
    "Site maps"                      = "AppModuleSiteMaps"
    "Dashboards"                     = "Dashboards"
    "Canvas / code apps"             = "CanvasApps"
    "Cloud flows"                    = "Workflows"
    "Copilot Studio agents"          = "bots"
    "Agent components"               = "botcomponents"
    "Business skills"                = "skills"
    "Environment variables"          = "environmentvariabledefinitions"
    "Web resources"                  = "WebResources"
}
Write-Host ""
Write-Host "Package inventory ($SolutionName)" -ForegroundColor Cyan
foreach ($k in $checks.Keys) {
    $present = $folders -contains $checks[$k]
    $n = if ($present) { (Get-ChildItem (Join-Path $src $checks[$k]) -Force | Measure-Object).Count } else { 0 }
    Write-Host ("  {0,-30} {1}" -f $k, $(if ($present) { "$n item(s)" } else { "-" }))
}
Write-Host ("  {0,-30} {1}" -f "Connection references", @($settings.ConnectionReferences).Count)
foreach ($cr in @($settings.ConnectionReferences)) { Write-Host "      $($cr.LogicalName)  ($($cr.ConnectorId -replace '.*/apis/',''))" }
Write-Host ("  {0,-30} {1}" -f "Environment variables (settings)", @($settings.EnvironmentVariables).Count)
Write-Host ""
Get-ChildItem $pkg -Filter "*.zip" | ForEach-Object { Write-Host ("  {0,-45} {1,10:N0} bytes" -f $_.Name, $_.Length) }
Write-Host ""
Write-Host "Check: does every component you built appear above? Every agent tool's connection reference must be listed." -ForegroundColor Yellow
