"""
Simulador de Topologia de Rede
Desenha topologia, simula falhas de nó/link, e calcula caminhos redundantes.
Stack: Python + NetworkX + Matplotlib (interface interativa via cliques no gráfico)
"""
import json
import os
import sys
import networkx as nx
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox

TOPOLOGIA_EXEMPLO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "topologia_exemplo.json")


def gerar_topologia_exemplo():
    """Gera uma topologia de exemplo: 2 datacenters conectados por 3 links redundantes,
    cada um com switches e servidores."""
    G = nx.Graph()
    nos = {
        "DC1-Core": "core",
        "DC2-Core": "core",
        "DC1-Switch1": "switch",
        "DC1-Switch2": "switch",
        "DC2-Switch1": "switch",
        "DC2-Switch2": "switch",
        "DC1-Server1": "server",
        "DC1-Server2": "server",
        "DC2-Server1": "server",
        "DC2-Server2": "server",
        "ISP-Link-A": "wan",
        "ISP-Link-B": "wan",
    }
    for no, tipo in nos.items():
        G.add_node(no, tipo=tipo)

    arestas = [
        ("DC1-Core", "ISP-Link-A"), ("DC1-Core", "ISP-Link-B"),
        ("DC2-Core", "ISP-Link-A"), ("DC2-Core", "ISP-Link-B"),
        ("DC1-Core", "DC1-Switch1"), ("DC1-Core", "DC1-Switch2"),
        ("DC2-Core", "DC2-Switch1"), ("DC2-Core", "DC2-Switch2"),
        ("DC1-Switch1", "DC1-Server1"), ("DC1-Switch2", "DC1-Server2"),
        ("DC2-Switch1", "DC2-Server1"), ("DC2-Switch2", "DC2-Server2"),
    ]
    G.add_edges_from(arestas)
    return G


def salvar_topologia(G, caminho):
    data = nx.node_link_data(G)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def carregar_topologia(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data)


CORES_TIPO = {
    "core": "#e74c3c",
    "switch": "#3498db",
    "server": "#2ecc71",
    "wan": "#f39c12",
    None: "#95a5a6",
}


