$ErrorActionPreference = "Stop"

$projectDirectory = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectDirectory ".venv\Scripts\python.exe"
$configPath = Join-Path $projectDirectory "ConfigApp.ini"
$configExample = Join-Path $projectDirectory "ConfigApp.example.ini"

function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $result = & py -3.10 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $result) {
            return $result.Trim()
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $result = & python -c "import sys; assert sys.version_info[:2] == (3, 10); print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $result) {
            return $result.Trim()
        }
    }
    $machinePython = "C:\Program Files\Python310\python.exe"
    if (Test-Path -LiteralPath $machinePython) {
        return $machinePython
    }
    return $null
}

Write-Host "[1/5] Verificando o Python..."
$systemPython = Find-Python
if (-not $systemPython) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python e winget nao foram encontrados. Instale o Python 3.10 e execute novamente."
    }
    Write-Host "Python nao encontrado. Instalando Python 3.10..."
    & winget install --exact --id Python.Python.3.10 --scope machine `
        --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        throw "O winget nao conseguiu instalar o Python (codigo $LASTEXITCODE)."
    }
    $machinePython = "C:\Program Files\Python310\python.exe"
    if (Test-Path -LiteralPath $machinePython) {
        $systemPython = $machinePython
    } else {
        $systemPython = Find-Python
    }
    if (-not $systemPython) {
        throw "Python foi instalado, mas o executavel nao foi localizado. Reinicie e tente novamente."
    }
}
Write-Host "Python: $systemPython"

Write-Host "[2/5] Preparando o ambiente virtual..."
$recreateVenv = -not (Test-Path -LiteralPath $venvPython)
if (-not $recreateVenv) {
    & $venvPython -c "import sys; assert sys.version_info[:2] == (3, 10)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "A .venv existente usa outra versao do Python e sera recriada."
        Remove-Item -LiteralPath (Join-Path $projectDirectory ".venv") -Recurse -Force
        $recreateVenv = $true
    }
}
if ($recreateVenv) {
    & $systemPython -m venv (Join-Path $projectDirectory ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Nao foi possivel criar a .venv." }
}

Write-Host "[3/5] Instalando as dependencias..."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar o pip." }
& $venvPython -m pip install -r (Join-Path $projectDirectory "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependencias." }

Write-Host "[4/5] Verificando a configuracao..."
if (-not (Test-Path -LiteralPath $configPath)) {
    Copy-Item -LiteralPath $configExample -Destination $configPath
    Write-Warning "ConfigApp.ini criado. Preencha as credenciais e execute install.bat novamente."
    exit 2
}
if (Select-String -LiteralPath $configPath -Pattern "PREENCHA" -Quiet) {
    Write-Warning "O ConfigApp.ini ainda possui campos PREENCHA. Corrija-os e execute novamente."
    exit 2
}

& $venvPython -c "from orquestrador.registry import JOBS; assert JOBS"
if ($LASTEXITCODE -ne 0) { throw "A aplicacao nao passou na validacao inicial." }

Write-Host "[5/5] Instalando a inicializacao automatica..."
& (Join-Path $PSScriptRoot "install_windows_task.ps1") -PythonPath $venvPython
if ($LASTEXITCODE -ne 0) { throw "Nao foi possivel registrar a tarefa do Windows." }

Write-Host "Aplicacao instalada e iniciada."
