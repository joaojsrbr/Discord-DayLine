<#
    Script de automação do projeto Discord DayLine
    Uso: .\build.ps1 <comando>

    Comandos:
      setup     -> instala dependências (uv sync)
      run       -> roda o script (com console, pra ver logs)
      run-silent-> roda sem janela de console (pythonw)
      build     -> gera o .exe com PyInstaller
      clean     -> apaga dist/, build/, *.spec e __pycache__
      env       -> cria o arquivo .env a partir do .env.example (se não existir)
      all       -> setup + build (fluxo completo)
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "run", "run-silent", "build", "clean", "env", "all", "help")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$ScriptName = "main.py"
$ExeName = "DiscordDayLine"

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Test-UvInstalled {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "ERRO: 'uv' não foi encontrado no PATH." -ForegroundColor Red
        Write-Host "Instale com: powershell -c `"irm https://astral.sh/uv/install.ps1 | iex`"" -ForegroundColor Yellow
        exit 1
    }
}

function Ensure-EnvFile {
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Host "Arquivo .env criado a partir de .env.example." -ForegroundColor Yellow
            Write-Host "-> Edite o .env e preencha o DISCORD_BOT_TOKEN antes de rodar." -ForegroundColor Yellow
        }
        else {
            @"
DISCORD_APP_ID=1521888010335948830
DISCORD_USER_ID=902909180426473512
DISCORD_BOT_TOKEN=SEU_TOKEN_AQUI
UPDATE_INTERVAL_MINUTES=10
"@ | Out-File -Encoding utf8 ".env"
            Write-Host "Arquivo .env criado com valores padrão." -ForegroundColor Yellow
            Write-Host "-> Edite o .env e preencha o DISCORD_BOT_TOKEN antes de rodar." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host ".env já existe, nada a fazer." -ForegroundColor Green
    }
}

function Do-Setup {
    Test-UvInstalled
    Write-Step "Sincronizando dependencias (uv sync)"
    uv sync
    Ensure-EnvFile
    Write-Host "`nSetup concluido." -ForegroundColor Green
}

function Do-Run {
    Test-UvInstalled
    if (-not (Test-Path ".env")) {
        Write-Host "AVISO: .env nao encontrado. Rodando 'env' primeiro..." -ForegroundColor Yellow
        Ensure-EnvFile
    }
    Write-Step "Rodando $ScriptName"
    uv run $ScriptName
}

function Do-RunSilent {
    Test-UvInstalled
    if (-not (Test-Path ".env")) {
        Ensure-EnvFile
    }
    Write-Step "Rodando $ScriptName sem console (pythonw)"
    $pythonwPath = Join-Path (uv python find) "" | Split-Path -Parent
    $pythonw = Join-Path ".venv\Scripts" "pythonw.exe"
    if (-not (Test-Path $pythonw)) {
        Write-Host "pythonw.exe nao encontrado em .venv\Scripts. Rode '.\build.ps1 setup' primeiro." -ForegroundColor Red
        exit 1
    }
    Start-Process -FilePath $pythonw -ArgumentList $ScriptName -WorkingDirectory (Get-Location)
    Write-Host "Rodando em background (sem janela)." -ForegroundColor Green
}

function Do-Build {
    Test-UvInstalled
    Write-Step "Instalando pyinstaller (dev dependency)"
    uv add --dev pyinstaller | Out-Null

    Write-Step "Gerando .ico a partir de assets/icon.png"
    $iconArg = @()
    if (Test-Path "assets\icon.png") {
        uv run make_icon.py
        if (Test-Path "assets\icon.ico") {
            $iconArg = @("--icon", "assets\icon.ico")
            Write-Host "Usando icone customizado: assets\icon.ico" -ForegroundColor Green
        }
    }
    else {
        Write-Host "AVISO: assets\icon.png nao encontrado. Buildando com icone padrao do PyInstaller." -ForegroundColor Yellow
    }

    Write-Step "Buildando executavel com PyInstaller"
    uv run pyinstaller --onefile --noconsole --name $ExeName --add-data "assets;assets" @iconArg $ScriptName

    Write-Step "Copiando .env para dist/"
    if (Test-Path ".env") {
        Copy-Item ".env" "dist\.env" -Force
        Write-Host ".env copiado para dist/" -ForegroundColor Green
    }
    else {
        Write-Host "AVISO: .env nao encontrado, copie manualmente para dist/ antes de rodar o .exe" -ForegroundColor Yellow
    }

    Write-Host "`nBuild concluido: dist\$ExeName.exe" -ForegroundColor Green
}

function Do-Clean {
    Write-Step "Limpando artefatos de build"
    $paths = @("dist", "build", "__pycache__", "*.spec")
    foreach ($p in $paths) {
        if (Test-Path $p) {
            Remove-Item -Recurse -Force $p
            Write-Host "Removido: $p" -ForegroundColor Yellow
        }
    }
    Write-Host "Limpeza concluida." -ForegroundColor Green
}

function Show-Help {
    Write-Host @"

Discord DayLine - script de build

Uso: .\build.ps1 <comando>

Comandos disponiveis:
  setup       Instala dependencias e cria o .env se nao existir
  env         Apenas cria/verifica o arquivo .env
  run         Roda o script com console (bom pra debugar / ver logs)
  run-silent  Roda o script sem janela de console (pythonw)
  build       Gera o executavel .exe (dist\$ExeName.exe) e copia o .env
  clean       Remove dist/, build/, *.spec e __pycache__
  all         Roda setup + build de uma vez

Exemplos:
  .\build.ps1 setup
  .\build.ps1 run
  .\build.ps1 build
  .\build.ps1 all

"@ -ForegroundColor White
}

switch ($Command) {
    "setup"      { Do-Setup }
    "run"        { Do-Run }
    "run-silent" { Do-RunSilent }
    "build"      { Do-Build }
    "clean"      { Do-Clean }
    "env"        { Ensure-EnvFile }
    "all"        { Do-Setup; Do-Build }
    default      { Show-Help }
}