class SimuladorTopologia:
    def __init__(self, grafo):
        self.grafo_original = grafo.copy()
        self.grafo_atual = grafo.copy()
        self.nos_removidos = set()
        self.links_removidos = set()
        self.origem = None
        self.destino = None

        self.fig, self.ax = plt.subplots(figsize=(11, 7))
        plt.subplots_adjust(bottom=0.22)
        self.pos = nx.spring_layout(self.grafo_original, seed=42)

        ax_reset = plt.axes([0.15, 0.05, 0.15, 0.06])
        ax_caminho = plt.axes([0.35, 0.05, 0.2, 0.06])
        ax_textbox_o = plt.axes([0.58, 0.12, 0.15, 0.05])
        ax_textbox_d = plt.axes([0.58, 0.05, 0.15, 0.05])

        self.btn_reset = Button(ax_reset, "Resetar Falhas")
        self.btn_reset.on_clicked(self.resetar)

        self.btn_caminho = Button(ax_caminho, "Calcular Caminhos")
        self.btn_caminho.on_clicked(self.calcular_caminhos)

        self.txt_origem = TextBox(ax_textbox_o, "Origem: ", initial="DC1-Server1")
        self.txt_destino = TextBox(ax_textbox_d, "Destino: ", initial="DC2-Server1")

        self.fig.canvas.mpl_connect("button_press_event", self.on_click)
        self.desenhar()

    def desenhar(self, destaque_caminho=None, mensagem=None):
        self.ax.clear()
        cores = []
        for n in self.grafo_atual.nodes():
            tipo = self.grafo_atual.nodes[n].get("tipo")
            cores.append(CORES_TIPO.get(tipo, CORES_TIPO[None]))

        nx.draw_networkx_nodes(self.grafo_atual, self.pos, ax=self.ax, node_color=cores, node_size=900)
        nx.draw_networkx_labels(self.grafo_atual, self.pos, ax=self.ax, font_size=7)

        edge_colors = []
        edges = list(self.grafo_atual.edges())
        for e in edges:
            if destaque_caminho and (e in destaque_caminho or (e[1], e[0]) in destaque_caminho):
                edge_colors.append("#e91e63")
            else:
                edge_colors.append("#7f8c8d")
        nx.draw_networkx_edges(self.grafo_atual, self.pos, ax=self.ax, edge_color=edge_colors,
                                width=[3 if c == "#e91e63" else 1.5 for c in edge_colors])

        titulo = "Simulador de Topologia de Rede\n"
        titulo += "Clique num nó = falha de nó | Clique numa aresta (perto do meio) = falha de link"
        if mensagem:
            titulo += f"\n{mensagem}"
        self.ax.set_title(titulo, fontsize=10)
        self.ax.set_axis_off()
        self.fig.canvas.draw_idle()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return

        # Verifica clique próximo a um nó
        for n, (x, y) in self.pos.items():
            if (x - event.xdata) ** 2 + (y - event.ydata) ** 2 < 0.002:
                self.simular_falha_no(n)
                return

        # Verifica clique próximo ao meio de uma aresta
        for u, v in self.grafo_atual.edges():
            xu, yu = self.pos[u]
            xv, yv = self.pos[v]
            mx, my = (xu + xv) / 2, (yu + yv) / 2
            if (mx - event.xdata) ** 2 + (my - event.ydata) ** 2 < 0.0015:
                self.simular_falha_link(u, v)
                return

    def simular_falha_no(self, no):
        if no not in self.grafo_atual:
            return
        self.grafo_atual.remove_node(no)
        self.nos_removidos.add(no)
        self.desenhar(mensagem=f"Nó '{no}' marcado como FORA DO AR.")

    def simular_falha_link(self, u, v):
        if not self.grafo_atual.has_edge(u, v):
            return
        self.grafo_atual.remove_edge(u, v)
        self.links_removidos.add((u, v))
        self.desenhar(mensagem=f"Link '{u} - {v}' marcado como INDISPONÍVEL.")

    def resetar(self, _event=None):
        self.grafo_atual = self.grafo_original.copy()
        self.nos_removidos.clear()
        self.links_removidos.clear()
        self.desenhar(mensagem="Falhas resetadas. Topologia restaurada ao estado original.")

    def calcular_caminhos(self, _event=None):
        origem = self.txt_origem.text.strip()
        destino = self.txt_destino.text.strip()
        self.origem, self.destino = origem, destino

        if origem not in self.grafo_atual or destino not in self.grafo_atual:
            self.desenhar(mensagem=f"Nó de origem/destino inválido ou fora do ar após falhas simuladas.")
            return

        if not nx.has_path(self.grafo_atual, origem, destino):
            self.desenhar(mensagem=f"SEM CAMINHO disponível entre {origem} e {destino} com as falhas atuais!")
            return

        caminho_curto = nx.shortest_path(self.grafo_atual, origem, destino)
        edges_caminho = list(zip(caminho_curto[:-1], caminho_curto[1:]))

        try:
            caminhos_disjuntos = list(nx.edge_disjoint_paths(self.grafo_atual, origem, destino))
            n_redundantes = len(caminhos_disjuntos)
        except nx.NetworkXNoPath:
            n_redundantes = 0

        msg = (f"Caminho mais curto ({len(caminho_curto)-1} saltos): {' -> '.join(caminho_curto)} | "
               f"Caminhos redundantes (sem aresta em comum): {n_redundantes}")
        self.desenhar(destaque_caminho=edges_caminho, mensagem=msg)

    def run(self):
        plt.show()


def main():
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        grafo = carregar_topologia(sys.argv[1])
        print(f"Topologia carregada de: {sys.argv[1]}")
    else:
        grafo = gerar_topologia_exemplo()
        salvar_topologia(grafo, TOPOLOGIA_EXEMPLO)
        print(f"Usando topologia de exemplo (salva em {TOPOLOGIA_EXEMPLO}).")
        print("Para carregar sua própria topologia: python app.py caminho_para_topologia.json")

    sim = SimuladorTopologia(grafo)
    sim.run()


if __name__ == "__main__":
    main()
