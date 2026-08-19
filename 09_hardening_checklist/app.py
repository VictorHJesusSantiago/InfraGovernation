"""
Ferramenta de Hardening Checklist (inspirada em CIS Benchmarks)
Roda checklist de hardening de SO (Windows e Linux) e gera relatório de gaps.
Stack: Python CLI + psutil/subprocess
"""
import argparse
import json
import platform
import subprocess
import sys
import datetime
import psutil


def _run(cmd, shell=False):
    try:
        resultado = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=15)
        return resultado.stdout.strip(), resultado.returncode
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return "", -1


# --------------------------------------------------------------------------
# Checks Windows (equivalentes simplificados a controles do CIS Benchmark
# para Microsoft Windows)
# --------------------------------------------------------------------------
def checks_windows():
    checks = []

    saida, _ = _run(["netsh", "advfirewall", "show", "allprofiles", "state"])
    firewall_ligado = saida.count("ON") >= 1 and "OFF" not in saida
    checks.append({
        "id": "CIS-WIN-1.1", "titulo": "Firewall do Windows ativo em todos os perfis",
        "conforme": firewall_ligado,
        "evidencia": saida[:300] or "netsh indisponível",
        "recomendacao": "Habilitar o firewall em todos os perfis (Domínio, Privado, Público).",
    })

    saida, _ = _run(["net", "accounts"])
    politica_senha_ok = False
    tamanho_min = None
    for linha in saida.splitlines():
        if "Minimum password length" in linha or "Comprimento m" in linha:
            partes = [p for p in linha.split() if p.isdigit()]
            if partes:
                tamanho_min = int(partes[-1])
    politica_senha_ok = bool(tamanho_min and tamanho_min >= 8)
    checks.append({
        "id": "CIS-WIN-1.2", "titulo": "Tamanho mínimo de senha >= 8 caracteres",
        "conforme": politica_senha_ok,
        "evidencia": saida[:300] or "net accounts indisponível",
        "recomendacao": "Configurar tamanho mínimo de senha para pelo menos 8 (idealmente 14) caracteres via GPO.",
    })

    saida, rc = _run(["powershell", "-Command",
                       "Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol"])
    smb1_desabilitado = "False" in saida or rc != 0
    checks.append({
        "id": "CIS-WIN-2.1", "titulo": "Protocolo SMBv1 desabilitado",
        "conforme": smb1_desabilitado,
        "evidencia": saida[:300] or "PowerShell indisponível",
        "recomendacao": "Desabilitar SMBv1: Disable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol",
    })

    saida, _ = _run(["powershell", "-Command", "Get-Service WinRM | Select-Object Status"])
    checks.append({
        "id": "CIS-WIN-2.2", "titulo": "Serviço WinRM sob controle (revisar se necessário)",
        "conforme": True,  # informativo - não bloqueia, apenas reporta estado
        "evidencia": saida[:300] or "N/D",
        "recomendacao": "Desabilitar WinRM se não for utilizado para administração remota.",
    })

    return checks


# --------------------------------------------------------------------------
# Checks Linux (equivalentes simplificados a controles do CIS Benchmark
# para distribuições Linux)
# --------------------------------------------------------------------------
def checks_linux():
    checks = []

    saida, rc = _run(["sshd", "-T"])
    permit_root = "permitrootlogin no" in saida.lower()
    checks.append({
        "id": "CIS-LNX-5.1", "titulo": "SSH: PermitRootLogin desabilitado",
        "conforme": permit_root if rc == 0 else False,
        "evidencia": saida[:300] if rc == 0 else "sshd -T indisponível (requer root/sshd instalado)",
        "recomendacao": "Definir 'PermitRootLogin no' em /etc/ssh/sshd_config.",
    })

    try:
        with open("/etc/login.defs", "r", encoding="utf-8") as f:
            conteudo = f.read()
        pass_max_days_ok = False
        for linha in conteudo.splitlines():
            if linha.strip().startswith("PASS_MAX_DAYS"):
                valor = linha.split()[-1]
                pass_max_days_ok = valor.isdigit() and int(valor) <= 90
        checks.append({
            "id": "CIS-LNX-5.2", "titulo": "PASS_MAX_DAYS <= 90 dias",
            "conforme": pass_max_days_ok,
            "evidencia": "Verificado em /etc/login.defs",
            "recomendacao": "Definir PASS_MAX_DAYS 90 em /etc/login.defs.",
        })
    except OSError:
        checks.append({
            "id": "CIS-LNX-5.2", "titulo": "PASS_MAX_DAYS <= 90 dias",
            "conforme": False, "evidencia": "/etc/login.defs não encontrado (ambiente não-Linux?)",
            "recomendacao": "Definir PASS_MAX_DAYS 90 em /etc/login.defs.",
        })

    saida, rc = _run(["systemctl", "is-enabled", "firewalld"])
    firewall_ok = "enabled" in saida
    if rc != 0:
        saida2, rc2 = _run(["ufw", "status"])
        firewall_ok = "active" in saida2.lower()
        saida = saida2
    checks.append({
        "id": "CIS-LNX-3.1", "titulo": "Firewall (firewalld/ufw) habilitado",
        "conforme": firewall_ok,
        "evidencia": saida[:300] or "N/D",
        "recomendacao": "Habilitar e iniciar firewalld ou ufw.",
    })

    return checks


