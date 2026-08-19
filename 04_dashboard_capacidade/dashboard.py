"""
Dashboard de Capacidade de Disco e Memória (multi-máquina)
Consolida os arquivos JSON gravados pelos agentes locais (agente.py) em uma pasta
compartilhada/rede e exibe um painel consolidado com alertas de capacidade.
Stack: Python + PyQt5 + psutil (para a própria máquina do dashboard, opcional)
"""
import sys
import os
import json
import glob
import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QLineEdit,
    QHeaderView, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer

LIMITE_DISCO_ALERTA = 85.0  # percentual
LIMITE_MEMORIA_ALERTA = 90.0  # percentual


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Capacidade de Disco e Memória (Multi-Máquina)")
        self.resize(1200, 700)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        top = QHBoxLayout()
        top.addWidget(QLabel("Pasta compartilhada de métricas:"))
        self.pasta_edit = QLineEdit(os.path.join(os.path.dirname(os.path.abspath(__file__)), "metrics"))
        top.addWidget(self.pasta_edit)
        btn_escolher = QPushButton("Escolher pasta...")
        btn_escolher.clicked.connect(self.escolher_pasta)
        top.addWidget(btn_escolher)
        btn_atualizar = QPushButton("Atualizar Agora")
        btn_atualizar.clicked.connect(self.atualizar)
        top.addWidget(btn_atualizar)
        layout.addLayout(top)

        self.status_label = QLabel("Aguardando dados...")
        layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Máquina", "Última Coleta", "CPU %", "Memória %", "Swap %",
            "Disco (pior partição)", "% Uso Disco", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.detalhe_label = QLabel("Selecione uma máquina para ver detalhes de todas as partições.")
        layout.addWidget(self.detalhe_label)
        self.table.cellClicked.connect(self.mostrar_detalhes)

        self.dados_por_maquina = {}

        os.makedirs(self.pasta_edit.text(), exist_ok=True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.atualizar)
        self.timer.start(30000)  # atualiza a cada 30s

        self.atualizar()

    def escolher_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Escolher pasta de métricas")
        if pasta:
            self.pasta_edit.setText(pasta)
            self.atualizar()

    def atualizar(self):
        pasta = self.pasta_edit.text().strip()
        if not os.path.isdir(pasta):
            self.status_label.setText(f"Pasta não encontrada: {pasta}")
            return

        arquivos = glob.glob(os.path.join(pasta, "*.json"))
        self.dados_por_maquina = {}
        for arq in arquivos:
            try:
                with open(arq, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                self.dados_por_maquina[dados["hostname"]] = dados
            except (json.JSONDecodeError, KeyError, OSError):
                continue

        self.table.setRowCount(len(self.dados_por_maquina))
        alertas = 0
        for i, (hostname, dados) in enumerate(sorted(self.dados_por_maquina.items())):
            discos = dados.get("discos", [])
            pior_disco = max(discos, key=lambda d: d["percentual_uso"], default=None)
            mem_pct = dados.get("memoria", {}).get("percentual_uso", 0)
            swap_pct = dados.get("swap", {}).get("percentual_uso", 0)
            cpu_pct = dados.get("cpu_percent", 0)

            problema = False
            if pior_disco and pior_disco["percentual_uso"] >= LIMITE_DISCO_ALERTA:
                problema = True
            if mem_pct >= LIMITE_MEMORIA_ALERTA:
                problema = True
            if problema:
                alertas += 1

            valores = [
                hostname,
                dados.get("timestamp", "N/D"),
                f"{cpu_pct:.1f}",
                f"{mem_pct:.1f}",
                f"{swap_pct:.1f}",
                pior_disco["ponto_montagem"] if pior_disco else "N/D",
                f"{pior_disco['percentual_uso']:.1f}" if pior_disco else "N/D",
                "ALERTA" if problema else "OK",
            ]
            for j, val in enumerate(valores):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if problema:
                    item.setBackground(Qt.red if j == 7 else item.background())
                self.table.setItem(i, j, item)

        agora = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_label.setText(
            f"[{agora}] {len(self.dados_por_maquina)} máquina(s) monitorada(s) | {alertas} com alerta de capacidade."
        )

    def mostrar_detalhes(self, row, _col):
        hostname_item = self.table.item(row, 0)
        if not hostname_item:
            return
        hostname = hostname_item.text()
        dados = self.dados_por_maquina.get(hostname)
        if not dados:
            return
        linhas = [f"Detalhes de partições - {hostname}:"]
        for d in dados.get("discos", []):
            linhas.append(
                f"  {d['ponto_montagem']} ({d['dispositivo']}): "
                f"{d['usado_gb']}GB usados / {d['total_gb']}GB total "
                f"({d['percentual_uso']}%)"
            )
        self.detalhe_label.setText("\n".join(linhas))


def main():
    app = QApplication(sys.argv)
    win = DashboardWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
