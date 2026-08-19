"""
Gerenciador de Licenças de Software
Controla chaves, validade e quantidade de instalações permitidas por contrato.
Stack: Python + PyQt5 + SQLite
"""
import sys
import os
import sqlite3
import datetime
import csv

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QTabWidget, QLabel, QFileDialog, QHeaderView,
    QGroupBox, QTextEdit
)
from PyQt5.QtCore import QDate, Qt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "licencas.db")

TIPOS_LICENCA = ["Perpétua", "Assinatura Anual", "Assinatura Mensal", "Trial", "OEM"]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS licencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            software TEXT NOT NULL,
            fornecedor TEXT,
            chave_licenca TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Perpétua',
            contrato_numero TEXT,
            instalacoes_permitidas INTEGER NOT NULL DEFAULT 1,
            data_compra TEXT,
            data_validade TEXT,
            valor REAL DEFAULT 0,
            observacoes TEXT,
            criado_em TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS instalacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            licenca_id INTEGER NOT NULL,
            maquina TEXT NOT NULL,
            usuario TEXT,
            instalado_em TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (licenca_id) REFERENCES licencas(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def contar_instalacoes(licenca_id):
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM instalacoes WHERE licenca_id=?", (licenca_id,)).fetchone()["c"]
    conn.close()
    return n


def dias_para_vencer(data_validade_str):
    if not data_validade_str:
        return None
    try:
        data = datetime.datetime.strptime(data_validade_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (data - datetime.date.today()).days


class LicencaForm(QWidget):
    def __init__(self, on_save):
        super().__init__()
        self.on_save = on_save
        self.editing_id = None
        layout = QFormLayout(self)

        self.software = QLineEdit()
        self.fornecedor = QLineEdit()
        self.chave_licenca = QLineEdit()
        self.tipo = QComboBox(); self.tipo.addItems(TIPOS_LICENCA)
        self.contrato_numero = QLineEdit()
        self.instalacoes_permitidas = QSpinBox(); self.instalacoes_permitidas.setRange(1, 100000); self.instalacoes_permitidas.setValue(1)
        self.data_compra = QDateEdit(calendarPopup=True); self.data_compra.setDate(QDate.currentDate())
        self.data_validade = QDateEdit(calendarPopup=True); self.data_validade.setDate(QDate.currentDate().addYears(1))
        self.valor = QLineEdit(); self.valor.setPlaceholderText("0.00")
        self.observacoes = QTextEdit()

        layout.addRow("Software*:", self.software)
        layout.addRow("Fornecedor:", self.fornecedor)
        layout.addRow("Chave de Licença* (única):", self.chave_licenca)
        layout.addRow("Tipo:", self.tipo)
        layout.addRow("Nº do Contrato:", self.contrato_numero)
        layout.addRow("Instalações Permitidas:", self.instalacoes_permitidas)
        layout.addRow("Data de Compra:", self.data_compra)
        layout.addRow("Data de Validade:", self.data_validade)
        layout.addRow("Valor (R$):", self.valor)
        layout.addRow("Observações:", self.observacoes)

        btn_row = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar Licença")
        self.btn_limpar = QPushButton("Limpar")
        btn_row.addWidget(self.btn_salvar)
        btn_row.addWidget(self.btn_limpar)
        layout.addRow(btn_row)

        self.btn_salvar.clicked.connect(self._salvar)
        self.btn_limpar.clicked.connect(self.limpar)

    def limpar(self):
        self.editing_id = None
        self.software.clear(); self.fornecedor.clear(); self.chave_licenca.clear()
        self.contrato_numero.clear(); self.valor.clear(); self.observacoes.clear()
        self.tipo.setCurrentIndex(0)
        self.instalacoes_permitidas.setValue(1)
        self.data_compra.setDate(QDate.currentDate())
        self.data_validade.setDate(QDate.currentDate().addYears(1))

    def carregar(self, row):
        self.editing_id = row["id"]
        self.software.setText(row["software"] or "")
        self.fornecedor.setText(row["fornecedor"] or "")
        self.chave_licenca.setText(row["chave_licenca"] or "")
        self.tipo.setCurrentText(row["tipo"] or TIPOS_LICENCA[0])
        self.contrato_numero.setText(row["contrato_numero"] or "")
        self.instalacoes_permitidas.setValue(row["instalacoes_permitidas"] or 1)
        if row["data_compra"]:
            self.data_compra.setDate(QDate.fromString(row["data_compra"], "yyyy-MM-dd"))
        if row["data_validade"]:
            self.data_validade.setDate(QDate.fromString(row["data_validade"], "yyyy-MM-dd"))
        self.valor.setText(str(row["valor"] or 0))
        self.observacoes.setPlainText(row["observacoes"] or "")

    def _salvar(self):
        if not self.software.text().strip() or not self.chave_licenca.text().strip():
            QMessageBox.warning(self, "Validação", "Software e Chave de Licença são obrigatórios.")
            return
        try:
            valor = float(self.valor.text().replace(",", ".") or 0)
        except ValueError:
            QMessageBox.warning(self, "Validação", "Valor inválido.")
            return
        dados = dict(
            software=self.software.text().strip(),
            fornecedor=self.fornecedor.text().strip(),
            chave_licenca=self.chave_licenca.text().strip(),
            tipo=self.tipo.currentText(),
            contrato_numero=self.contrato_numero.text().strip(),
            instalacoes_permitidas=self.instalacoes_permitidas.value(),
            data_compra=self.data_compra.date().toString("yyyy-MM-dd"),
            data_validade=self.data_validade.date().toString("yyyy-MM-dd"),
            valor=valor,
            observacoes=self.observacoes.toPlainText().strip(),
        )
        try:
            conn = get_conn()
            if self.editing_id:
                dados["id"] = self.editing_id
                conn.execute("""
                    UPDATE licencas SET software=:software, fornecedor=:fornecedor, chave_licenca=:chave_licenca,
                    tipo=:tipo, contrato_numero=:contrato_numero, instalacoes_permitidas=:instalacoes_permitidas,
                    data_compra=:data_compra, data_validade=:data_validade, valor=:valor, observacoes=:observacoes
                    WHERE id=:id
                """, dados)
            else:
                conn.execute("""
                    INSERT INTO licencas (software, fornecedor, chave_licenca, tipo, contrato_numero,
                    instalacoes_permitidas, data_compra, data_validade, valor, observacoes)
                    VALUES (:software, :fornecedor, :chave_licenca, :tipo, :contrato_numero,
                    :instalacoes_permitidas, :data_compra, :data_validade, :valor, :observacoes)
                """, dados)
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Erro", "Já existe uma licença com esta chave.")
            return
        self.on_save()
        self.limpar()


class InstalacaoDialogWidget(QWidget):
    """Painel simples para registrar instalação de uma licença selecionada."""
    def __init__(self, get_selected_id, on_change):
        super().__init__()
        self.get_selected_id = get_selected_id
        self.on_change = on_change
        layout = QHBoxLayout(self)
        self.maquina = QLineEdit(); self.maquina.setPlaceholderText("Nome da máquina")
        self.usuario = QLineEdit(); self.usuario.setPlaceholderText("Usuário")
        btn = QPushButton("Registrar Instalação")
        btn.clicked.connect(self._registrar)
        layout.addWidget(self.maquina)
        layout.addWidget(self.usuario)
        layout.addWidget(btn)

    def _registrar(self):
        licenca_id = self.get_selected_id()
        if licenca_id is None:
            QMessageBox.information(self, "Instalação", "Selecione uma licença na tabela.")
            return
        if not self.maquina.text().strip():
            QMessageBox.warning(self, "Validação", "Informe o nome da máquina.")
            return
        conn = get_conn()
        row = conn.execute("SELECT instalacoes_permitidas FROM licencas WHERE id=?", (licenca_id,)).fetchone()
        atuais = conn.execute("SELECT COUNT(*) c FROM instalacoes WHERE licenca_id=?", (licenca_id,)).fetchone()["c"]
        if atuais >= row["instalacoes_permitidas"]:
            conn.close()
            QMessageBox.critical(self, "Limite excedido",
                                  "Número de instalações permitidas para esta licença já foi atingido.")
            return
        conn.execute("INSERT INTO instalacoes (licenca_id, maquina, usuario) VALUES (?, ?, ?)",
                     (licenca_id, self.maquina.text().strip(), self.usuario.text().strip()))
        conn.commit()
        conn.close()
        self.maquina.clear(); self.usuario.clear()
        self.on_change()


class LicencasWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador de Licenças de Software")
        self.resize(1150, 700)

        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        form_box = QGroupBox("Cadastro / Edição de Licença")
        form_layout = QVBoxLayout(form_box)
        self.form = LicencaForm(self.refresh_all)
        form_layout.addWidget(self.form)
        main_layout.addWidget(form_box, 1)

        right = QVBoxLayout()
        filtro_row = QHBoxLayout()
        self.filtro = QLineEdit(); self.filtro.setPlaceholderText("Buscar software / fornecedor / contrato...")
        self.filtro.textChanged.connect(self.refresh_table)
        filtro_row.addWidget(self.filtro)
        right.addLayout(filtro_row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Software", "Tipo", "Validade", "Dias p/ vencer",
            "Instalações (uso/permitido)", "Chave"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self.editar_selecionado)
        right.addWidget(self.table)

        self.instalacao_panel = InstalacaoDialogWidget(self._linha_selecionada_id, self.refresh_all)
        right.addWidget(self.instalacao_panel)

        btn_row = QHBoxLayout()
        btn_excluir = QPushButton("Excluir Licença")
        btn_excluir.clicked.connect(self.excluir_selecionado)
        btn_exportar = QPushButton("Exportar CSV")
        btn_exportar.clicked.connect(self.exportar_csv)
        btn_row.addWidget(btn_excluir)
        btn_row.addWidget(btn_exportar)
        right.addLayout(btn_row)

        main_layout.addLayout(right, 2)
        tabs.addTab(main_widget, "Licenças")

        alertas_widget = QWidget()
        alertas_layout = QVBoxLayout(alertas_widget)
        self.alertas_text = QTextEdit(); self.alertas_text.setReadOnly(True)
        alertas_layout.addWidget(QLabel("Licenças vencidas ou vencendo em 30 dias / limite de instalações atingido:"))
        alertas_layout.addWidget(self.alertas_text)
        btn_refresh = QPushButton("Atualizar Alertas")
        btn_refresh.clicked.connect(self.refresh_alertas)
        alertas_layout.addWidget(btn_refresh)
        tabs.addTab(alertas_widget, "Alertas")

        self.refresh_all()

    def _query(self):
        conn = get_conn()
        texto = self.filtro.text().strip().lower()
        query = "SELECT * FROM licencas WHERE 1=1"
        params = []
        if texto:
            query += " AND (LOWER(software) LIKE ? OR LOWER(fornecedor) LIKE ? OR LOWER(contrato_numero) LIKE ?)"
            like = f"%{texto}%"
            params += [like, like, like]
        query += " ORDER BY id DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return rows

    def refresh_all(self):
        self.refresh_table()
        self.refresh_alertas()

    def refresh_table(self):
        rows = self._query()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            uso = contar_instalacoes(row["id"])
            dias = dias_para_vencer(row["data_validade"])
            dias_str = "N/D" if dias is None else str(dias)
            valores = [
                str(row["id"]), row["software"], row["tipo"], row["data_validade"] or "",
                dias_str, f"{uso}/{row['instalacoes_permitidas']}", row["chave_licenca"]
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
        licenca_id = int(self.table.item(row_idx, 0).text())
        conn = get_conn()
        row = conn.execute("SELECT * FROM licencas WHERE id=?", (licenca_id,)).fetchone()
        conn.close()
        if row:
            self.form.carregar(row)

    def excluir_selecionado(self):
        licenca_id = self._linha_selecionada_id()
        if licenca_id is None:
            QMessageBox.information(self, "Excluir", "Selecione uma licença na tabela.")
            return
        if QMessageBox.question(self, "Confirmar", "Deseja excluir esta licença?") == QMessageBox.Yes:
            conn = get_conn()
            conn.execute("DELETE FROM licencas WHERE id=?", (licenca_id,))
            conn.commit()
            conn.close()
            self.refresh_all()

    def exportar_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar CSV", "licencas.csv", "CSV (*.csv)")
        if not path:
            return
        rows = self._query()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys() if rows else [])
            for row in rows:
                writer.writerow(list(row))
        QMessageBox.information(self, "Exportar", f"Exportado para:\n{path}")

    def refresh_alertas(self):
        conn = get_conn()
        rows = conn.execute("SELECT * FROM licencas").fetchall()
        conn.close()
        linhas = []
        for row in rows:
            dias = dias_para_vencer(row["data_validade"])
            if dias is not None and dias <= 30:
                estado = "VENCIDA" if dias < 0 else f"vence em {dias} dias"
                linhas.append(f"[{row['id']}] {row['software']} - validade {estado} ({row['data_validade']})")
            uso = contar_instalacoes(row["id"])
            if uso >= row["instalacoes_permitidas"]:
                linhas.append(f"[{row['id']}] {row['software']} - limite de instalações atingido ({uso}/{row['instalacoes_permitidas']})")
        self.alertas_text.setPlainText("\n".join(linhas) if linhas else "Nenhum alerta no momento.")


def main():
    init_db()
    app = QApplication(sys.argv)
    win = LicencasWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