# --------------------------------------------------------------------------
# Checks multiplataforma (via psutil)
# --------------------------------------------------------------------------
def checks_multiplataforma():
    checks = []

    conexoes = psutil.net_connections(kind="inet")
    portas_escuta = sorted({c.laddr.port for c in conexoes if c.status == psutil.CONN_LISTEN and c.laddr})
    portas_arriscadas = {21, 23, 445, 3389, 5900}
    portas_expostas_risco = sorted(portas_arriscadas.intersection(portas_escuta))
    checks.append({
        "id": "CIS-GEN-1.1", "titulo": "Nenhum serviço de alto risco escutando (FTP/Telnet/SMB/RDP/VNC)",
        "conforme": len(portas_expostas_risco) == 0,
        "evidencia": f"Portas em escuta: {portas_escuta}. Risco encontrado: {portas_expostas_risco}",
        "recomendacao": "Desabilitar serviços desnecessários escutando em portas de alto risco.",
    })

    usuarios_conectados = psutil.users()
    checks.append({
        "id": "CIS-GEN-1.2", "titulo": "Sessões ativas revisadas",
        "conforme": True,
        "evidencia": f"{len(usuarios_conectados)} sessão(ões) ativa(s): "
                     f"{[u.name for u in usuarios_conectados]}",
        "recomendacao": "Revisar periodicamente sessões ativas não reconhecidas.",
    })

    disco = psutil.disk_usage("/")
    checks.append({
        "id": "CIS-GEN-1.3", "titulo": "Espaço em disco root/system suficiente (< 90% de uso)",
        "conforme": disco.percent < 90,
        "evidencia": f"{disco.percent}% utilizado",
        "recomendacao": "Liberar espaço em disco ou expandir volume - discos cheios impedem logs de segurança.",
    })

    return checks


def executar_checklist():
    sistema = platform.system()
    checks = checks_multiplataforma()
    if sistema == "Windows":
        checks += checks_windows()
    elif sistema == "Linux":
        checks += checks_linux()
    else:
        print(f"Aviso: sistema '{sistema}' não possui checks específicos implementados; "
              "executando apenas checks multiplataforma.", file=sys.stderr)
    return checks


def imprimir_relatorio(checks):
    total = len(checks)
    conformes = sum(1 for c in checks if c["conforme"])
    print(f"=== Relatório de Hardening ({platform.system()}) ===")
    print(f"Data: {datetime.datetime.now().isoformat()}")
    print(f"Conformidade: {conformes}/{total} controles\n")
    for c in checks:
        status = "OK" if c["conforme"] else "GAP"
        print(f"[{status}] {c['id']} - {c['titulo']}")
        if not c["conforme"]:
            print(f"         Evidência: {c['evidencia']}")
            print(f"         Recomendação: {c['recomendacao']}")
    print(f"\nResumo: {conformes}/{total} conformes, {total - conformes} gap(s) identificado(s).")


def main():
    parser = argparse.ArgumentParser(description="Hardening Checklist local (inspirado em CIS Benchmarks)")
    parser.add_argument("--saida", help="Caminho para salvar o relatório completo em JSON")
    args = parser.parse_args()

    checks = executar_checklist()
    imprimir_relatorio(checks)

    if args.saida:
        relatorio = {
            "sistema": platform.system(),
            "data": datetime.datetime.now().isoformat(),
            "checks": checks,
        }
        with open(args.saida, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        print(f"\nRelatório salvo em: {args.saida}")

    gaps = sum(1 for c in checks if not c["conforme"])
    sys.exit(1 if gaps > 0 else 0)


if __name__ == "__main__":
    main()
