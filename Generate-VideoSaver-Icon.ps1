# Render an original gradient VideoSaver VN launcher icon with System.Drawing.
# Creates a standards-compliant multi-resolution PNG-compressed Windows ICO file.
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$iconFile = Join-Path $PSScriptRoot "VideoSaverVN.ico"
function New-IconPng([int]$size) {
    $bitmap = [System.Drawing.Bitmap]::new($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bitmap)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $scale = $size / 256.0
    $g.ScaleTransform([single]$scale, [single]$scale)
    $rect = [System.Drawing.Rectangle]::new(12, 12, 232, 232)
    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $r = 54
    $path.AddArc($rect.Left, $rect.Top, $r, $r, 180, 90)
    $path.AddArc($rect.Right-$r, $rect.Top, $r, $r, 270, 90)
    $path.AddArc($rect.Right-$r, $rect.Bottom-$r, $r, $r, 0, 90)
    $path.AddArc($rect.Left, $rect.Bottom-$r, $r, $r, 90, 90)
    $path.CloseFigure()
    $brush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
        [System.Drawing.Point]::new(15,16),
        [System.Drawing.Point]::new(235,250),
        [System.Drawing.Color]::FromArgb(255, 33, 103, 247),
        [System.Drawing.Color]::FromArgb(255, 107, 41, 201))
    $g.FillPath($brush, $path)
    $edge = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(140, 202, 225, 255), 3)
    $g.DrawPath($edge, $path)
    # Subtle dark plate behind the media symbol.
    $plate = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(74, 9, 18, 58))
    $g.FillEllipse($plate, 47, 45, 164, 164)
    # White triangular Play mark.
    $triangle = [System.Drawing.Point[]]@(
        ([System.Drawing.Point]::new(91, 73)),
        ([System.Drawing.Point]::new(91, 173)),
        ([System.Drawing.Point]::new(174, 123)))
    $white = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 255, 255, 255))
    $g.FillPolygon($white, $triangle)
    # Cyan download arrow and tray.
    $cyan = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 60, 230, 234))
    $g.FillRectangle($cyan, 171, 148, 16, 46)
    $down = [System.Drawing.Point[]]@(
        ([System.Drawing.Point]::new(157, 185)),
        ([System.Drawing.Point]::new(201, 185)),
        ([System.Drawing.Point]::new(179, 209)))
    $g.FillPolygon($cyan, $down)
    $pen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(255, 60, 230, 234), 10)
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $g.DrawLine($pen, 144, 214, 144, 225)
    $g.DrawLine($pen, 144, 225, 211, 225)
    $g.DrawLine($pen, 211, 225, 211, 214)
    $stream = [System.IO.MemoryStream]::new()
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
$writer = [System.IO.BinaryWriter]::new($file)
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
