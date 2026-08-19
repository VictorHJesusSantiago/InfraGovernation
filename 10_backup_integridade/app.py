"""
Controlador de Backup Local com Verificação de Integridade
Agenda backups, calcula hash e valida restauração.
Stack: Python + Tkinter + hashlib
"""
import os
import sys
import json
import shutil
import hashlib
import zipfile
import datetime
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup_config.json")
HASHES_DIRNAME = "_hashes"


def calcular_hash_arquivo(caminho, algoritmo="sha256", bloco=65536):
    h = hashlib.new(algoritmo)
    with open(caminho, "rb") as f:
        while True:
            dados = f.read(bloco)
            if not dados:
                break
            h.update(dados)
    return h.hexdigest()


def gerar_manifesto_hashes(pasta_origem, algoritmo="sha256"):
    """Gera um dicionário {caminho_relativo: hash} para todos os arquivos da pasta."""
    manifesto = {}
    for raiz, _dirs, arquivos in os.walk(pasta_origem):
        for nome in arquivos:
            caminho_abs = os.path.join(raiz, nome)
            caminho_rel = os.path.relpath(caminho_abs, pasta_origem)
            manifesto[caminho_rel] = calcular_hash_arquivo(caminho_abs, algoritmo)
    return manifesto


def executar_backup(pasta_origem, pasta_destino, algoritmo="sha256", log_callback=None):
    """Executa um backup completo: copia arquivos para um .zip com timestamp e grava
    manifesto de hashes ao lado, para validação de integridade posterior."""
    def log(msg):
        if log_callback:
            log_callback(msg)

    if not os.path.isdir(pasta_origem):
        raise FileNotFoundError(f"Pasta de origem não encontrada: {pasta_origem}")
    os.makedirs(pasta_destino, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_base = os.path.basename(os.path.normpath(pasta_origem))
    nome_zip = f"{nome_base}_{timestamp}.zip"
    caminho_zip = os.path.join(pasta_destino, nome_zip)

    log(f"Calculando hashes de integridade dos arquivos de origem ({algoritmo})...")
    manifesto = gerar_manifesto_hashes(pasta_origem, algoritmo)
    log(f"{len(manifesto)} arquivo(s) mapeado(s).")

    log(f"Compactando para: {caminho_zip}")
    with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for caminho_rel in manifesto:
            caminho_abs = os.path.join(pasta_origem, caminho_rel)
            zf.write(caminho_abs, caminho_rel)

    hashes_dir = os.path.join(pasta_destino, HASHES_DIRNAME)
    os.makedirs(hashes_dir, exist_ok=True)
    manifesto_path = os.path.join(hashes_dir, f"{nome_zip}.manifest.json")
    with open(manifesto_path, "w", encoding="utf-8") as f:
        json.dump({
            "origem": pasta_origem,
            "zip": nome_zip,
            "algoritmo": algoritmo,
            "criado_em": datetime.datetime.now().isoformat(),
            "arquivos": manifesto,
        }, f, indent=2, ensure_ascii=False)

    log(f"Backup concluído: {caminho_zip}")
    log(f"Manifesto de integridade salvo em: {manifesto_path}")
    return caminho_zip, manifesto_path


def validar_restauracao(caminho_zip, manifesto_path, pasta_restauracao=None, log_callback=None):
    """Extrai (em pasta temporária ou informada) e recalcula hashes, comparando com o
    manifesto original. Retorna (ok: bool, divergencias: list)."""
    def log(msg):
        if log_callback:
            log_callback(msg)

    with open(manifesto_path, "r", encoding="utf-8") as f:
        manifesto_original = json.load(f)

    algoritmo = manifesto_original["algoritmo"]
    arquivos_originais = manifesto_original["arquivos"]

    pasta_temp_criada = False
    if pasta_restauracao is None:
        pasta_restauracao = caminho_zip + "_restaurado_tmp"
        pasta_temp_criada = True

    if os.path.isdir(pasta_restauracao):
        shutil.rmtree(pasta_restauracao)
    os.makedirs(pasta_restauracao, exist_ok=True)

    log(f"Extraindo {caminho_zip} para {pasta_restauracao}...")
    with zipfile.ZipFile(caminho_zip, "r") as zf:
        zf.extractall(pasta_restauracao)

    divergencias = []
    for caminho_rel, hash_original in arquivos_originais.items():
        caminho_abs = os.path.join(pasta_restauracao, caminho_rel)
        if not os.path.isfile(caminho_abs):
            divergencias.append(f"AUSENTE: {caminho_rel}")
            continue
        hash_atual = calcular_hash_arquivo(caminho_abs, algoritmo)
        if hash_atual != hash_original:
            divergencias.append(f"HASH DIVERGENTE: {caminho_rel}")

    arquivos_extraidos = set()
    for raiz, _dirs, arquivos in os.walk(pasta_restauracao):
        for nome in arquivos:
            caminho_abs = os.path.join(raiz, nome)
            arquivos_extraidos.add(os.path.relpath(caminho_abs, pasta_restauracao))
    extras = arquivos_extraidos - set(arquivos_originais.keys())
    for extra in extras:
        divergencias.append(f"ARQUIVO INESPERADO: {extra}")

    if pasta_temp_criada:
        shutil.rmtree(pasta_restauracao, ignore_errors=True)

    ok = len(divergencias) == 0
    log("Validação concluída: " + ("ÍNTEGRO" if ok else f"{len(divergencias)} divergência(s) encontrada(s)"))
    return ok, divergencias


class BackupApp:
    def __init__(self, root):
        self.root = root
        root.title("Controlador de Backup Local com Verificação de Integridade")
        root.geometry("900x650")

        self.agendamentos = []
        self.thread_agendador = None
        self.parar_agendador = threading.Event()

        frame_config = ttk.LabelFrame(root, text="Configuração de Backup", padding=10)
        frame_config.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame_config, text="Pasta de Origem:").grid(row=0, column=0, sticky="w")
        self.origem_var = tk.StringVar()
        ttk.Entry(frame_config, textvariable=self.origem_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(frame_config, text="Escolher...", command=self.escolher_origem).grid(row=0, column=2)

        ttk.Label(frame_config, text="Pasta de Destino:").grid(row=1, column=0, sticky="w")
        self.destino_var = tk.StringVar()
        ttk.Entry(frame_config, textvariable=self.destino_var, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(frame_config, text="Escolher...", command=self.escolher_destino).grid(row=1, column=2)

        ttk.Label(frame_config, text="Algoritmo de Hash:").grid(row=2, column=0, sticky="w")
        self.algoritmo_var = tk.StringVar(value="sha256")
        ttk.Combobox(frame_config, textvariable=self.algoritmo_var,
                     values=["sha256", "sha1", "md5"], state="readonly", width=15).grid(row=2, column=1, sticky="w", padx=5)

        ttk.Label(frame_config, text="Agendar a cada (minutos, 0=manual):").grid(row=3, column=0, sticky="w")
        self.intervalo_var = tk.IntVar(value=0)
        ttk.Entry(frame_config, textvariable=self.intervalo_var, width=10).grid(row=3, column=1, sticky="w", padx=5)

        btns = ttk.Frame(frame_config)
        btns.grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(btns, text="Executar Backup Agora", command=self.executar_backup_agora).pack(side="left", padx=5)
        self.btn_agendar = ttk.Button(btns, text="Iniciar Agendamento", command=self.alternar_agendamento)
        self.btn_agendar.pack(side="left", padx=5)

        frame_validar = ttk.LabelFrame(root, text="Validar Integridade de um Backup Existente", padding=10)
        frame_validar.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_validar, text="Arquivo .zip do backup:").grid(row=0, column=0, sticky="w")
        self.zip_validar_var = tk.StringVar()
        ttk.Entry(frame_validar, textvariable=self.zip_validar_var, width=55).grid(row=0, column=1, padx=5)
        ttk.Button(frame_validar, text="Escolher...", command=self.escolher_zip).grid(row=0, column=2)
        ttk.Button(frame_validar, text="Validar Restauração", command=self.validar_backup_selecionado).grid(row=1, column=1, pady=5, sticky="w")

        frame_log = ttk.LabelFrame(root, text="Log de Operações", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_text = tk.Text(frame_log, height=15)
        self.log_text.pack(fill="both", expand=True)

        self._carregar_config()

    def log(self, msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.root.after(0, lambda: (
            self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n"),
            self.log_text.see(tk.END)
        ))

    def escolher_origem(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self.origem_var.set(pasta)
            self._salvar_config()

    def escolher_destino(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self.destino_var.set(pasta)
            self._salvar_config()

    def escolher_zip(self):
        caminho = filedialog.askopenfilename(filetypes=[("Backup ZIP", "*.zip")])
        if caminho:
            self.zip_validar_var.set(caminho)

    def executar_backup_agora(self):
        origem = self.origem_var.get().strip()
        destino = self.destino_var.get().strip()
        if not origem or not destino:
            messagebox.showwarning("Validação", "Informe a pasta de origem e de destino.")
            return

        def tarefa():
            try:
                executar_backup(origem, destino, self.algoritmo_var.get(), log_callback=self.log)
            except (OSError, FileNotFoundError, zipfile.BadZipFile) as e:
                self.log(f"ERRO no backup: {e}")

        threading.Thread(target=tarefa, daemon=True).start()

    def alternar_agendamento(self):
        if self.thread_agendador and self.thread_agendador.is_alive():
            self.parar_agendador.set()
            self.btn_agendar.config(text="Iniciar Agendamento")
            self.log("Agendamento interrompido.")
            return

        intervalo_min = self.intervalo_var.get()
        if intervalo_min <= 0:
            messagebox.showwarning("Validação", "Defina um intervalo em minutos maior que 0 para agendar.")
            return
        origem = self.origem_var.get().strip()
        destino = self.destino_var.get().strip()
        if not origem or not destino:
            messagebox.showwarning("Validação", "Informe a pasta de origem e de destino.")
            return

        self.parar_agendador.clear()

        def loop_agendador():
            self.log(f"Agendamento iniciado: backup a cada {intervalo_min} minuto(s).")
            while not self.parar_agendador.is_set():
                try:
                    executar_backup(origem, destino, self.algoritmo_var.get(), log_callback=self.log)
                except (OSError, FileNotFoundError, zipfile.BadZipFile) as e:
                    self.log(f"ERRO no backup agendado: {e}")
                for _ in range(intervalo_min * 60):
                    if self.parar_agendador.is_set():
                        break
                    time.sleep(1)

        self.thread_agendador = threading.Thread(target=loop_agendador, daemon=True)
        self.thread_agendador.start()
        self.btn_agendar.config(text="Parar Agendamento")

    def validar_backup_selecionado(self):
        caminho_zip = self.zip_validar_var.get().strip()
        if not caminho_zip or not os.path.isfile(caminho_zip):
            messagebox.showwarning("Validação", "Selecione um arquivo .zip de backup válido.")
            return

        pasta_destino = os.path.dirname(caminho_zip)
        nome_zip = os.path.basename(caminho_zip)
        manifesto_path = os.path.join(pasta_destino, HASHES_DIRNAME, f"{nome_zip}.manifest.json")
        if not os.path.isfile(manifesto_path):
            messagebox.showerror("Erro", f"Manifesto de integridade não encontrado:\n{manifesto_path}")
            return

        def tarefa():
            try:
                ok, divergencias = validar_restauracao(caminho_zip, manifesto_path, log_callback=self.log)
                if ok:
                    self.root.after(0, lambda: messagebox.showinfo("Validação", "Backup ÍNTEGRO. Todos os hashes conferem."))
                else:
                    detalhes = "\n".join(divergencias[:20])
                    self.root.after(0, lambda: messagebox.showerror(
                        "Divergências encontradas", f"{len(divergencias)} divergência(s):\n{detalhes}"))
            except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as e:
                self.log(f"ERRO na validação: {e}")

        threading.Thread(target=tarefa, daemon=True).start()

    def _salvar_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "origem": self.origem_var.get(),
                    "destino": self.destino_var.get(),
                }, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def _carregar_config(self):
        if os.path.isfile(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.origem_var.set(cfg.get("origem", ""))
                self.destino_var.set(cfg.get("destino", ""))
            except (OSError, json.JSONDecodeError):
                pass


def main():
    root = tk.Tk()
    BackupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
