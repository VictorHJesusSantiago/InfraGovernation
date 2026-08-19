"""
Auditor de Configuração de Rede Local
Varre hosts na LAN, portas abertas, hostname, MAC, e gera relatório de compliance.
Stack: Python + Scapy + Tkinter

Observação: descoberta de hosts via ARP (Scapy) requer privilégios de administrador/root
e a biblioteca Npcap (Windows) / libpcap (Linux/Mac) instalada. Caso Scapy não esteja
disponível ou falhe por falta de permissão, o auditor cai automaticamente para um modo
de fallback baseado em sockets puros (ping via TCP connect + resolução de hostname),
mantendo a ferramenta funcional em qualquer ambiente.
"""
import ipaddress
import socket
import threading
import queue
import datetime
import json
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from scapy.all import ARP, Ether, srp
    SCAPY_OK = True
except Exception:
    SCAPY_OK = False

PORTAS_PADRAO = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 3306, 3389, 8080]

PORTAS_RISCO = {
    23: "Telnet (texto claro) - alto risco",
    21: "FTP (texto claro) - risco médio",
    139: "NetBIOS - risco médio",
    445: "SMB - risco alto se exposto",
    3389: "RDP exposto - risco alto",
    135: "RPC - risco médio",
}


def descobrir_hosts_arp(rede_cidr, timeout=2):
    """Descoberta via ARP usando Scapy (requer privilégios administrativos)."""
    hosts = []
    arp = ARP(pdst=rede_cidr)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    pacote = ether / arp
    resultado = srp(pacote, timeout=timeout, verbose=False)[0]
    for _sent, recebido in resultado:
        hosts.append({"ip": recebido.psrc, "mac": recebido.hwsrc})
    return hosts


def descobrir_hosts_fallback(rede_cidr, timeout=0.3):
    """Fallback sem Scapy: tenta conexão TCP em portas comuns para detectar hosts ativos."""
    rede = ipaddress.ip_network(rede_cidr, strict=False)
    hosts = []
    lock = threading.Lock()
    q = queue.Queue()
    for ip in rede.hosts():
        q.put(str(ip))

    def worker():
        while not q.empty():
            try:
                ip = q.get_nowait()
            except queue.Empty:
                return
            ativo = False
            for porta in (80, 443, 22, 445, 139):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(timeout)
                        if s.connect_ex((ip, porta)) == 0:
                            ativo = True
                            break
                except OSError:
                    pass
            if ativo:
                with lock:
                    hosts.append({"ip": ip, "mac": "N/D (fallback sem ARP)"})
            q.task_done()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return hosts


def resolver_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror):
        return "N/D"


def escanear_portas(ip, portas, timeout=0.5):
    abertas = []
    for porta in portas:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                if s.connect_ex((ip, porta)) == 0:
                    abertas.append(porta)
        except OSError:
            pass
    return abertas


def avaliar_compliance(host):
    problemas = []
    for porta in host["portas_abertas"]:
        if porta in PORTAS_RISCO:
            problemas.append(f"Porta {porta}: {PORTAS_RISCO[porta]}")
    if host["hostname"] == "N/D":
        problemas.append("Hostname não resolvido (DNS reverso ausente)")
    host["compliance_ok"] = len(problemas) == 0
    host["problemas"] = problemas
    return host


