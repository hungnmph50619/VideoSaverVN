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
$linkPath = Join-Path $desktop "VideoSaver VN.lnk"
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($linkPath)
$link.TargetPath = $env:ComSpec
$link.Arguments = '/d /c ""' + $launcher + '""'
$link.WorkingDirectory = $repo
$link.IconLocation = "$env:SystemRoot\System32\shell32.dll,116"
$link.Description = "Open VideoSaver VN in the browser"
$link.WindowStyle = 1
$link.Save()
Write-Host "Shortcut created: $linkPath" -ForegroundColor Green
Write-Host "Double-click VideoSaver VN on the Desktop to start the app."
