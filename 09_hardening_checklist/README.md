# Ferramenta de Hardening Checklist (CIS Benchmark local)

CLI que executa um checklist de hardening de sistema operacional, inspirado em controles
do CIS Benchmark, detectando automaticamente Windows ou Linux, e reporta gaps com
recomendação de correção.

## Requisitos
```
pip install -r requirements.txt
```
No Windows, alguns checks usam `netsh`, `net accounts` e PowerShell (já nativos do SO).
No Linux, alguns checks usam `sshd -T`, `/etc/login.defs`, `systemctl`/`ufw` (podem exigir
privilégios elevados para leitura completa).

## Executar
```
python app.py
python app.py --saida relatorio.json
```
Código de saída do processo: `0` = 100% conforme, `1` = algum gap encontrado (apto para CI/agendador).

## Controles verificados

### Multiplataforma
- Nenhum serviço de alto risco (FTP/Telnet/SMB/RDP/VNC) escutando em portas expostas.
- Revisão de sessões de usuário ativas.
- Espaço em disco do volume raiz/sistema abaixo de 90%.

### Windows
- Firewall do Windows ativo em todos os perfis.
- Tamanho mínimo de senha ≥ 8 caracteres (via `net accounts`).
- Protocolo SMBv1 desabilitado.
- Estado do serviço WinRM (informativo).

### Linux
- SSH: `PermitRootLogin no`.
- `PASS_MAX_DAYS` ≤ 90 dias em `/etc/login.defs`.
- Firewall (`firewalld` ou `ufw`) habilitado.

## Funcionalidades
- Detecção automática de plataforma (Windows/Linux) e execução dos checks pertinentes.
- Relatório no console com evidência e recomendação para cada gap encontrado.
- Exportação do relatório completo em JSON para auditoria/histórico.
