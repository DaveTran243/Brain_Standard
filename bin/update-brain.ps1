<#
.SYNOPSIS
    Update a brain from Brain_Standard, check it, and connect Claude Desktop and Claude Code, in one command.

.DESCRIPTION
    A thin wrapper: the work is done by update_brain.py beside this file (standard library Python, tested in CI).
    It replaces only the standard's paths (docs, tools, bin, tests, integrations, CHANGELOG.md), never vault/ or
    brain.toml, and with -Tests rolls everything back if the standard's tests fail on this machine.

.EXAMPLE
    .\bin\update-brain.ps1 -Brain D:\Brain_dave\Coding\second-brain -DryRun
    .\bin\update-brain.ps1 -Brain D:\Brain_dave\Coding\second-brain -Tests -Commit -Mcp claude-desktop,claude-code
    .\bin\update-brain.ps1 -Brain D:\Brain_dave\Coding\second-brain -RegisterTask -Day Sunday -At 20:00
#>
[CmdletBinding()]
param(
    [string]$Brain = (Get-Location).Path,
    [string]$Standard = "",
    [switch]$Commit,
    [switch]$Tests,
    [switch]$UpdateAgents,
    [string[]]$Mcp = @(),
    [switch]$McpWrite,
    [switch]$Force,
    [switch]$DryRun,
    [switch]$RegisterTask,
    [ValidateSet("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
    [string]$Day = "Sunday",
    [string]$At = "20:00",
    [switch]$UnregisterTask
)

$ErrorActionPreference = "Stop"
$TaskName = "Brain_Standard update"
$Script = Join-Path $PSScriptRoot "update_brain.py"

function Find-Python {
    foreach ($candidate in @("py -3", "python", "python3")) {
        $parts = $candidate -split " "
        $exe = Get-Command $parts[0] -ErrorAction SilentlyContinue
        if ($null -ne $exe) {
            $rest = @($parts | Select-Object -Skip 1)
            $ok = & $exe.Source @rest -c "import sys; print(sys.version_info >= (3, 11))" 2>$null
            if ("$ok".Trim() -eq "True") { return @($exe.Source) + $rest }
        }
    }
    throw "Python 3.11 or later was not found. Install it from python.org (tick 'Add to PATH'), then run this again."
}

if ($UnregisterTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed the scheduled task '$TaskName' (if it existed)."
    exit 0
}

$Brain = (Resolve-Path $Brain).Path

if ($RegisterTask) {
    # The weekly run uses the brain's own copy of this script, so it keeps itself up to date.
    $self = Join-Path $Brain "bin\update-brain.ps1"
    if (-not (Test-Path $self)) { $self = $PSCommandPath }
    $log = Join-Path $Brain ".brain\update.log"
    # -Command, not -File: the log redirection must be read by PowerShell, not passed to the script as an argument.
    $command = "& '$self' -Brain '$Brain' -Tests -Commit *>> '$log'"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$command`""
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $At
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Description "Update $Brain from Brain_Standard, run its tests, commit. Rolls back if tests fail." -Force | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Brain ".brain") | Out-Null
    Write-Host "Scheduled '$TaskName': every $Day at $At. Log: $log"
    Write-Host "Remove it with: .\bin\update-brain.ps1 -UnregisterTask"
    exit 0
}

$py = Find-Python
$pyExe = $py[0]
$pyArgs = @($py | Select-Object -Skip 1)
$argsList = $pyArgs + @($Script, "--brain", $Brain)
if ($Standard) { $argsList += @("--standard", $Standard) }
if ($Commit) { $argsList += "--commit" }
if ($Tests) { $argsList += "--tests" }
if ($UpdateAgents) { $argsList += "--update-agents" }
if ($Mcp.Count -gt 0) { $argsList += @("--mcp", ($Mcp -join ",")) }
if ($McpWrite) { $argsList += "--mcp-write" }
if ($Force) { $argsList += "--force" }
if ($DryRun) { $argsList += "--dry-run" }

$env:PYTHONUTF8 = "1"
& $pyExe @argsList
exit $LASTEXITCODE
