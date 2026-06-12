$f = "D:\Autonomous DFIR - Agentic SOC\src\findevil\ui\static\find-evil.html"
$html = Get-Content $f -Raw
$rx = [regex]'(?s)<script>(.*?)</script>'
$m = $rx.Matches($html)
Write-Output ("extracted {0} inline script blocks" -f $m.Count)
$allok = $true
for ($i = 0; $i -lt $m.Count; $i++) {
  $tmp = Join-Path $env:TEMP ("fe_script_{0}.js" -f $i)
  Set-Content $tmp $m[$i].Groups[1].Value -NoNewline
  $out = node --check $tmp 2>&1 | Out-String
  if ($LASTEXITCODE -eq 0) {
    Write-Output ("block {0}: SYNTAX OK" -f $i)
  } else {
    $allok = $false
    Write-Output ("block {0}: SYNTAX ERROR" -f $i)
    Write-Output $out
  }
}
# Also check the external live JS
$live = node --check "D:\Autonomous DFIR - Agentic SOC\src\findevil\ui\static\find-evil-live.js" 2>&1 | Out-String
if ($LASTEXITCODE -eq 0) { Write-Output "find-evil-live.js: SYNTAX OK" } else { $allok = $false; Write-Output "find-evil-live.js: SYNTAX ERROR"; Write-Output $live }
if ($allok) { Write-Output "ALL_OK" }
