"""
Gestor de Change Management (RFC interno)
Fluxo de aprovação de mudanças de TI com trilha de auditoria local.
Stack: Python + PyQt5 + SQLite
"""
import sys
import os
import sqlite3
import datetime
import csv

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QTabWidget, QLabel, QFileDialog, QHeaderView, QGroupBox, QDateEdit
)
from PyQt5.QtCore import QDate, Qt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "changes.db")

TIPOS_MUDANCA = ["Normal", "Emergencial", "Padrão (pré-aprovada)"]
RISCOS = ["Baixo", "Médio", "Alto"]

# Fluxo de estados do RFC (Request for Change)
ESTADOS = ["Rascunho", "Em Análise", "Aprovada", "Rejeitada", "Em Implementação", "Concluída", "Cancelada"]

TRANSICOES_PERMITIDAS = {
    "Rascunho": ["Em Análise", "Cancelada"],
    "Em Análise": ["Aprovada", "Rejeitada", "Cancelada"],
    "Aprovada": ["Em Implementação", "Cancelada"],
    "Rejeitada": ["Rascunho", "Cancelada"],
    "Em Implementação": ["Concluída", "Rejeitada"],
    "Concluída": [],
    "Cancelada": [],
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rfcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            solicitante TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Normal',
            risco TEXT NOT NULL DEFAULT 'Médio',
            sistemas_afetados TEXT,
            plano_rollback TEXT,
            data_planejada TEXT,
            estado TEXT NOT NULL DEFAULT 'Rascunho',
            aprovador TEXT,
            criado_em TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfc_id INTEGER NOT NULL,
            evento TEXT NOT NULL,
            detalhes TEXT,
            usuario TEXT,
            data TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (rfc_id) REFERENCES rfcs(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def registrar_auditoria(rfc_id, evento, detalhes="", usuario="sistema"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO auditoria (rfc_id, evento, detalhes, usuario) VALUES (?, ?, ?, ?)",
        (rfc_id, evento, detalhes, usuario),
    )
    conn.commit()
    conn.close()


class RFCForm(QWidget):
    def __init__(self, on_save):
        super().__init__()
        self.on_save = on_save
        self.editing_id = None
        layout = QFormLayout(self)

        self.titulo = QLineEdit()
        self.solicitante = QLineEdit()
        self.tipo = QComboBox(); self.tipo.addItems(TIPOS_MUDANCA)
        self.risco = QComboBox(); self.risco.addItems(RISCOS)
        self.sistemas_afetados = QLineEdit()
        self.data_planejada = QDateEdit(calendarPopup=True); self.data_planejada.setDate(QDate.currentDate().addDays(7))
        self.descricao = QTextEdit()
        self.plano_rollback = QTextEdit()

        layout.addRow("Título*:", self.titulo)
        layout.addRow("Solicitante*:", self.solicitante)
        layout.addRow("Tipo:", self.tipo)
        layout.addRow("Risco:", self.risco)
        layout.addRow("Sistemas Afetados:", self.sistemas_afetados)
        layout.addRow("Data Planejada:", self.data_planejada)
        layout.addRow("Descrição:", self.descricao)
        layout.addRow("Plano de Rollback:", self.plano_rollback)

        btn_row = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar RFC (Rascunho)")
        self.btn_limpar = QPushButton("Limpar")
        btn_row.addWidget(self.btn_salvar)
        btn_row.addWidget(self.btn_limpar)
        layout.addRow(btn_row)

        self.btn_salvar.clicked.connect(self._salvar)
        self.btn_limpar.clicked.connect(self.limpar)

    def limpar(self):
        self.editing_id = None
        self.titulo.clear(); self.solicitante.clear(); self.sistemas_afetados.clear()
        self.descricao.clear(); self.plano_rollback.clear()
        self.tipo.setCurrentIndex(0); self.risco.setCurrentIndex(1)
        self.data_planejada.setDate(QDate.currentDate().addDays(7))

    def carregar(self, row):
        self.editing_id = row["id"]
        self.titulo.setText(row["titulo"] or "")
        self.solicitante.setText(row["solicitante"] or "")
        self.tipo.setCurrentText(row["tipo"] or TIPOS_MUDANCA[0])
        self.risco.setCurrentText(row["risco"] or RISCOS[1])
        self.sistemas_afetados.setText(row["sistemas_afetados"] or "")
        if row["data_planejada"]:
            self.data_planejada.setDate(QDate.fromString(row["data_planejada"], "yyyy-MM-dd"))
        self.descricao.setPlainText(row["descricao"] or "")
        self.plano_rollback.setPlainText(row["plano_rollback"] or "")

    def _salvar(self):
        if not self.titulo.text().strip() or not self.solicitante.text().strip():
            QMessageBox.warning(self, "Validação", "Título e Solicitante são obrigatórios.")
            return
        if not self.plano_rollback.toPlainText().strip():
            QMessageBox.warning(self, "Validação", "Plano de Rollback é obrigatório para qualquer mudança.")
            return

        dados = dict(
            titulo=self.titulo.text().strip(),
            descricao=self.descricao.toPlainText().strip(),
            solicitante=self.solicitante.text().strip(),
            tipo=self.tipo.currentText(),
            risco=self.risco.currentText(),
            sistemas_afetados=self.sistemas_afetados.text().strip(),
            plano_rollback=self.plano_rollback.toPlainText().strip(),
            data_planejada=self.data_planejada.date().toString("yyyy-MM-dd"),
        )
        conn = get_conn()
        if self.editing_id:
            dados["id"] = self.editing_id
            conn.execute("""
                UPDATE rfcs SET titulo=:titulo, descricao=:descricao, solicitante=:solicitante,
                tipo=:tipo, risco=:risco, sistemas_afetados=:sistemas_afetados,
                plano_rollback=:plano_rollback, data_planejada=:data_planejada
                WHERE id=:id
            """, dados)
            conn.commit()
            conn.close()
            registrar_auditoria(self.editing_id, "Atualização", "RFC atualizada via formulário", dados["solicitante"])
        else:
            cur = conn.execute("""
                INSERT INTO rfcs (titulo, descricao, solicitante, tipo, risco, sistemas_afetados,
                plano_rollback, data_planejada)
                VALUES (:titulo, :descricao, :solicitante, :tipo, :risco, :sistemas_afetados,
                :plano_rollback, :data_planejada)
            """, dados)
            conn.commit()
            rfc_id = cur.lastrowid
            conn.close()
            registrar_auditoria(rfc_id, "Criação", "RFC criada em estado Rascunho", dados["solicitante"])
        self.on_save()
        self.limpar()


class RFCWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor de Change Management (RFC)")
        self.resize(1250, 750)

        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        form_box = QGroupBox("Nova RFC / Edição (somente em Rascunho)")
        form_layout = QVBoxLayout(form_box)
        self.form = RFCForm(self.refresh_all)
        form_layout.addWidget(self.form)
        main_layout.addWidget(form_box, 1)

        right = QVBoxLayout()

        filtro_row = QHBoxLayout()
        self.filtro = QLineEdit(); self.filtro.setPlaceholderText("Buscar por título / solicitante / sistema...")
        self.filtro.textChanged.connect(self.refresh_table)
        self.filtro_estado = QComboBox(); self.filtro_estado.addItems(["Todos"] + ESTADOS)
        self.filtro_estado.currentTextChanged.connect(self.refresh_table)
        filtro_row.addWidget(self.filtro)
        filtro_row.addWidget(self.filtro_estado)
        right.addLayout(filtro_row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Título", "Tipo", "Risco", "Estado", "Solicitante", "Data Planejada"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self.editar_selecionado)
        right.addWidget(self.table)

        transicao_box = QGroupBox("Fluxo de Aprovação")
        transicao_layout = QHBoxLayout(transicao_box)
        self.combo_transicao = QComboBox()
        self.aprovador_edit = QLineEdit(); self.aprovador_edit.setPlaceholderText("Nome de quem está aplicando a transição")
        self.comentario_edit = QLineEdit(); self.comentario_edit.setPlaceholderText("Comentário/justificativa")
        btn_transicionar = QPushButton("Aplicar Transição")
        btn_transicionar.clicked.connect(self.aplicar_transicao)
        transicao_layout.addWidget(self.combo_transicao)
        transicao_layout.addWidget(self.aprovador_edit)
        transicao_layout.addWidget(self.comentario_edit)
        transicao_layout.addWidget(btn_transicionar)
        right.addWidget(transicao_box)

        self.table.itemSelectionChanged.connect(self.atualizar_transicoes_disponiveis)

        btn_row = QHBoxLayout()
        btn_excluir = QPushButton("Excluir RFC (somente Rascunho/Cancelada)")
        btn_excluir.clicked.connect(self.excluir_selecionado)
        btn_exportar = QPushButton("Exportar CSV")
        btn_exportar.clicked.connect(self.exportar_csv)
        btn_row.addWidget(btn_excluir)
        btn_row.addWidget(btn_exportar)
        right.addLayout(btn_row)

        main_layout.addLayout(right, 2)
        tabs.addTab(main_widget, "RFCs")

        # Aba trilha de auditoria
        audit_widget = QWidget()
        audit_layout = QVBoxLayout(audit_widget)
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(5)
        self.audit_table.setHorizontalHeaderLabels(["RFC ID", "Evento", "Detalhes", "Usuário", "Data"])
        self.audit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        audit_layout.addWidget(self.audit_table)
        btn_refresh_audit = QPushButton("Atualizar Trilha de Auditoria")
        btn_refresh_audit.clicked.connect(self.refresh_auditoria)
        audit_layout.addWidget(btn_refresh_audit)
        tabs.addTab(audit_widget, "Trilha de Auditoria")

        self.refresh_all()

    def _query(self):
        conn = get_conn()
        texto = self.filtro.text().strip().lower()
        estado = self.filtro_estado.currentText()
        query = "SELECT * FROM rfcs WHERE 1=1"
        params = []
        if texto:
            query += " AND (LOWER(titulo) LIKE ? OR LOWER(solicitante) LIKE ? OR LOWER(sistemas_afetados) LIKE ?)"
            like = f"%{texto}%"
            params += [like, like, like]
        if estado != "Todos":
            query += " AND estado = ?"
            params.append(estado)
        query += " ORDER BY id DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return rows

    def refresh_all(self):
        self.refresh_table()
        self.refresh_auditoria()

    def refresh_table(self):
        rows = self._query()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            valores = [
                str(row["id"]), row["titulo"], row["tipo"], row["risco"],
                row["estado"], row["solicitante"], row["data_planejada"] or ""
            ]
            for j, val in enumerate(valores):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)
        self.atualizar_transicoes_disponiveis()

    def _linha_selecionada(self):
        sel = self.table.selectedItems()
        if not sel:
            return None
        row_idx = sel[0].row()
        rfc_id = int(self.table.item(row_idx, 0).text())
        conn = get_conn()
        row = conn.execute("SELECT * FROM rfcs WHERE id=?", (rfc_id,)).fetchone()
        conn.close()
        return row

    def editar_selecionado(self, row_idx, _col):
        rfc_id = int(self.table.item(row_idx, 0).text())
        conn = get_conn()
        row = conn.execute("SELECT * FROM rfcs WHERE id=?", (rfc_id,)).fetchone()
        conn.close()
        if row and row["estado"] == "Rascunho":
            self.form.carregar(row)
        elif row:
            QMessageBox.information(self, "Edição bloqueada",
                                     "Apenas RFCs em estado 'Rascunho' podem ser editadas diretamente.\n"
                                     "Use o fluxo de transição de estados abaixo da tabela.")

    def atualizar_transicoes_disponiveis(self):
        self.combo_transicao.clear()
        row = self._linha_selecionada()
        if row is None:
            return
        destinos = TRANSICOES_PERMITIDAS.get(row["estado"], [])
        self.combo_transicao.addItems(destinos if destinos else ["(estado final - sem transições)"])

    def aplicar_transicao(self):
        row = self._linha_selecionada()
        if row is None:
            QMessageBox.information(self, "Transição", "Selecione uma RFC na tabela.")
            return
        destino = self.combo_transicao.currentText()
        permitidos = TRANSICOES_PERMITIDAS.get(row["estado"], [])
        if destino not in permitidos:
            QMessageBox.critical(self, "Transição inválida",
                                  f"Não é possível transicionar de '{row['estado']}' para '{destino}'.")
            return
        if not self.aprovador_edit.text().strip():
            QMessageBox.warning(self, "Validação", "Informe o nome de quem está aplicando a transição.")
            return
        if destino == "Aprovada" and row["risco"] == "Alto" and not self.comentario_edit.text().strip():
            QMessageBox.warning(self, "Validação",
                                 "Mudanças de risco Alto exigem justificativa/comentário para aprovação.")
            return

        conn = get_conn()
        aprovador = self.aprovador_edit.text().strip()
        campos_extra = ", aprovador=:aprovador" if destino == "Aprovada" else ""
        conn.execute(f"UPDATE rfcs SET estado=:estado{campos_extra} WHERE id=:id",
                     {"estado": destino, "id": row["id"], "aprovador": aprovador})
        conn.commit()
        conn.close()
        detalhes = self.comentario_edit.text().strip() or f"Transição para {destino}"
        registrar_auditoria(row["id"], f"Transição: {row['estado']} -> {destino}", detalhes, aprovador)

        self.aprovador_edit.clear()
        self.comentario_edit.clear()
        self.refresh_all()

    def excluir_selecionado(self):
        row = self._linha_selecionada()
        if row is None:
            QMessageBox.information(self, "Excluir", "Selecione uma RFC na tabela.")
            return
        if row["estado"] not in ("Rascunho", "Cancelada"):
            QMessageBox.critical(self, "Bloqueado",
                                  "Só é possível excluir RFCs em estado Rascunho ou Cancelada (trilha de auditoria preservada para as demais).")
            return
        if QMessageBox.question(self, "Confirmar", "Deseja excluir esta RFC?") == QMessageBox.Yes:
            conn = get_conn()
            conn.execute("DELETE FROM rfcs WHERE id=?", (row["id"],))
            conn.commit()
            conn.close()
            self.refresh_all()

    def exportar_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar CSV", "rfcs.csv", "CSV (*.csv)")
        if not path:
            return
        rows = self._query()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys() if rows else [])
            for row in rows:
                writer.writerow(list(row))
        QMessageBox.information(self, "Exportar", f"Exportado para:\n{path}")

    def refresh_auditoria(self):
        conn = get_conn()
        rows = conn.execute("SELECT * FROM auditoria ORDER BY data DESC LIMIT 1000").fetchall()
        conn.close()
        self.audit_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            valores = [str(row["rfc_id"]), row["evento"], row["detalhes"] or "", row["usuario"] or "", row["data"]]
            for j, val in enumerate(valores):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.audit_table.setItem(i, j, item)


def main():
    init_db()
    app = QApplication(sys.argv)
    win = RFCWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
