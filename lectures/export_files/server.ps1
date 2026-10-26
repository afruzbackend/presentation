# Elektron darslik - oflayn nusxani kompyuterning o'zida ochish (Python kerak emas).
# YouTube videolari sahifa "file://" dan ochilsa ijro etilmaydi, shuning uchun darslik
# http://localhost manzilida ochiladi - videolar darslikning ichida ko'rinadi.
# Ishga tushirish: "Ochish.bat" ni ikki marta bosing. Yopish: shu qora oynani yoping.

$root = [IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path)).TrimEnd('\') + '\'
$types = @{
  '.html' = 'text/html; charset=utf-8'; '.css' = 'text/css; charset=utf-8'; '.js' = 'text/javascript; charset=utf-8'
  '.json' = 'application/json'; '.txt' = 'text/plain; charset=utf-8'; '.svg' = 'image/svg+xml'
  '.png' = 'image/png'; '.jpg' = 'image/jpeg'; '.jpeg' = 'image/jpeg'; '.gif' = 'image/gif'; '.webp' = 'image/webp'
  '.ico' = 'image/x-icon'; '.pdf' = 'application/pdf'; '.mp4' = 'video/mp4'; '.webm' = 'video/webm'; '.mp3' = 'audio/mpeg'
  '.woff' = 'font/woff'; '.woff2' = 'font/woff2'
}

$listener = $null
for ($p = 8731; $p -lt 8800; $p++) {
  $l = New-Object System.Net.HttpListener
  $l.Prefixes.Add("http://localhost:$p/")
  try { $l.Start(); $listener = $l; $port = $p; break } catch { $l.Close() }
}
if (-not $listener) {
  Write-Host "Darslikni ochib bo'lmadi: bo'sh port topilmadi. Uning o'rniga index.html ni oching."
  Read-Host 'Enter - yopish'
  exit 1
}

$url = "http://localhost:$port/index.html"
Write-Host ''
Write-Host '  Elektron darslik ochildi:' $url
Write-Host '  Darslik bilan ishlayotganda bu oynani YOPMANG (kichraytirib qo''ying).'
Write-Host '  Tugatgach - shu oynani yoping.'
if (-not $env:DARSLIK_BRAUZERSIZ) { Start-Process $url }  # sinov uchun brauzer ochilmasin

while ($listener.IsListening) {
  try {
    $ctx = $listener.GetContext()
    $res = $ctx.Response
    $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath).TrimStart('/')
    if ($rel -eq '') { $rel = 'index.html' }
    $file = [IO.Path]::GetFullPath((Join-Path $root ($rel -replace '/', '\')))
    if ($file.StartsWith($root, [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $file -PathType Leaf)) {
      $ext = [IO.Path]::GetExtension($file).ToLower()
      if ($types.ContainsKey($ext)) { $res.ContentType = $types[$ext] } else { $res.ContentType = 'application/octet-stream' }
      $bytes = [IO.File]::ReadAllBytes($file)
      $res.ContentLength64 = $bytes.Length
      $res.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
      $res.StatusCode = 404
    }
    $res.Close()
  } catch {
    # brauzer so'rovni yarim yo'lda to'xtatsa - davom etamiz
  }
}
