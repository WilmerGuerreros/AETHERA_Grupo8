$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    py -3 -m venv (Join-Path $PSScriptRoot ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear el entorno virtual. Instala Python 3 y vuelve a intentarlo."
    }
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo actualizar pip."
}

& $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron instalar las dependencias de Aethera."
}

$basePython = (& $python -c "import sys; print(sys.base_prefix)").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo localizar la instalación base de Python."
}

$tclRoot = Join-Path $basePython "tcl"
$tclLibrary = Get-ChildItem $tclRoot -Directory -Filter "tcl*" -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName "init.tcl") } |
    Select-Object -First 1
$tkLibrary = Get-ChildItem $tclRoot -Directory -Filter "tk*" -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName "tk.tcl") } |
    Select-Object -First 1
if (-not $tclLibrary -or -not $tkLibrary) {
    throw "La instalación base de Python no incluye Tcl/Tk. Reinstala Python con soporte de Tcl/Tk y vuelve a intentarlo."
}

$env:TCL_LIBRARY = $tclLibrary.FullName
$env:TK_LIBRARY = $tkLibrary.FullName

& $python -m PyInstaller --clean --noconfirm (Join-Path $PSScriptRoot "Aethera.spec")
if ($LASTEXITCODE -ne 0) {
    throw "Falló la creación del ejecutable."
}

$guideName = "GU" + [char]0x00CD + "A.txt"
Copy-Item (Join-Path $PSScriptRoot $guideName) (Join-Path $PSScriptRoot "dist\$guideName") -Force
Write-Host "Ejecutable creado en dist\Aethera.exe"
