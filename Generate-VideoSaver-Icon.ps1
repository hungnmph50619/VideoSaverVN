# Render an original gradient VideoSaver VN launcher icon with System.Drawing.
# Creates a standards-compliant multi-resolution PNG-compressed Windows ICO file.
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$iconFile = Join-Path $PSScriptRoot "VideoSaverVN.ico"
function New-IconPng([int]$size) {
    $bitmap = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bitmap)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $scale = $size / 256.0
    $g.ScaleTransform([single]$scale, [single]$scale)
    $rect = New-Object System.Drawing.Rectangle(12, 12, 232, 232)
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $r = 54
    $path.AddArc($rect.Left, $rect.Top, $r, $r, 180, 90)
    $path.AddArc($rect.Right-$r, $rect.Top, $r, $r, 270, 90)
    $path.AddArc($rect.Right-$r, $rect.Bottom-$r, $r, $r, 0, 90)
    $path.AddArc($rect.Left, $rect.Bottom-$r, $r, $r, 90, 90)
    $path.CloseFigure()
    $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        (New-Object System.Drawing.Point(15, 16)),
        (New-Object System.Drawing.Point(235, 250)),
        [System.Drawing.Color]::FromArgb(255, 33, 103, 247),
        [System.Drawing.Color]::FromArgb(255, 107, 41, 201))
    $g.FillPath($brush, $path)
    $edge = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(140, 202, 225, 255), 3)
    $g.DrawPath($edge, $path)
    # Subtle dark plate behind the media symbol.
    $plate = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(74, 9, 18, 58))
    $g.FillEllipse($plate, 47, 45, 164, 164)
    # White triangular Play mark.
    $triangle = [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(91, 73)),
        (New-Object System.Drawing.Point(91, 173)),
        (New-Object System.Drawing.Point(174, 123)))
    $white = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 255, 255))
    $g.FillPolygon($white, $triangle)
    # Cyan download arrow and tray.
    $cyan = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 60, 230, 234))
    $g.FillRectangle($cyan, 171, 148, 16, 46)
    $down = [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(157, 185)),
        (New-Object System.Drawing.Point(201, 185)),
        (New-Object System.Drawing.Point(179, 209)))
    $g.FillPolygon($cyan, $down)
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 60, 230, 234), 10)
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $g.DrawLine($pen, 144, 214, 144, 225)
    $g.DrawLine($pen, 144, 225, 211, 225)
    $g.DrawLine($pen, 211, 225, 211, 214)
    $stream = New-Object System.IO.MemoryStream
    $g.ResetTransform()
    $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
    $bytes = $stream.ToArray()
    $stream.Dispose(); $g.Dispose(); $bitmap.Dispose()
    $path.Dispose(); $brush.Dispose(); $edge.Dispose(); $plate.Dispose(); $white.Dispose(); $cyan.Dispose(); $pen.Dispose()
    return ,$bytes
}
$sizes = @(256, 64, 32, 16)
$images = @()
foreach ($size in $sizes) { $images += ,(New-IconPng $size) }
$file = [System.IO.File]::Create($iconFile)
$writer = New-Object System.IO.BinaryWriter($file)
try {
    $writer.Write([uint16]0)
    $writer.Write([uint16]1)
    $writer.Write([uint16]$sizes.Count)
    $offset = 6 + (16 * $sizes.Count)
    for ($i=0; $i -lt $sizes.Count; $i++) {
        $size = $sizes[$i]
        $writer.Write([byte]($size % 256))
        $writer.Write([byte]($size % 256))
        $writer.Write([byte]0)
        $writer.Write([byte]0)
        $writer.Write([uint16]1)
        $writer.Write([uint16]32)
        $writer.Write([uint32]$images[$i].Length)
        $writer.Write([uint32]$offset)
        $offset += $images[$i].Length
    }
    foreach ($image in $images) { $writer.Write([byte[]]$image) }
} finally {
    $writer.Dispose()
}
Write-Host "Icon created: $iconFile" -ForegroundColor Cyan
