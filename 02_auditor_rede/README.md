# Auditor de Configuração de Rede Local

Varre a LAN, identifica hosts (IP/MAC/hostname), portas abertas e gera relatório de compliance
apontando portas de risco (Telnet, FTP, SMB exposto, RDP exposto etc.) e ausência de DNS reverso.

## Requisitos
```
pip install -r requirements.txt
```
No Windows é necessário o **Npcap** instalado (https://npcap.com) para o Scapy capturar pacotes ARP,
e a aplicação deve rodar como Administrador. Sem isso, a ferramenta cai automaticamente para um modo
fallback (via sockets TCP) que funciona sem privilégios especiais, apenas com descoberta menos precisa.

## Executar
```
python app.py
```

## Funcionalidades
- Descoberta de hosts ativos na rede informada (CIDR).
- Varredura de portas configurável (lista padrão de portas comuns).
- Resolução de hostname via DNS reverso.
- Motor de regras de compliance (portas de risco conhecidas, DNS reverso ausente).
- Interface Tkinter com tabela colorida (verde = OK, vermelho = não conforme).
- Exportação de relatório em JSON e CSV.
