# Gerenciador de Licenças de Software

Controla chaves de licença, validade contratual e quantidade de instalações permitidas.

## Requisitos
```
pip install -r requirements.txt
```

## Executar
```
python app.py
```

## Funcionalidades
- Cadastro de licenças (software, fornecedor, chave única, tipo, contrato, valor).
- Registro de instalações por máquina/usuário, com bloqueio automático ao atingir o limite contratado.
- Aba de Alertas: licenças vencidas/vencendo em 30 dias e limites de instalação atingidos.
- Busca por software, fornecedor ou contrato.
- Exportação para CSV.
- Banco SQLite local (`licencas.db`), criado automaticamente.
