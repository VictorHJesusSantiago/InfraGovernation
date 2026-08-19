"""
Gerador de Políticas de Senha e Compliance
Valida políticas corporativas (baseadas em NIST SP 800-63B e ISO/IEC 27001 Anexo A)
contra arquivos de configuração exportados (JSON), e opcionalmente valida senhas individuais.
Stack: Python CLI + argparse
"""
import argparse
import json
import re
import sys
import datetime

# --------------------------------------------------------------------------
# Perfis de referência (simplificados a partir de NIST 800-63B e ISO 27001)
# --------------------------------------------------------------------------
PERFIS = {
    "nist": {
        "nome": "NIST SP 800-63B",
        "min_tamanho": 8,
        "recomendado_tamanho": 15,
        "exige_maiuscula": False,
        "exige_minuscula": False,
        "exige_numero": False,
        "exige_especial": False,
        "expiracao_maxima_dias": None,   # NIST não recomenda expiração forçada
        "bloqueia_reuso_ultimas": 0,
        "bloqueia_senhas_comuns": True,
        "max_tentativas_login": 10,
    },
    "iso27001": {
        "nome": "ISO/IEC 27001 (Anexo A - controles de senha)",
        "min_tamanho": 12,
        "recomendado_tamanho": 16,
        "exige_maiuscula": True,
        "exige_minuscula": True,
        "exige_numero": True,
        "exige_especial": True,
        "expiracao_maxima_dias": 90,
        "bloqueia_reuso_ultimas": 5,
        "bloqueia_senhas_comuns": True,
        "max_tentativas_login": 5,
    },
}

SENHAS_COMUNS = {
    "123456", "senha123", "password", "admin123", "qwerty", "123456789",
    "12345678", "senha", "letmein", "welcome", "abc123", "iloveyou",
    "administrator", "trocar123",
}


def validar_config(config, perfil_nome):
    """Compara um dicionário de configuração exportada contra o perfil de referência.
    Retorna lista de (severidade, mensagem)."""
    perfil = PERFIS[perfil_nome]
    achados = []

    def checar(campo, valor_config, comparador, esperado, msg_fail):
        if comparador(valor_config, esperado):
            return
        achados.append(("NAO_CONFORME", msg_fail))

    tamanho_cfg = config.get("tamanho_minimo", 0)
    if tamanho_cfg < perfil["min_tamanho"]:
        achados.append(("NAO_CONFORME",
            f"tamanho_minimo={tamanho_cfg} é menor que o exigido ({perfil['min_tamanho']})."))
    elif tamanho_cfg < perfil["recomendado_tamanho"]:
        achados.append(("AVISO",
            f"tamanho_minimo={tamanho_cfg} atende ao mínimo, mas abaixo do recomendado ({perfil['recomendado_tamanho']})."))

    for campo, chave_cfg in [
        ("exige_maiuscula", "exige_maiuscula"),
        ("exige_minuscula", "exige_minuscula"),
        ("exige_numero", "exige_numero"),
        ("exige_especial", "exige_especial"),
    ]:
        se_exigido = perfil[campo]
        valor_cfg = bool(config.get(chave_cfg, False))
        if se_exigido and not valor_cfg:
            achados.append(("NAO_CONFORME", f"{chave_cfg}=false, mas o perfil exige true."))

    exp_max = perfil["expiracao_maxima_dias"]
    exp_cfg = config.get("expiracao_dias")
    if exp_max is not None:
        if not exp_cfg or exp_cfg > exp_max:
            achados.append(("NAO_CONFORME",
                f"expiracao_dias={exp_cfg} excede o máximo permitido ({exp_max}) ou não está definido."))
    else:
        if exp_cfg and exp_cfg < 365:
            achados.append(("AVISO",
                "Perfil NIST recomenda não forçar expiração de senha sem motivo (ex.: indício de comprometimento)."))

    reuso_min = perfil["bloqueia_reuso_ultimas"]
    reuso_cfg = config.get("bloqueia_reuso_ultimas", 0)
    if reuso_min > 0 and reuso_cfg < reuso_min:
        achados.append(("NAO_CONFORME",
            f"bloqueia_reuso_ultimas={reuso_cfg} é menor que o exigido ({reuso_min})."))

    if perfil["bloqueia_senhas_comuns"] and not config.get("bloqueia_senhas_comuns", False):
        achados.append(("NAO_CONFORME", "Configuração não bloqueia senhas comuns/vazadas (bloqueia_senhas_comuns=false)."))

    max_tent = perfil["max_tentativas_login"]
    tent_cfg = config.get("max_tentativas_login")
    if tent_cfg is None or tent_cfg > max_tent:
        achados.append(("AVISO",
            f"max_tentativas_login={tent_cfg} maior que o recomendado ({max_tent}) - risco de força bruta."))

    return achados


