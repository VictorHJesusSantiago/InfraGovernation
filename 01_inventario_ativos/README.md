# Inventário de Ativos de TI Offline

Cadastro completo de hardware/software com ciclo de vida, garantia e depreciação linear automática.

## Requisitos
```
pip install -r requirements.txt
```

## Executar
```
python app.py
```

## Funcionalidades
- Cadastro/edição/exclusão de ativos (hardware, software, periféricos, licenças, rede).
- Número de série único (evita duplicidade).
- Cálculo automático de depreciação linear com base em valor de aquisição, data e vida útil.
- Aba de Alertas: lista ativos com garantia vencida ou a vencer em 30 dias.
- Histórico de eventos por ativo (cadastro, atualização).
- Filtro por texto (nome, série, responsável) e por status.
- Exportação para CSV.
- Banco de dados SQLite local (`inventario.db`), criado automaticamente na primeira execução.
