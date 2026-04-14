#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

$taskName = "VacancyBot24x7"
$startupShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\VacancyBot24x7.cmd"

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed scheduled task: $taskName"
}

if (Test-Path $startupShortcut) {
    Remove-Item -LiteralPath $startupShortcut -Force
    Write-Host "Removed startup shortcut: $startupShortcut"
}
