"""
Parsers de logs de firewall/proxy offline: Squid, pfSense (formato CSV de filterlog
decodificado) e Windows Firewall (log padrão w3c).
Retorna sempre um DataFrame pandas normalizado com colunas:
    timestamp, origem, destino, porta_destino, acao, protocolo, usuario, bytes, origem_arquivo
"""
import re
import pandas as pd
import datetime


COLUNAS_PADRAO = ["timestamp", "origem", "destino", "porta_destino", "acao", "protocolo", "usuario", "bytes", "origem_arquivo"]


def _vazio():
    return pd.DataFrame(columns=COLUNAS_PADRAO)


def parse_squid(caminho):
    """Formato de log de acesso padrão do Squid:
    timestamp(epoch) duracao_ms cliente_ip codigo/status bytes metodo url usuario codigo_hier/servidor tipo_conteudo
    """
    registros = []
    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        for linha in f:
            partes = linha.split()
            if len(partes) < 10:
                continue
            try:
                ts = datetime.datetime.fromtimestamp(float(partes[0]))
            except ValueError:
                continue
            cliente_ip = partes[2]
            status = partes[3]
            n_bytes = int(partes[4]) if partes[4].isdigit() else 0
            metodo = partes[5]
            url = partes[6]
            usuario = partes[7] if partes[7] != "-" else None
            acao = "NEGADO" if "DENIED" in status else "PERMITIDO"
            registros.append({
                "timestamp": ts, "origem": cliente_ip, "destino": url, "porta_destino": None,
                "acao": acao, "protocolo": metodo, "usuario": usuario, "bytes": n_bytes,
                "origem_arquivo": "squid",
            })
    return pd.DataFrame(registros, columns=COLUNAS_PADRAO) if registros else _vazio()


def parse_pfsense(caminho):
    """Formato CSV decodificado do pfSense filterlog (colunas comuns exportadas):
    timestamp,action,interface,proto,src,src_port,dst,dst_port
    """
    try:
        df = pd.read_csv(caminho)
    except (pd.errors.ParserError, UnicodeDecodeError, OSError):
        return _vazio()

    colunas_esperadas = {"timestamp", "action", "src", "dst"}
    if not colunas_esperadas.issubset(set(c.lower() for c in df.columns)):
        return _vazio()

    df.columns = [c.lower() for c in df.columns]
    saida = pd.DataFrame()
    saida["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    saida["origem"] = df["src"]
    saida["destino"] = df["dst"]
    saida["porta_destino"] = df.get("dst_port")
    saida["acao"] = df["action"].str.upper().map(
        lambda v: "NEGADO" if v in ("BLOCK", "DENY") else "PERMITIDO"
    )
    saida["protocolo"] = df.get("proto")
    saida["usuario"] = None
    saida["bytes"] = 0
    saida["origem_arquivo"] = "pfsense"
    return saida[COLUNAS_PADRAO]


REGEX_W3C_WINFIREWALL = re.compile(
    r"^(?P<data>\S+)\s+(?P<hora>\S+)\s+(?P<action>\S+)\s+(?P<protocol>\S+)\s+"
    r"(?P<src>\S+)\s+(?P<dst>\S+)\s+(?P<srcport>\S+)\s+(?P<dstport>\S+)"
)


def parse_windows_firewall(caminho):
    """Formato padrão de log do Windows Firewall (pfirewall.log, W3C extended log format):
    #Fields: date time action protocol src-ip dst-ip src-port dst-port ...
    """
    registros = []
    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            m = REGEX_W3C_WINFIREWALL.match(linha)
            if not m:
                continue
            g = m.groupdict()
            try:
                ts = datetime.datetime.strptime(f"{g['data']} {g['hora']}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                ts = None
            acao = "NEGADO" if g["action"].upper() in ("DROP", "BLOCK") else "PERMITIDO"
            registros.append({
                "timestamp": ts, "origem": g["src"], "destino": g["dst"],
                "porta_destino": g["dstport"] if g["dstport"] != "-" else None,
                "acao": acao, "protocolo": g["protocol"], "usuario": None, "bytes": 0,
                "origem_arquivo": "windows_firewall",
            })
    return pd.DataFrame(registros, columns=COLUNAS_PADRAO) if registros else _vazio()


PARSERS = {
    "Squid (access.log)": parse_squid,
    "pfSense (filterlog CSV)": parse_pfsense,
    "Windows Firewall (pfirewall.log)": parse_windows_firewall,
}


def detectar_anomalias(df):
    """Correlação simples: identifica padrões suspeitos:
    - Origem com muitas negações em curto espaço de tempo (possível varredura/brute force).
    - Origem acessando muitos destinos distintos (possível scan de portas)."""
    anomalias = []
    if df.empty:
        return pd.DataFrame(columns=["origem", "tipo_anomalia", "detalhes"])

    negados = df[df["acao"] == "NEGADO"]
    contagem_negados = negados.groupby("origem").size()
    for origem, qtd in contagem_negados.items():
        if qtd >= 10:
            anomalias.append({"origem": origem, "tipo_anomalia": "Excesso de conexões negadas",
                               "detalhes": f"{qtd} tentativas negadas - possível varredura/força bruta"})

    destinos_distintos = df.groupby("origem")["destino"].nunique()
    for origem, qtd in destinos_distintos.items():
        if qtd >= 20:
            anomalias.append({"origem": origem, "tipo_anomalia": "Muitos destinos distintos",
                               "detalhes": f"{qtd} destinos diferentes - possível varredura de rede"})

    portas_distintas = df.dropna(subset=["porta_destino"]).groupby("origem")["porta_destino"].nunique()
    for origem, qtd in portas_distintas.items():
        if qtd >= 15:
            anomalias.append({"origem": origem, "tipo_anomalia": "Varredura de portas",
                               "detalhes": f"{qtd} portas de destino distintas em curto período"})

    return pd.DataFrame(anomalias) if anomalias else pd.DataFrame(columns=["origem", "tipo_anomalia", "detalhes"])