class AuditorApp:
    def __init__(self, root):
        self.root = root
        root.title("Auditor de Configuração de Rede Local")
        root.geometry("1000x650")

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Rede (CIDR):").pack(side="left")
        self.rede_var = tk.StringVar(value=self._detectar_rede_local())
        ttk.Entry(top, textvariable=self.rede_var, width=20).pack(side="left", padx=5)

        ttk.Label(top, text="Portas (separadas por vírgula):").pack(side="left", padx=(15, 0))
        self.portas_var = tk.StringVar(value=",".join(str(p) for p in PORTAS_PADRAO))
        ttk.Entry(top, textvariable=self.portas_var, width=40).pack(side="left", padx=5)

        self.btn_scan = ttk.Button(top, text="Iniciar Varredura", command=self.iniciar_scan)
        self.btn_scan.pack(side="left", padx=10)

        self.status_var = tk.StringVar(value="Pronto." + (" (Scapy disponível)" if SCAPY_OK else " (modo fallback sem Scapy/privilégios)"))
        ttk.Label(root, textvariable=self.status_var, foreground="blue").pack(fill="x", padx=10)

        colunas = ("ip", "mac", "hostname", "portas", "compliance")
        self.tree = ttk.Treeview(root, columns=colunas, show="headings", height=20)
        for col, texto, largura in [
            ("ip", "IP", 120), ("mac", "MAC", 150), ("hostname", "Hostname", 200),
            ("portas", "Portas Abertas", 250), ("compliance", "Compliance", 100)
        ]:
            self.tree.heading(col, text=texto)
            self.tree.column(col, width=largura)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.tag_configure("nok", background="#ffdddd")
        self.tree.tag_configure("ok", background="#ddffdd")
        self.tree.bind("<<TreeviewSelect>>", self.mostrar_detalhes)

        bottom = ttk.Frame(root, padding=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Exportar Relatório JSON", command=self.exportar_json).pack(side="left")
        ttk.Button(bottom, text="Exportar Relatório CSV", command=self.exportar_csv).pack(side="left", padx=10)

        self.detalhes_text = tk.Text(root, height=6)
        self.detalhes_text.pack(fill="x", padx=10, pady=(0, 10))

        self.resultados = []

    def _detectar_rede_local(self):
        try:
            hostname = socket.gethostname()
            ip_local = socket.gethostbyname(hostname)
            partes = ip_local.split(".")
            return f"{'.'.join(partes[:3])}.0/24"
        except socket.error:
            return "192.168.1.0/24"

    def iniciar_scan(self):
        rede_cidr = self.rede_var.get().strip()
        try:
            ipaddress.ip_network(rede_cidr, strict=False)
        except ValueError:
            messagebox.showerror("Erro", "CIDR de rede inválido. Ex: 192.168.1.0/24")
            return
        try:
            portas = [int(p.strip()) for p in self.portas_var.get().split(",") if p.strip()]
        except ValueError:
            messagebox.showerror("Erro", "Lista de portas inválida.")
            return

        self.btn_scan.config(state="disabled")
        self.status_var.set("Varredura em andamento...")
        self.tree.delete(*self.tree.get_children())
        self.resultados = []
        thread = threading.Thread(target=self._executar_scan, args=(rede_cidr, portas), daemon=True)
        thread.start()

    def _executar_scan(self, rede_cidr, portas):
        try:
            if SCAPY_OK:
                try:
                    hosts = descobrir_hosts_arp(rede_cidr)
                except PermissionError:
                    hosts = descobrir_hosts_fallback(rede_cidr)
                except Exception:
                    hosts = descobrir_hosts_fallback(rede_cidr)
            else:
                hosts = descobrir_hosts_fallback(rede_cidr)

            for h in hosts:
                h["hostname"] = resolver_hostname(h["ip"])
                h["portas_abertas"] = escanear_portas(h["ip"], portas)
                h["timestamp"] = datetime.datetime.now().isoformat()
                avaliar_compliance(h)
                self.resultados.append(h)
                self.root.after(0, self._adicionar_linha, h)

            self.root.after(0, lambda: self.status_var.set(f"Concluído: {len(hosts)} host(s) encontrado(s)."))
        finally:
            self.root.after(0, lambda: self.btn_scan.config(state="normal"))

    def _adicionar_linha(self, host):
        tag = "ok" if host["compliance_ok"] else "nok"
        portas_str = ", ".join(str(p) for p in host["portas_abertas"]) or "nenhuma"
        status = "OK" if host["compliance_ok"] else f"{len(host['problemas'])} problema(s)"
        self.tree.insert("", "end", values=(host["ip"], host["mac"], host["hostname"], portas_str, status), tags=(tag,))

    def mostrar_detalhes(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        host = self.resultados[idx]
        self.detalhes_text.delete("1.0", tk.END)
        if host["problemas"]:
            self.detalhes_text.insert(tk.END, "Problemas de compliance:\n" + "\n".join(f"- {p}" for p in host["problemas"]))
        else:
            self.detalhes_text.insert(tk.END, "Nenhum problema de compliance identificado.")

    def exportar_json(self):
        if not self.resultados:
            messagebox.showinfo("Exportar", "Nenhum resultado para exportar.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Exportar", f"Relatório salvo em:\n{path}")

    def exportar_csv(self):
        if not self.resultados:
            messagebox.showinfo("Exportar", "Nenhum resultado para exportar.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ip", "mac", "hostname", "portas_abertas", "compliance_ok", "problemas", "timestamp"])
            for h in self.resultados:
                writer.writerow([
                    h["ip"], h["mac"], h["hostname"],
                    ";".join(str(p) for p in h["portas_abertas"]),
                    h["compliance_ok"], " | ".join(h["problemas"]), h["timestamp"]
                ])
        messagebox.showinfo("Exportar", f"Relatório salvo em:\n{path}")


def main():
    root = tk.Tk()
    AuditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
