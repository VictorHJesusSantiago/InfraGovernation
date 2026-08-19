# Analisador de Logs de Firewall/Proxy (offline)

Importa arquivos de log exportados de Squid, pfSense e Windows Firewall, normaliza tudo
em um schema único e aplica um motor de correlação para sinalizar anomalias.

## Requisitos
```
pip install -r requirements.txt
```

## Executar
```
python app.py
```

## Formatos suportados
- **Squid** (`access.log`): formato padrão de log de acesso (`timestamp cliente_ip status/codigo bytes metodo url usuario ...`).
- **pfSense** (`filterlog` exportado como CSV): colunas `timestamp, action, proto, src, src_port, dst, dst_port`.
- **Windows Firewall** (`pfirewall.log`, formato W3C estendido): `date time action protocol src-ip dst-ip src-port dst-port ...`.

## Funcionalidades
- Importação de múltiplos arquivos simultaneamente, mesmo de formatos diferentes (normalizados no mesmo schema).
- Aba **Eventos**: tabela completa navegável, com filtro por origem/destino e por ação (permitido/negado).
- Aba **Anomalias Detectadas**: motor de correlação simples que sinaliza:
  - Origem com 10+ conexões negadas (possível varredura/força bruta).
  - Origem acessando 20+ destinos distintos (possível scan de rede).
  - Origem usando 15+ portas de destino distintas (possível scan de portas).
- Aba **Resumo Estatístico**: totais, permitidos vs. negados, origens/destinos únicos.
- Exportação dos eventos filtrados para CSV.

## Arquitetura
- `parsers.py`: contém a lógica de parsing pura (testável isoladamente, sem dependência de UI).
- `app.py`: interface PyQt5 que consome os parsers e exibe os resultados.
