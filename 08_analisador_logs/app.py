"""
Analisador de Logs de Firewall/Proxy (offline)
Importa logs (Squid, pfSense, Windows Firewall), correlaciona e sinaliza anomalias.
Stack: Python + Pandas + PyQt5
"""
import sys
import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QLabel, QLineEdit,
    QMessageBox, QTabWidget, QHeaderView
)
from PyQt5.QtCore import Qt

from parsers import PARSERS, detectar_anomalias, COLUNAS_PADRAO


class AnalisadorLogsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analisador de Logs de Firewall/Proxy (offline)")
        self.resize(1250, 750)

        self.df = pd.DataFrame(columns=COLUNAS_PADRAO)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        top = QHBoxLayout()
        self.combo_formato = QComboBox()
        self.combo_formato.addItems(list(PARSERS.keys()))
        top.addWidget(QLabel("Formato do log:"))
        top.addWidget(self.combo_formato)
        btn_importar = QPushButton("Importar Arquivo(s) de Log...")
        btn_importar.clicked.connect(self.importar_logs)
        top.addWidget(btn_importar)
        btn_limpar = QPushButton("Limpar Dados")
        btn_limpar.clicked.connect(self.limpar_dados)
        top.addWidget(btn_limpar)
        layout.addLayout(top)

        filtro_row = QHBoxLayout()
        self.filtro_texto = QLineEdit(); self.filtro_texto.setPlaceholderText("Filtrar por origem/destino...")
        self.filtro_texto.textChanged.connect(self.atualizar_tabela)
        self.filtro_acao = QComboBox(); self.filtro_acao.addItems(["Todos", "PERMITIDO", "NEGADO"])
        self.filtro_acao.currentTextChanged.connect(self.atualizar_tabela)
        filtro_row.addWidget(self.filtro_texto)
        filtro_row.addWidget(self.filtro_acao)
        layout.addLayout(filtro_row)

        self.status_label = QLabel("Nenhum log carregado.")
        layout.addWidget(self.status_label)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUNAS_PADRAO))
        self.table.setHorizontalHeaderLabels(COLUNAS_PADRAO)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        tabs.addTab(self.table, "Eventos")

        self.anomalias_table = QTableWidget()
        self.anomalias_table.setColumnCount(3)
        self.anomalias_table.setHorizontalHeaderLabels(["Origem", "Tipo de Anomalia", "Detalhes"])
        self.anomalias_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        tabs.addTab(self.anomalias_table, "Anomalias Detectadas")

        self.resumo_table = QTableWidget()
        self.resumo_table.setColumnCount(2)
        self.resumo_table.setHorizontalHeaderLabels(["Métrica", "Valor"])
        tabs.addTab(self.resumo_table, "Resumo Estatístico")

        btn_exportar = QPushButton("Exportar Eventos Filtrados (CSV)")
        btn_exportar.clicked.connect(self.exportar_csv)
        layout.addWidget(btn_exportar)

    def importar_logs(self):
        formato = self.combo_formato.currentText()
        parser = PARSERS[formato]
        arquivos, _ = QFileDialog.getOpenFileNames(self, f"Selecionar arquivo(s) de log - {formato}")
        if not arquivos:
            return

        novos_dfs = []
        for arq in arquivos:
            try:
                df_novo = parser(arq)
                novos_dfs.append(df_novo)
            except (OSError, ValueError) as e:
                QMessageBox.warning(self, "Erro ao importar", f"Falha ao processar {arq}:\n{e}")

        if novos_dfs:
            self.df = pd.concat([self.df] + novos_dfs, ignore_index=True)
            self.status_label.setText(f"{len(self.df)} evento(s) carregado(s) no total.")
            self.atualizar_tabela()
            self.atualizar_anomalias()
            self.atualizar_resumo()
        else:
            QMessageBox.information(self, "Importar", "Nenhum evento reconhecido nos arquivos selecionados.")

    def limpar_dados(self):
        self.df = pd.DataFrame(columns=COLUNAS_PADRAO)
        self.status_label.setText("Nenhum log carregado.")
        self.atualizar_tabela()
        self.atualizar_anomalias()
        self.atualizar_resumo()

    def _df_filtrado(self):
        df = self.df
        texto = self.filtro_texto.text().strip().lower()
        acao = self.filtro_acao.currentText()
        if texto:
            mask = (
                df["origem"].astype(str).str.lower().str.contains(texto, na=False)
                | df["destino"].astype(str).str.lower().str.contains(texto, na=False)
            )
            df = df[mask]
        if acao != "Todos":
            df = df[df["acao"] == acao]
        return df

    def atualizar_tabela(self):
        df = self._df_filtrado()
        self.table.setRowCount(len(df))
        for i, (_, row) in enumerate(df.iterrows()):
            for j, col in enumerate(COLUNAS_PADRAO):
                item = QTableWidgetItem(str(row[col]) if pd.notna(row[col]) else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)

    def atualizar_anomalias(self):
        anomalias = detectar_anomalias(self.df)
        self.anomalias_table.setRowCount(len(anomalias))
        for i, (_, row) in enumerate(anomalias.iterrows()):
            for j, col in enumerate(["origem", "tipo_anomalia", "detalhes"]):
                item = QTableWidgetItem(str(row[col]))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col == "tipo_anomalia":
                    item.setBackground(Qt.yellow)
                self.anomalias_table.setItem(i, j, item)

    def atualizar_resumo(self):
        df = self.df
        total = len(df)
        negados = int((df["acao"] == "NEGADO").sum()) if total else 0
        permitidos = total - negados
        origens_unicas = df["origem"].nunique() if total else 0
        destinos_unicos = df["destino"].nunique() if total else 0
        top_origem = df["origem"].value_counts().idxmax() if total else "N/D"

        metricas = [
            ("Total de eventos", total),
            ("Permitidos", permitidos),
            ("Negados", negados),
            ("Origens únicas", origens_unicas),
            ("Destinos únicos", destinos_unicos),
            ("Origem mais frequente", top_origem),
        ]
        self.resumo_table.setRowCount(len(metricas))
        for i, (metrica, valor) in enumerate(metricas):
            self.resumo_table.setItem(i, 0, QTableWidgetItem(metrica))
            self.resumo_table.setItem(i, 1, QTableWidgetItem(str(valor)))

    def exportar_csv(self):
        if self.df.empty:
            QMessageBox.information(self, "Exportar", "Nenhum dado para exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar CSV", "eventos_filtrados.csv", "CSV (*.csv)")
        if not path:
            return
        self._df_filtrado().to_csv(path, index=False, encoding="utf-8")
        QMessageBox.information(self, "Exportar", f"Exportado para:\n{path}")


def main():
    app = QApplication(sys.argv)
    win = AnalisadorLogsWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
