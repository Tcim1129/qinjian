param(
  [string]$out
)

Add-Type -AssemblyName System.Drawing

if (!(Test-Path $out)) {
  New-Item -ItemType Directory -Path $out | Out-Null
}

function New-Icon([string]$name,[string]$hex,[string]$type) {
  $bmp = New-Object System.Drawing.Bitmap 48,48
  $g=[System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode=[System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.Clear([System.Drawing.Color]::Transparent)
  $color=[System.Drawing.ColorTranslator]::FromHtml($hex)
  $brush=New-Object System.Drawing.SolidBrush($color)
  $path=New-Object System.Drawing.Drawing2D.GraphicsPath
  $rect=New-Object System.Drawing.RectangleF(4,4,40,40)
  $r=10
  $path.AddArc($rect.X,$rect.Y,$r,$r,180,90)
  $path.AddArc($rect.X+$rect.Width-$r,$rect.Y,$r,$r,270,90)
  $path.AddArc($rect.X+$rect.Width-$r,$rect.Y+$rect.Height-$r,$r,$r,0,90)
  $path.AddArc($rect.X,$rect.Y+$rect.Height-$r,$r,$r,90,90)
  $path.CloseFigure()
  $g.FillPath($brush,$path)
  $white=[System.Drawing.Color]::FromArgb(255,255,255,255)
  $pen=New-Object System.Drawing.Pen($white,2.5)
  $g.SmoothingMode=[System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

  switch ($type) {
    'home' {
      $roof = New-Object System.Drawing.PointF[] 6
      $roof[0] = New-Object System.Drawing.PointF(12,24)
      $roof[1] = New-Object System.Drawing.PointF(24,12)
      $roof[2] = New-Object System.Drawing.PointF(36,24)
      $roof[3] = New-Object System.Drawing.PointF(36,34)
      $roof[4] = New-Object System.Drawing.PointF(12,34)
      $roof[5] = New-Object System.Drawing.PointF(12,24)
      $g.DrawLines($pen,$roof)
    }
    'checkin' {
      $g.DrawLine($pen,14,26,22,34)
      $g.DrawLine($pen,22,34,34,18)
    }
    'discover' {
      $g.DrawEllipse($pen,14,14,20,20)
      $g.DrawLine($pen,24,24,32,20)
      $g.DrawLine($pen,24,24,20,32)
    }
    'report' {
      $g.DrawLine($pen,16,34,16,22)
      $g.DrawLine($pen,24,34,24,18)
      $g.DrawLine($pen,32,34,32,26)
      $g.DrawLine($pen,14,34,34,34)
    }
    'profile' {
      $g.DrawEllipse($pen,18,14,12,12)
      $g.DrawArc($pen,14,24,20,12,0,180)
    }
  }
  $bmp.Save((Join-Path $out ($name + '.png')),[System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose()
  $bmp.Dispose()
}

$inactive='#C8CDD5'
$active='#E06B5A'

New-Icon 'tab-home' $inactive 'home'
New-Icon 'tab-home-active' $active 'home'
New-Icon 'tab-checkin' $inactive 'checkin'
New-Icon 'tab-checkin-active' $active 'checkin'
New-Icon 'tab-discover' $inactive 'discover'
New-Icon 'tab-discover-active' $active 'discover'
New-Icon 'tab-report' $inactive 'report'
New-Icon 'tab-report-active' $active 'report'
New-Icon 'tab-profile' $inactive 'profile'
New-Icon 'tab-profile-active' $active 'profile'
