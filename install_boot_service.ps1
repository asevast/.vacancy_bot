#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

$taskName = "VacancyBot24x7"
$projectDir = "C:\Users\Flesheater\.vacancy_bot"
$bootstrapScript = Join-Path $projectDir "run_bot_service.ps1"
$startupShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\VacancyBot24x7.cmd"

if (-not (Test-Path $bootstrapScript)) {
    throw "Bootstrap script not found: $bootstrapScript"
}

if (Test-Path $startupShortcut) {
    Remove-Item -LiteralPath $startupShortcut -Force
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$bootstrapScript`"" -WorkingDirectory $projectDir

$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

$definition = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings

Register-ScheduledTask -TaskName $taskName -InputObject $definition -Force | Out-Null

Write-Host "Installed machine-level boot task: $taskName"
Write-Host "The task runs at system startup as SYSTEM and starts the Docker stack."
