"""
Inventário de Ativos de TI Offline
Cadastro de hardware/software, ciclo de vida, garantia e depreciação.
Stack: Python + PyQt5 + SQLite
"""
import sys
import os
import sqlite3
import datetime
import csv

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QTabWidget, QLabel,
    QTextEdit, QFileDialog, QHeaderView, QGroupBox
)
from PyQt5.QtCore import QDate, Qt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventario.db")

TIPOS_ATIVO = ["Hardware", "Software", "Periférico", "Licença", "Rede"]
STATUS_ATIVO = ["Em uso", "Em estoque", "Em manutenção", "Descartado", "Emprestado"]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ativos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            fabricante TEXT,
            modelo TEXT,
            numero_serie TEXT UNIQUE,
            responsavel TEXT,
            localizacao TEXT,
            status TEXT NOT NULL DEFAULT 'Em uso',
            data_aquisicao TEXT,
            valor_aquisicao REAL DEFAULT 0,
            vida_util_anos INTEGER DEFAULT 3,
            garantia_ate TEXT,
            observacoes TEXT,
            criado_em TEXT DEFAULT (datetime('now'))
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo_id INTEGER NOT NULL,
            evento TEXT NOT NULL,
            detalhes TEXT,
            data TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ativo_id) REFERENCES ativos(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def registrar_historico(ativo_id, evento, detalhes=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO historico (ativo_id, evento, detalhes) VALUES (?, ?, ?)",
        (ativo_id, evento, detalhes),
    )
    conn.commit()
    conn.close()


def calcular_depreciacao(valor_aquisicao, data_aquisicao_str, vida_util_anos):
    """Depreciação linear simples. Retorna (valor_atual, percentual_depreciado)."""
    if not valor_aquisicao or not data_aquisicao_str or not vida_util_anos:
        return 0.0, 0.0
    try:
        data_aq = datetime.datetime.strptime(data_aquisicao_str, "%Y-%m-%d").date()
    except ValueError:
        return valor_aquisicao, 0.0
    hoje = datetime.date.today()
    dias_passados = (hoje - data_aq).days
    dias_vida_util = vida_util_anos * 365
    if dias_vida_util <= 0:
        return 0.0, 100.0
    fracao = min(max(dias_passados / dias_vida_util, 0.0), 1.0)
    valor_atual = valor_aquisicao * (1 - fracao)
    return round(valor_atual, 2), round(fracao * 100, 2)


class AtivoForm(QWidget):
    def __init__(self, on_save):
        super().__init__()
        self.on_save = on_save
        self.editing_id = None
        layout = QFormLayout(self)

        self.nome = QLineEdit()
        self.tipo = QComboBox(); self.tipo.addItems(TIPOS_ATIVO)
        self.fabricante = QLineEdit()
        self.modelo = QLineEdit()
        self.numero_serie = QLineEdit()
        self.responsavel = QLineEdit()
        self.localizacao = QLineEdit()
        self.status = QComboBox(); self.status.addItems(STATUS_ATIVO)
        self.data_aquisicao = QDateEdit(calendarPopup=True); self.data_aquisicao.setDate(QDate.currentDate())
        self.valor_aquisicao = QDoubleSpinBox(); self.valor_aquisicao.setMaximum(10_000_000); self.valor_aquisicao.setPrefix("R$ ")
        self.vida_util_anos = QSpinBox(); self.vida_util_anos.setRange(1, 30); self.vida_util_anos.setValue(3)
        self.garantia_ate = QDateEdit(calendarPopup=True); self.garantia_ate.setDate(QDate.currentDate().addYears(1))
        self.observacoes = QTextEdit()

        layout.addRow("Nome*:", self.nome)
        layout.addRow("Tipo:", self.tipo)
        layout.addRow("Fabricante:", self.fabricante)
        layout.addRow("Modelo:", self.modelo)
        layout.addRow("Nº de Série (único):", self.numero_serie)
        layout.addRow("Responsável:", self.responsavel)
        layout.addRow("Localização:", self.localizacao)
        layout.addRow("Status:", self.status)
        layout.addRow("Data de Aquisição:", self.data_aquisicao)
        layout.addRow("Valor de Aquisição:", self.valor_aquisicao)
        layout.addRow("Vida Útil (anos):", self.vida_util_anos)
        layout.addRow("Garantia até:", self.garantia_ate)
        layout.addRow("Observações:", self.observacoes)

        btn_row = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar Ativo")
        self.btn_limpar = QPushButton("Limpar")
        btn_row.addWidget(self.btn_salvar)
        btn_row.addWidget(self.btn_limpar)
        layout.addRow(btn_row)

        self.btn_salvar.clicked.connect(self._salvar)
        self.btn_limpar.clicked.connect(self.limpar)

    def limpar(self):
        self.editing_id = None
        self.nome.clear(); self.fabricante.clear(); self.modelo.clear()
        self.numero_serie.clear(); self.responsavel.clear(); self.localizacao.clear()
        self.observacoes.clear()
        self.tipo.setCurrentIndex(0); self.status.setCurrentIndex(0)
        self.data_aquisicao.setDate(QDate.currentDate())
        self.garantia_ate.setDate(QDate.currentDate().addYears(1))
        self.valor_aquisicao.setValue(0)
        self.vida_util_anos.setValue(3)

    def carregar(self, row):
        self.editing_id = row["id"]
        self.nome.setText(row["nome"] or "")
        self.tipo.setCurrentText(row["tipo"] or TIPOS_ATIVO[0])
        self.fabricante.setText(row["fabricante"] or "")
        self.modelo.setText(row["modelo"] or "")
        self.numero_serie.setText(row["numero_serie"] or "")
        self.responsavel.setText(row["responsavel"] or "")
        self.localizacao.setText(row["localizacao"] or "")
        self.status.setCurrentText(row["status"] or STATUS_ATIVO[0])
        if row["data_aquisicao"]:
            self.data_aquisicao.setDate(QDate.fromString(row["data_aquisicao"], "yyyy-MM-dd"))
        self.valor_aquisicao.setValue(row["valor_aquisicao"] or 0)
        self.vida_util_anos.setValue(row["vida_util_anos"] or 3)
        if row["garantia_ate"]:
            self.garantia_ate.setDate(QDate.fromString(row["garantia_ate"], "yyyy-MM-dd"))
        self.observacoes.setPlainText(row["observacoes"] or "")

    def _salvar(self):
        if not self.nome.text().strip():
            QMessageBox.warning(self, "Validação", "O campo Nome é obrigatório.")
            return
        dados = dict(
            nome=self.nome.text().strip(),
            tipo=self.tipo.currentText(),
            fabricante=self.fabricante.text().strip(),
            modelo=self.modelo.text().strip(),
            numero_serie=self.numero_serie.text().strip() or None,
            responsavel=self.responsavel.text().strip(),
            localizacao=self.localizacao.text().strip(),
            status=self.status.currentText(),
            data_aquisicao=self.data_aquisicao.date().toString("yyyy-MM-dd"),
            valor_aquisicao=self.valor_aquisicao.value(),
            vida_util_anos=self.vida_util_anos.value(),
            garantia_ate=self.garantia_ate.date().toString("yyyy-MM-dd"),
            observacoes=self.observacoes.toPlainText().strip(),
        )
        try:
            conn = get_conn()
            if self.editing_id:
                dados["id"] = self.editing_id
                conn.execute("""
                    UPDATE ativos SET nome=:nome, tipo=:tipo, fabricante=:fabricante, modelo=:modelo,
                    numero_serie=:numero_serie, responsavel=:responsavel, localizacao=:localizacao,
                    status=:status, data_aquisicao=:data_aquisicao, valor_aquisicao=:valor_aquisicao,
                    vida_util_anos=:vida_util_anos, garantia_ate=:garantia_ate, observacoes=:observacoes
                    WHERE id=:id
                """, dados)
                conn.commit()
                registrar_historico(self.editing_id, "Atualização", "Ativo atualizado via formulário")
            else:
                cur = conn.execute("""
                    INSERT INTO ativos (nome, tipo, fabricante, modelo, numero_serie, responsavel,
                    localizacao, status, data_aquisicao, valor_aquisicao, vida_util_anos, garantia_ate, observacoes)
                    VALUES (:nome, :tipo, :fabricante, :modelo, :numero_serie, :responsavel, :localizacao,
                    :status, :data_aquisicao, :valor_aquisicao, :vida_util_anos, :garantia_ate, :observacoes)
                """, dados)
                conn.commit()
                registrar_historico(cur.lastrowid, "Cadastro", "Ativo cadastrado")
            conn.close()
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Erro", "Já existe um ativo com este número de série.")
            return
        self.on_save()
        self.limpar()


class InventarioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventário de Ativos de TI Offline")
        self.resize(1100, 700)

        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        cadastro_widget = QWidget()
        cadastro_layout = QHBoxLayout(cadastro_widget)
        self.form = AtivoForm(self.refresh_table)
        form_box = QGroupBox("Cadastro / Edição de Ativo")
        form_box_layout = QVBoxLayout(form_box)
        form_box_layout.addWidget(self.form)
        cadastro_layout.addWidget(form_box, 1)

        right_panel = QVBoxLayout()
        filtro_row = QHBoxLayout()
        self.filtro_texto = QLineEdit(); self.filtro_texto.setPlaceholderText("Buscar por nome, série, responsável...")
        self.filtro_texto.textChanged.connect(self.refresh_table)
        self.filtro_status = QComboBox(); self.filtro_status.addItems(["Todos"] + STATUS_ATIVO)
        self.filtro_status.currentTextChanged.connect(self.refresh_table)
        filtro_row.addWidget(self.filtro_texto)
        filtro_row.addWidget(self.filtro_status)
        right_panel.addLayout(filtro_row)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nome", "Tipo", "Nº Série", "Responsável", "Status",
            "Garantia até", "Valor Atual (Deprec.)", "% Depreciado"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self.editar_selecionado)
        right_panel.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_excluir = QPushButton("Excluir Selecionado")
        btn_excluir.clicked.connect(self.excluir_selecionado)
        btn_exportar = QPushButton("Exportar CSV")
        btn_exportar.clicked.connect(self.exportar_csv)
        btn_row.addWidget(btn_excluir)
        btn_row.addWidget(btn_exportar)
        right_panel.addLayout(btn_row)

        cadastro_layout.addLayout(right_panel, 2)
        tabs.addTab(cadastro_widget, "Ativos")

        alertas_widget = QWidget()
        alertas_layout = QVBoxLayout(alertas_widget)
        self.alertas_text = QTextEdit(); self.alertas_text.setReadOnly(True)
        alertas_layout.addWidget(QLabel("Ativos com garantia vencendo em 30 dias ou já vencida:"))
        alertas_layout.addWidget(self.alertas_text)
        btn_refresh_alertas = QPushButton("Atualizar Alertas")
        btn_refresh_alertas.clicked.connect(self.refresh_alertas)
        alertas_layout.addWidget(btn_refresh_alertas)
        tabs.addTab(alertas_widget, "Alertas de Garantia")

        hist_widget = QWidget()
        hist_layout = QVBoxLayout(hist_widget)
        self.hist_table = QTableWidget()
        self.hist_table.setColumnCount(4)
        self.hist_table.setHorizontalHeaderLabels(["Ativo ID", "Evento", "Detalhes", "Data"])
        self.hist_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        hist_layout.addWidget(self.hist_table)
        btn_refresh_hist = QPushButton("Atualizar Histórico")
        btn_refresh_hist.clicked.connect(self.refresh_historico)
        hist_layout.addWidget(btn_refresh_hist)
        tabs.addTab(hist_widget, "Histórico")

        self.refresh_table()
        self.refresh_alertas()
        self.refresh_historico()

    def _query_ativos(self):
        conn = get_conn()
        texto = self.filtro_texto.text().strip().lower()
        status = self.filtro_status.currentText()
        query = "SELECT * FROM ativos WHERE 1=1"
        params = []
        if texto:
            query += " AND (LOWER(nome) LIKE ? OR LOWER(numero_serie) LIKE ? OR LOWER(responsavel) LIKE ?)"
            like = f"%{texto}%"
            params += [like, like, like]
        if status != "Todos":
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY id DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return rows

    def refresh_table(self):
        rows = self._query_ativos()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            valor_atual, pct = calcular_depreciacao(row["valor_aquisicao"], row["data_aquisicao"], row["vida_util_anos"])
            valores = [
                str(row["id"]), row["nome"], row["tipo"], row["numero_serie"] or "",
                row["responsavel"] or "", row["status"], row["garantia_ate"] or "",
                f"R$ {valor_atual:.2f}", f"{pct:.1f}%"
            ]
            for j, val in enumerate(valores):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)

    def _linha_selecionada_id(self):
        sel = self.table.selectedItems()
        if not sel:
            return None
        return int(self.table.item(sel[0].row(), 0).text())

    def editar_selecionado(self, row_idx, _col):
        ativo_id = int(self.table.item(row_idx, 0).text())
        conn = get_conn()
        row = conn.execute("SELECT * FROM ativos WHERE id=?", (ativo_id,)).fetchone()
        conn.close()
        if row:
            self.form.carregar(row)

    def excluir_selecionado(self):
        ativo_id = self._linha_selecionada_id()
        if ativo_id is None:
            QMessageBox.information(self, "Excluir", "Selecione um ativo na tabela.")
            return
        confirm = QMessageBox.question(self, "Confirmar", "Deseja realmente excluir este ativo?")
        if confirm == QMessageBox.Yes:
            conn = get_conn()
            conn.execute("DELETE FROM ativos WHERE id=?", (ativo_id,))
            conn.commit()
            conn.close()
            self.refresh_table()
            self.refresh_historico()

    def exportar_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar CSV", "inventario.csv", "CSV (*.csv)")
        if not path:
            return
        rows = self._query_ativos()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys() if rows else [])
            for row in rows:
                writer.writerow(list(row))
        QMessageBox.information(self, "Exportar", f"Exportado com sucesso para:\n{path}")

    def refresh_alertas(self):
        conn = get_conn()
        rows = conn.execute("SELECT * FROM ativos WHERE garantia_ate IS NOT NULL").fetchall()
        conn.close()
        hoje = datetime.date.today()
        linhas = []
        for row in rows:
            try:
                garantia = datetime.datetime.strptime(row["garantia_ate"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            dias = (garantia - hoje).days
            if dias <= 30:
                estado = "VENCIDA" if dias < 0 else f"vence em {dias} dias"
                linhas.append(f"[{row['id']}] {row['nome']} ({row['numero_serie'] or 's/n'}) - garantia {estado} ({row['garantia_ate']})")
        self.alertas_text.setPlainText("\n".join(linhas) if linhas else "Nenhum alerta de garantia no momento.")

    def refresh_historico(self):
        conn = get_conn()
        rows = conn.execute("SELECT * FROM historico ORDER BY data DESC LIMIT 500").fetchall()
        conn.close()
        self.hist_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate([str(row["ativo_id"]), row["evento"], row["detalhes"] or "", row["data"]]):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.hist_table.setItem(i, j, item)


def main():
    init_db()
    app = QApplication(sys.argv)
    win = InventarioWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
