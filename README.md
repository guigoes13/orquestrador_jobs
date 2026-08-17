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

## Uso manual

```powershell
# Mantém o processo ativo
.\.venv\Scripts\python.exe server.py
```

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

### API local

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

## Novos jobs

Crie o novo processamento em `jobs/<nome_do_job>/`, exponha uma
função sem argumentos e registre-a em `orquestrador/registry.py`. Depois adicione
uma seção `[job:<nome_do_job>]` ao `orchestrator.ini`.