def avaliar_senha(senha, perfil_nome):
    """Avalia uma senha individual contra as regras do perfil."""
    perfil = PERFIS[perfil_nome]
    problemas = []

    if len(senha) < perfil["min_tamanho"]:
        problemas.append(f"Tamanho {len(senha)} menor que o mínimo exigido ({perfil['min_tamanho']}).")
    elif len(senha) < perfil["recomendado_tamanho"]:
        problemas.append(f"Tamanho {len(senha)} abaixo do recomendado ({perfil['recomendado_tamanho']}) - aviso.")

    if perfil["exige_maiuscula"] and not re.search(r"[A-Z]", senha):
        problemas.append("Falta letra maiúscula.")
    if perfil["exige_minuscula"] and not re.search(r"[a-z]", senha):
        problemas.append("Falta letra minúscula.")
    if perfil["exige_numero"] and not re.search(r"[0-9]", senha):
        problemas.append("Falta número.")
    if perfil["exige_especial"] and not re.search(r"[^A-Za-z0-9]", senha):
        problemas.append("Falta caractere especial.")

    if perfil["bloqueia_senhas_comuns"] and senha.lower() in SENHAS_COMUNS:
        problemas.append("Senha está na lista de senhas comuns/vazadas conhecidas.")

    if re.search(r"(.)\1{2,}", senha):
        problemas.append("Contém sequência de caracteres repetidos (ex.: 'aaa').")

    conforme = not any("menor que o mínimo" in p or "Falta" in p or "lista de senhas comuns" in p for p in problemas)
    return conforme, problemas


def cmd_validar_config(args):
    with open(args.arquivo, "r", encoding="utf-8") as f:
        config = json.load(f)

    print(f"=== Relatório de Compliance de Política de Senha ===")
    print(f"Arquivo: {args.arquivo}")
    print(f"Perfil de referência: {PERFIS[args.perfil]['nome']}")
    print(f"Data: {datetime.datetime.now().isoformat()}\n")

    achados = validar_config(config, args.perfil)
    if not achados:
        print("RESULTADO: CONFORME. Nenhuma violação encontrada.")
    else:
        n_falhas = sum(1 for s, _ in achados if s == "NAO_CONFORME")
        n_avisos = sum(1 for s, _ in achados if s == "AVISO")
        print(f"RESULTADO: {'NÃO CONFORME' if n_falhas else 'CONFORME COM RESSALVAS'} "
              f"({n_falhas} não conformidade(s), {n_avisos} aviso(s))\n")
        for severidade, msg in achados:
            prefixo = "[NÃO CONFORME]" if severidade == "NAO_CONFORME" else "[AVISO]"
            print(f"{prefixo} {msg}")

    if args.saida:
        relatorio = {
            "arquivo": args.arquivo,
            "perfil": args.perfil,
            "data": datetime.datetime.now().isoformat(),
            "achados": [{"severidade": s, "mensagem": m} for s, m in achados],
        }
        with open(args.saida, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        print(f"\nRelatório salvo em: {args.saida}")

    return 1 if any(s == "NAO_CONFORME" for s, _ in achados) else 0


def cmd_validar_senha(args):
    conforme, problemas = avaliar_senha(args.senha, args.perfil)
    print(f"Perfil: {PERFIS[args.perfil]['nome']}")
    print(f"Senha conforme: {'SIM' if conforme else 'NÃO'}")
    if problemas:
        print("Observações:")
        for p in problemas:
            print(f"  - {p}")
    return 0 if conforme else 1


def cmd_gerar_exemplo(args):
    exemplo = {
        "tamanho_minimo": 12,
        "exige_maiuscula": True,
        "exige_minuscula": True,
        "exige_numero": True,
        "exige_especial": True,
        "expiracao_dias": 90,
        "bloqueia_reuso_ultimas": 5,
        "bloqueia_senhas_comuns": True,
        "max_tentativas_login": 5,
    }
    with open(args.saida, "w", encoding="utf-8") as f:
        json.dump(exemplo, f, indent=2, ensure_ascii=False)
    print(f"Arquivo de configuração de exemplo gerado em: {args.saida}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Gerador/validador de políticas de senha corporativas (NIST 800-63B / ISO 27001)."
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_validar = sub.add_parser("validar-config", help="Valida um arquivo de configuração exportado contra um perfil.")
    p_validar.add_argument("arquivo", help="Caminho do arquivo JSON de configuração exportada.")
    p_validar.add_argument("--perfil", choices=PERFIS.keys(), default="iso27001", help="Perfil de referência.")
    p_validar.add_argument("--saida", help="Caminho para salvar o relatório em JSON.")
    p_validar.set_defaults(func=cmd_validar_config)

    p_senha = sub.add_parser("validar-senha", help="Valida uma senha individual contra um perfil.")
    p_senha.add_argument("senha", help="Senha a validar.")
    p_senha.add_argument("--perfil", choices=PERFIS.keys(), default="iso27001")
    p_senha.set_defaults(func=cmd_validar_senha)

    p_exemplo = sub.add_parser("gerar-exemplo", help="Gera um arquivo de configuração de exemplo (conforme).")
    p_exemplo.add_argument("--saida", default="config_exemplo.json")
    p_exemplo.set_defaults(func=cmd_gerar_exemplo)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
