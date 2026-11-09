# Creates a Windows desktop shortcut. No admin rights required.
$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$launcher = Join-Path $repo "Start-VideoSaverVN.cmd"
if (!(Test-Path -LiteralPath $launcher)) {
    throw "Missing launcher: $launcher"
}
$desktop = [Environment]::GetFolderPath("DesktopDirectory")
if (!(Test-Path -LiteralPath $desktop)) {
    throw "Could not locate the Windows Desktop."
}
$iconBuilder = Join-Path $repo "Generate-VideoSaver-Icon.ps1"
if (!(Test-Path -LiteralPath $iconBuilder)) { throw "Missing icon generator." }
& $iconBuilder
$iconFile = Join-Path $repo "VideoSaverVN.ico"
if (!(Test-Path -LiteralPath $iconFile)) { throw "Could not create VideoSaverVN.ico." }
$linkPath = Join-Path $desktop "VideoSaver VN.lnk"
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($linkPath)
$link.TargetPath = $env:ComSpec
$link.Arguments = '/d /c ""' + $launcher + '""'
$link.WorkingDirectory = $repo
$link.IconLocation = "$iconFile,0"
$link.Description = "Open VideoSaver VN in the browser"
$link.WindowStyle = 1
$link.Save()
Write-Host "Custom VideoSaver icon installed: $iconFile" -ForegroundColor Cyan
Write-Host "Shortcut created: $linkPath" -ForegroundColor Green
Write-Host "Double-click VideoSaver VN on the Desktop to start the app."
