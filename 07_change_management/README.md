# Gestor de Change Management (RFC interno)

Fluxo de aprovação de mudanças de TI (Request for Change) com máquina de estados e trilha
de auditoria imutável (nenhum evento de auditoria é apagado, mesmo excluindo a RFC final).

## Requisitos
```
pip install -r requirements.txt
```

## Executar
```
python app.py
```

## Fluxo de estados
```
Rascunho -> Em Análise -> Aprovada -> Em Implementação -> Concluída
                |             |
                v             v
            Rejeitada     Cancelada
```
- Só é permitido transicionar entre estados definidos na máquina de estados (`TRANSICOES_PERMITIDAS`).
- Aprovação de mudanças de risco **Alto** exige comentário/justificativa obrigatório.
- Edição direta do formulário só é permitida enquanto a RFC está em **Rascunho**.
- Exclusão só é permitida para RFCs em **Rascunho** ou **Cancelada** (preserva histórico de mudanças reais).

## Funcionalidades
- Cadastro de RFC com título, solicitante, tipo (normal/emergencial/padrão), risco,
  sistemas afetados, data planejada e plano de rollback obrigatório.
- Fluxo de aprovação com validações de transição de estado.
- Trilha de auditoria completa (quem, quando, o quê) por RFC, em aba dedicada.
- Filtro por texto e por estado.
- Exportação para CSV.
