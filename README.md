# Governança de TI e Infraestrutura Local — Stack Python

Conjunto de 10 ferramentas independentes de governança de TI e infraestrutura, cada uma em
sua própria pasta, com aplicação funcional, `requirements.txt` e `README.md` próprios.

| # | Projeto | Pasta | Stack |
|---|---------|-------|-------|
| 1 | Inventário de Ativos de TI Offline | [01_inventario_ativos](01_inventario_ativos) | Python + PyQt5 + SQLite |
| 2 | Auditor de Configuração de Rede Local | [02_auditor_rede](02_auditor_rede) | Python + Scapy + Tkinter |
| 3 | Gerenciador de Licenças de Software | [03_gerenciador_licencas](03_gerenciador_licencas) | Python + PyQt5 + SQLite |
| 4 | Dashboard de Capacidade (multi-máquina) | [04_dashboard_capacidade](04_dashboard_capacidade) | Python + PyQt5 + psutil |
| 5 | Gerador de Políticas de Senha e Compliance | [05_politica_senha](05_politica_senha) | Python CLI + argparse |
| 6 | Simulador de Topologia de Rede | [06_simulador_topologia](06_simulador_topologia) | Python + NetworkX + Matplotlib |
| 7 | Gestor de Change Management (RFC) | [07_change_management](07_change_management) | Python + PyQt5 + SQLite |
| 8 | Analisador de Logs de Firewall/Proxy | [08_analisador_logs](08_analisador_logs) | Python + Pandas + PyQt5 |
| 9 | Hardening Checklist (CIS Benchmark local) | [09_hardening_checklist](09_hardening_checklist) | Python CLI + psutil/subprocess |
| 10 | Backup Local com Verificação de Integridade | [10_backup_integridade](10_backup_integridade) | Python + Tkinter + hashlib |

## Como usar cada projeto

Cada pasta é independente e autocontida:
```
cd <pasta_do_projeto>
pip install -r requirements.txt
python app.py        # ou o nome do arquivo indicado no README da pasta
```

## Observações gerais
- Todos os projetos com persistência usam **SQLite local** (arquivo `.db` criado
  automaticamente na primeira execução) — nenhuma infraestrutura de banco externa é necessária.
- Os projetos 1, 3 e 7 (PyQt5) e o projeto 8 (PyQt5 + Pandas) exigem `pip install PyQt5`.
- O projeto 2 (Auditor de Rede) funciona mesmo sem Scapy/privilégios administrativos, caindo
  automaticamente para um modo de descoberta via sockets TCP puro.
- O projeto 9 (Hardening Checklist) detecta automaticamente Windows ou Linux e executa os
  controles pertinentes a cada plataforma.
- Os projetos 5 e 10 não têm dependências externas — usam apenas a biblioteca padrão do Python.
- Todas as ferramentas foram testadas de fato nesta máquina Windows: para os projetos com
  GUI (1, 3, 4, 7, 8 em PyQt5; 2 em Tkinter) a janela real foi instanciada via script de
  teste; para os projetos CLI (5, 9) os comandos foram executados de ponta a ponta; para
  6, 8 e 10 a lógica de negócio (cálculo de caminhos, parsing de log, hash de integridade)
  foi exercitada com dados reais.
