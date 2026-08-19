# Gerador de Políticas de Senha e Compliance

Ferramenta de linha de comando para validar políticas de senha corporativas contra dois
perfis de referência (NIST SP 800-63B e ISO/IEC 27001), tanto a nível de configuração
exportada (ex.: de um AD/GPO) quanto de senhas individuais.

## Requisitos
Nenhuma dependência externa (apenas biblioteca padrão do Python 3).

## Uso

Gerar um arquivo de configuração de exemplo (conforme):
```
python app.py gerar-exemplo --saida config_exemplo.json
```

Validar um arquivo de configuração exportado:
```
python app.py validar-config config_exemplo.json --perfil iso27001
python app.py validar-config config_exemplo.json --perfil nist --saida relatorio.json
```

Validar uma senha individual:
```
python app.py validar-senha "MinhaSenh@Forte123" --perfil iso27001
```

## Formato esperado do arquivo de configuração (JSON)
```json
{
  "tamanho_minimo": 12,
  "exige_maiuscula": true,
  "exige_minuscula": true,
  "exige_numero": true,
  "exige_especial": true,
  "expiracao_dias": 90,
  "bloqueia_reuso_ultimas": 5,
  "bloqueia_senhas_comuns": true,
  "max_tentativas_login": 5
}
```

## Funcionalidades
- Dois perfis de referência embutidos: NIST 800-63B (mais permissivo, foco em tamanho e
  bloqueio de senhas vazadas) e ISO 27001 (mais rígido, com complexidade e expiração).
- Classificação dos achados em NÃO CONFORME (bloqueante) e AVISO (recomendação).
- Código de saída do processo reflete o resultado (0 = conforme, 1 = não conforme) — apto
  para uso em pipelines de auditoria automatizada.
- Validação de senha individual: tamanho, complexidade, lista de senhas comuns e sequências repetidas.
- Exportação do relatório de compliance em JSON.
