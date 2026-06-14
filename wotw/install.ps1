# Installs Wok of the Warrior into the user's apps folder and adds a Start Menu
# shortcut, so it shows up when you search "Wok of the Warrior" in Windows.
# Run from this folder:  powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"

$src = Join-Path $PSScriptRoot "dist\WokOfTheWarrior.exe"
if (-not (Test-Path $src)) {
    throw "dist\WokOfTheWarrior.exe not found. Build it first:  pyinstaller wok.spec"
}

# 1) Copy the exe to a permanent per-user install location (no admin needed).
$installDir = Join-Path $env:LOCALAPPDATA "Programs\Wok of the Warrior"
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
$exe = Join-Path $installDir "Wok of the Warrior.exe"
Copy-Item $src $exe -Force

# 2) Create a Start Menu shortcut named "Wok of the Warrior".
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$lnk = Join-Path $startMenu "Wok of the Warrior.lnk"
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnk)
$sc.TargetPath = $exe
$sc.WorkingDirectory = $installDir
$sc.IconLocation = "$exe,0"
$sc.Description = "Wok of the Warrior"
$sc.Save()

# Nudge Windows to refresh its icon cache so the new logo shows immediately.
try { & ie4uinit.exe -show } catch {}

Write-Output "Installed: $exe"
Write-Output "Start Menu shortcut: $lnk"
Write-Output "Search the Start menu for 'Wok of the Warrior' to launch it."

