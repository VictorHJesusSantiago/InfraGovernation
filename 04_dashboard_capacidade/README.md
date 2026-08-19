# Dashboard de Capacidade de Disco e Memória (multi-máquina)

Arquitetura de dois componentes:
- **agente.py**: roda em cada estação, coleta CPU/memória/swap/disco via `psutil` e grava um
  arquivo JSON (`<hostname>.json`) numa pasta compartilhada de rede (ou local, para testes).
- **dashboard.py**: aplicação PyQt5 que lê todos os JSONs da pasta compartilhada e consolida
  em um painel único, com destaque de alertas de capacidade.

## Requisitos
```
pip install -r requirements.txt
```

## Executar o agente em cada estação
```
python agente.py --pasta "\\servidor\compartilhamento\metrics" --intervalo 60
```
Use `--intervalo 0` para rodar uma única coleta (útil via Agendador de Tarefas do Windows).

## Executar o dashboard (uma máquina central)
```
python dashboard.py
```
Aponte a "pasta compartilhada de métricas" para o mesmo caminho usado pelos agentes.
Sem uma pasta de rede real disponível, é possível testar tudo localmente: aponte o agente e
o dashboard para a mesma pasta local (padrão: `./metrics`).

## Funcionalidades
- Coleta periódica de CPU, memória, swap e uso de disco por partição.
- Consolidação multi-máquina simples via arquivos compartilhados (sem necessidade de banco central).
- Alertas automáticos: disco ≥ 85% ou memória ≥ 90%.
- Detalhamento por partição ao clicar em uma máquina na tabela.
- Atualização automática a cada 30 segundos (ou manual pelo botão).
