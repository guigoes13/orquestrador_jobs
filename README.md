# Orquestrador local

Aplicação Flask sem interface gráfica que permanece ligada no servidor do
cliente, centraliza e executa jobs recorrentes. O primeiro job sincroniza
produtos, vendas e inventário entre o Firebird e o SharePoint.

O acesso ao SharePoint usa MSAL com credenciais de aplicação e a Microsoft
Graph API. Não há autenticação interativa ou dependência da biblioteca antiga
do Office 365.

## Estrutura

```text
orquestrador/
├── scheduler.py                  # ciclo contínuo e execução dos jobs
└── registry.py                   # registro central de jobs
jobs/
└── processar_produtos/           # processamento completo e visível
src/
├── config.py                     # configuração compartilhada entre jobs
└── api_sharepoint/               # cliente compartilhado do SharePoint
scripts/
├── install_windows_task.ps1     # instala e inicia no Windows
└── uninstall_windows_task.ps1   # remove a instalação
orchestrator.ini                  # intervalos e jobs habilitados
server.py                         # único ponto de entrada Flask
```

## Preparação

### Instalação automática recomendada

Copie a pasta para o servidor e execute:

```text
install.bat
```

O instalador solicita permissão de administrador e realiza automaticamente:

1. instalação do Python 3.12 pelo `winget`, se necessária;
2. criação da `.venv`;
3. instalação das dependências;
4. criação do `ConfigApp.ini` inicial;
5. instalação e inicialização da tarefa do Windows.

Na primeira execução, preencha o `ConfigApp.ini` criado e execute o
`install.bat` novamente. As credenciais não podem ser preenchidas
automaticamente.

Para remover a inicialização automática, execute `uninstall.bat` como
administrador. Os arquivos e o ambiente virtual permanecem preservados.

### Preparação manual

Se preferir instalar manualmente, use:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copie `ConfigApp.example.ini` para `ConfigApp.ini`, preencha os campos e mantenha
o arquivo na raiz. As credenciais não devem ser incluídas no controle de versão.

A aplicação registrada no Microsoft Entra precisa de permissão de aplicativo
`Sites.ReadWrite.All` no Microsoft Graph, com consentimento do administrador.

## Operação manual

Execute os comandos abaixo no PowerShell, a partir da pasta raiz do projeto.

### Iniciar o orquestrador

```powershell
.\.venv\Scripts\python.exe server.py
```

O comando mantém o processo ativo no terminal. Enquanto ele estiver rodando,
a API estará disponível em `http://127.0.0.1:5000`. Para confirmar que o
orquestrador iniciou corretamente, abra outro PowerShell e execute:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/health"
```

Uma resposta com `status` igual a `ok` indica que o serviço está funcionando.

### Executar o job manualmente

O orquestrador deve estar ligado. Em outro PowerShell, execute:

```powershell
Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:5000/jobs/processar_produtos/run"
```

A resposta `status: started` significa que o job foi aceito e começou a rodar
em segundo plano. Ela não significa que o processamento já terminou.

Consulte o estado do job com:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/jobs"
```

- `running: true`: o job ainda está executando;
- `running: false`: o job terminou ou falhou;
- `next_run`: data e hora da próxima execução automática.

Para saber se o job terminou com sucesso ou falhou, acompanhe o log:

```powershell
Get-Content ".\logs\orchestrator.log" -Tail 50 -Wait
```

Pressione `Ctrl+C` para parar apenas o acompanhamento do log. Isso não encerra
o orquestrador.

Se o job já estiver em execução, uma segunda solicitação não cria outra
instância simultânea. Aguarde o término e consulte o log.

### Desligar o orquestrador

Se o orquestrador estiver rodando no terminal, selecione esse terminal e
pressione `Ctrl+C`. Esse é o modo recomendado para uma execução manual.

Se o processo estiver oculto, primeiro identifique quem está ouvindo na porta
5000:

```powershell
Get-NetTCPConnection -LocalPort 5000 -State Listen
```

Confira o valor da coluna `OwningProcess` e encerre esse PID somente depois de
confirmar que ele pertence ao `server.py` deste projeto:

```powershell
Get-CimInstance Win32_Process -Filter "ProcessId = NUMERO_DO_PID" |
    Select-Object ProcessId, ExecutablePath, CommandLine

Stop-Process -Id NUMERO_DO_PID
```

Exemplo: se `OwningProcess` for `28100`, use `Stop-Process -Id 28100`.

Confirme que o serviço parou:

```powershell
Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
```

Se o comando não retornar nenhuma conexão, o orquestrador está desligado.

> **Atenção:** encerrar o orquestrador interrompe imediatamente qualquer job
> que esteja rodando. A aplicação atualmente não possui um comando para
> cancelar somente um job.

O arquivo `orchestrator.ini` controla a frequência:

```ini
[server]
host = 127.0.0.1
port = 5000

[job:processar_produtos]
enabled = true
interval_minutes = 15
run_on_start = false
```

Se uma execução durar mais que o intervalo, o próximo ciclo daquele job é
ignorado. Outros jobs continuam funcionando normalmente.

### Referência da API local

Com o servidor ativo:

- `GET http://127.0.0.1:5000/health`: saúde da aplicação;
- `GET http://127.0.0.1:5000/jobs`: status e próxima execução;
- `POST http://127.0.0.1:5000/jobs/processar_produtos/run`: execução manual.

O endereço padrão aceita somente conexões da própria máquina. Isso evita
expor os comandos de execução na rede do cliente sem necessidade.

## Instalação 24 horas no Windows

O `install.bat` já realiza esta etapa. Para registrar somente a tarefa de forma
manual, abra o PowerShell como administrador e execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows_task.ps1
```

A instalação cria a tarefa `OrquestradorCliente`, que:

- inicia junto com o computador, sem login de usuário;
- executa pela conta local `SYSTEM`;
- não permite instâncias duplicadas;
- reinicia o processo apó um minuto caso ele encerre;
- não possui limite de tempo de execução.

Os logs ficam em `logs/orchestrator.log`. Para remover a tarefa:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall_windows_task.ps1
```

### Controlar a tarefa agendada

Abra o PowerShell como administrador. Para desligar o orquestrador iniciado
pela tarefa do Windows sem remover sua instalação:

```powershell
Stop-ScheduledTask -TaskName "OrquestradorCliente"
```

Para iniciá-lo novamente:

```powershell
Start-ScheduledTask -TaskName "OrquestradorCliente"
```

Para verificar o estado da tarefa:

```powershell
Get-ScheduledTask -TaskName "OrquestradorCliente" |
    Select-Object TaskName, State
```

Quando a tarefa agendada estiver ativa, não encerre apenas o processo Python:
a configuração pode iniciá-lo novamente. Pare primeiro a tarefa com
`Stop-ScheduledTask`.

Para remover definitivamente a inicialização automática, execute como
administrador:

```powershell
.\uninstall.bat
```

Esse comando remove a tarefa agendada, mas preserva o código, as configurações,
os logs e o ambiente virtual.

## Novos jobs

Crie o novo processamento em `jobs/<nome_do_job>/`, exponha uma
função sem argumentos e registre-a em `orquestrador/registry.py`. Depois adicione
uma seção `[job:<nome_do_job>]` ao `orchestrator.ini`.

Recursos que podem ser reutilizados por vários jobs ficam em `src`. Para usar a
configuração geral e o cliente do SharePoint em um job:

```python
from src.api_sharepoint import SharePointRepository
from src.config import load_config

config = load_config("ConfigApp.ini")
sharepoint = SharePointRepository(config.sharepoint)
```

O diretório `jobs` deve conter apenas a regra de negócio de cada processamento;
conexões, configurações e outros componentes compartilhados devem ficar em
`src`.
