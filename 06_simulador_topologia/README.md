# Simulador de Topologia de Rede

Desenha uma topologia de rede (nós: core, switch, servidor, WAN), permite simular falhas de
nó/link interativamente clicando no gráfico, e calcula o caminho mais curto e o número de
caminhos redundantes (sem arestas em comum) entre dois pontos.

## Requisitos
```
pip install -r requirements.txt
```

## Executar
```
python app.py
```
Ou carregando uma topologia própria (JSON no formato `networkx.node_link_data`):
```
python app.py minha_topologia.json
```

## Uso
- Ao abrir, uma topologia de exemplo é gerada (2 datacenters interligados por 2 links de
  ISP redundantes) e salva em `topologia_exemplo.json`.
- **Clique em um nó** para simular sua falha (nó é removido do grafo ativo).
- **Clique próximo ao meio de uma aresta** para simular falha do link.
- Preencha os campos "Origem" e "Destino" e clique em **Calcular Caminhos** para ver o
  caminho mais curto (destacado em rosa) e a quantidade de caminhos redundantes
  disponíveis considerando as falhas simuladas.
- **Resetar Falhas** restaura a topologia original.

## Funcionalidades
- Visualização colorida por tipo de nó (core, switch, servidor, WAN).
- Simulação interativa de falha de nó e de link.
- Cálculo de caminho mais curto (Dijkstra/BFS via NetworkX).
- Cálculo de caminhos redundantes disjuntos por aresta (`edge_disjoint_paths`), essencial
  para avaliar resiliência da rede a falhas simultâneas.
- Persistência de topologias customizadas em JSON.
