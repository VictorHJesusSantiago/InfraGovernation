"""
Agente Local de Coleta de Métricas
Coleta métricas de disco/memória/CPU da estação local e grava em um arquivo JSON
compartilhado (pasta de rede ou compartilhamento local), para consolidação pelo dashboard.
Stack: Python + psutil

Uso:
    python agente.py --pasta "\\\\servidor\\compartilhamento\\metrics" --intervalo 60
"""
import argparse
import json
import os
import socket
import time
import datetime
import psutil


def coletar_metricas():
    disco_particoes = []
    for part in psutil.disk_partitions(all=False):
        try:
            uso = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        disco_particoes.append({
            "dispositivo": part.device,
            "ponto_montagem": part.mountpoint,
            "total_gb": round(uso.total / (1024 ** 3), 2),
            "usado_gb": round(uso.used / (1024 ** 3), 2),
            "livre_gb": round(uso.free / (1024 ** 3), 2),
            "percentual_uso": uso.percent,
        })

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "hostname": socket.gethostname(),
        "timestamp": datetime.datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_count": psutil.cpu_count(),
        "memoria": {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "usado_gb": round(mem.used / (1024 ** 3), 2),
            "percentual_uso": mem.percent,
        },
        "swap": {
            "total_gb": round(swap.total / (1024 ** 3), 2),
            "usado_gb": round(swap.used / (1024 ** 3), 2),
            "percentual_uso": swap.percent,
        },
        "discos": disco_particoes,
        "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    }


def gravar_metricas(pasta_destino):
    os.makedirs(pasta_destino, exist_ok=True)
    metricas = coletar_metricas()
    arquivo = os.path.join(pasta_destino, f"{metricas['hostname']}.json")
    tmp = arquivo + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False)
    os.replace(tmp, arquivo)
    return arquivo


def main():
    parser = argparse.ArgumentParser(description="Agente local de coleta de métricas de capacidade")
    parser.add_argument("--pasta", required=True, help="Pasta compartilhada/rede onde gravar as métricas")
    parser.add_argument("--intervalo", type=int, default=60, help="Intervalo em segundos entre coletas (0 = executar uma vez)")
    args = parser.parse_args()

    if args.intervalo <= 0:
        arquivo = gravar_metricas(args.pasta)
        print(f"Métricas gravadas em: {arquivo}")
        return

    print(f"Agente iniciado. Gravando métricas a cada {args.intervalo}s em {args.pasta}")
    try:
        while True:
            arquivo = gravar_metricas(args.pasta)
            print(f"[{datetime.datetime.now()}] Métricas gravadas em {arquivo}")
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("Agente encerrado.")


if __name__ == "__main__":
    main()
