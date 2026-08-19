# Controlador de Backup Local com Verificação de Integridade

Agenda backups locais (compactados em .zip), calcula hash (SHA-256/SHA-1/MD5) de cada
arquivo no momento do backup, e permite validar a restauração comparando os hashes
originais com os do conteúdo extraído.

## Requisitos
Nenhuma dependência externa (apenas biblioteca padrão do Python 3, incluindo Tkinter).

## Executar
```
python app.py
```

## Funcionalidades
- Backup completo de uma pasta de origem para um `.zip` com timestamp na pasta de destino.
- Geração de manifesto de integridade (`_hashes/<arquivo>.zip.manifest.json`) com o hash
  de cada arquivo original, salvo junto ao backup.
- Agendamento simples em background (a cada N minutos) sem dependências externas (thread + sleep).
- Validação de restauração: extrai o `.zip` em uma pasta temporária, recalcula os hashes de
  todos os arquivos e compara com o manifesto original, apontando arquivos ausentes,
  arquivos com hash divergente (corrupção/alteração) e arquivos inesperados.
- Log de operações em tempo real na interface.
- Configuração de pastas de origem/destino persistida entre execuções (`backup_config.json`).

## Fluxo recomendado
1. Escolher pasta de origem e destino.
2. Rodar "Executar Backup Agora" (ou configurar um agendamento).
3. Periodicamente, selecionar um dos `.zip` gerados e clicar em "Validar Restauração" para
   confirmar que o backup pode ser restaurado com integridade garantida.
