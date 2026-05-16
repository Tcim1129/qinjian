$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$srcRoot = Join-Path $projectRoot 'src'

$fileEntries = @(
  'App.vue',
  'App.uvue',
  'main.js',
  'main.uts',
  'pages.json',
  'manifest.json',
  'uni.scss'
)

$dirEntries = @(
  'pages',
  'components',
  'static',
  'store',
  'utils'
)

New-Item -ItemType Directory -Force -Path $srcRoot | Out-Null

foreach ($name in $fileEntries + $dirEntries) {
  $source = Join-Path $projectRoot $name
  $target = Join-Path $srcRoot $name

  if (-not (Test-Path $source)) {
    continue
  }

  if (Test-Path $target) {
    Remove-Item $target -Recurse -Force
  }

  Copy-Item $source $target -Recurse -Force
}

Write-Output "synced uni src mirror to $srcRoot"
