from flask import (
    Blueprint,
    render_template,
    jsonify,
    request
)

from .service import (
    fetch_prices,
    calcular_rebalanceamento,
    aplicar_rebalanceamento,
    buscar_ativos
)

from .storage import (
    load_portfolio,
    save_portfolio,
    add_ativo,
    remove_ativo,
    update_ativo,
    listar_backups,
    restaurar_backup,
    BACKUP_DIR,
    PORTFOLIO_FILE
)

import os
import json
from datetime import datetime

financeiro_bp = Blueprint(
    "financeiro",
    __name__,
    template_folder="templates"
)


# =====================================================
# PÁGINA PRINCIPAL
# =====================================================

@financeiro_bp.route("/")
def index():

    portfolio = load_portfolio()

    precos = fetch_prices(portfolio)

    resultado = calcular_rebalanceamento(
        portfolio=portfolio,
        precos=precos,
        aporte=0,
        tolerancia=2
    )

    return render_template(
        "financeiro.html",
        portfolio=portfolio,
        precos=precos,
        resultado=resultado
    )


# =====================================================
# COTAÇÕES
# =====================================================

@financeiro_bp.route(
    "/api/cotacoes",
    methods=["GET"]
)
def api_cotacoes():

    portfolio = load_portfolio()

    precos = fetch_prices(portfolio)

    return jsonify(precos)


# =====================================================
# PORTFOLIO
# =====================================================

@financeiro_bp.route(
    "/api/portfolio",
    methods=["GET"]
)
def api_get_portfolio():

    return jsonify(load_portfolio())


@financeiro_bp.route(
    "/api/portfolio",
    methods=["POST"]
)
def api_save_portfolio():

    data = request.json

    if not isinstance(data, list):

        return jsonify({
            "error":
            "Esperado uma lista de ativos"
        }), 400

    soma = sum(
        item.get("peso", 0)
        for item in data
    )

    if abs(soma - 1.0) > 0.001:

        return jsonify({
            "error":
            f"A soma dos pesos deve ser 100%. Atual: {soma*100:.2f}%"
        }), 400

    save_portfolio(data)

    return jsonify({
        "ok": True,
        "total": len(data)
    })


# =====================================================
# ADICIONAR ATIVO
# =====================================================

@financeiro_bp.route(
    "/api/portfolio/ativo",
    methods=["POST"]
)
def api_add_ativo():
    body = request.json or {}
    ticker = body.get("ticker", "").strip().upper()
    display = body.get("display", ticker).strip().upper()
    peso = float(body.get("peso", 0))
    quantidade = int(body.get("quantidade", 0))

    if not ticker:
        return jsonify({"error": "Ticker obrigatório"}), 400
    if peso <= 0:
        return jsonify({"error": "Peso deve ser maior que zero"}), 400

    portfolio = load_portfolio()
    if any(a["display"] == display for a in portfolio):
        return jsonify({"error": f"Ativo '{display}' já existe na carteira"}), 400

    portfolio.append({
        "ticker": ticker,
        "display": display,
        "peso": peso,
        "quantidade": quantidade,
    })
    save_portfolio(portfolio)
    return jsonify({"ok": True, "portfolio": portfolio})


# =====================================================
# REMOVER ATIVO
# =====================================================

@financeiro_bp.route(
    "/api/portfolio/ativo/<display>",
    methods=["DELETE"]
)
def api_remove_ativo(display):
    portfolio = load_portfolio()
    nova = [a for a in portfolio if a["display"] != display.upper()]
    if len(nova) == len(portfolio):
        return jsonify({"error": f"Ativo '{display}' não encontrado"}), 404
    save_portfolio(nova)
    return jsonify({"ok": True, "portfolio": nova})

# =====================================================
# ATUALIZAR ATIVO
# =====================================================

@financeiro_bp.route(
    "/api/portfolio/ativo/<display>",
    methods=["PUT"]
)
def api_update_ativo(display):
    body = request.json or {}
    portfolio = load_portfolio()
    for a in portfolio:
        if a["display"] == display.upper():
            if "quantidade" in body:
                a["quantidade"] = int(body["quantidade"])
            if "peso" in body:
                a["peso"] = float(body["peso"])
            save_portfolio(portfolio)
            return jsonify({"ok": True})
    return jsonify({"error": "Ativo não encontrado"}), 404


# =====================================================
# REBALANCEAR
# =====================================================

@financeiro_bp.route(
    "/api/rebalancear",
    methods=["POST"]
)
def api_rebalancear():
    data = request.json or {}
    aporte = float(data.get("aporte", 0))
    quantidades = data.get("quantidades", {})
    tolerancia = float(data.get("tolerancia", 2.0))  # 🔥 recebe do front

    portfolio = load_portfolio()
    for i, item in enumerate(portfolio):
        if item["display"] in quantidades:
            portfolio[i]["quantidade"] = int(quantidades[item["display"]])

    precos = fetch_prices(portfolio)
    resultado = calcular_rebalanceamento(portfolio, precos, aporte, tolerancia)
    return jsonify(resultado)


# =====================================================
# APLICAR REBALANCEAMENTO
# =====================================================

@financeiro_bp.route(
    "/api/aplicar",
    methods=["POST"]
)
def api_aplicar():

    data = request.json or {}

    try:

        resultado = aplicar_rebalanceamento(
            data
        )

        return jsonify(resultado)

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400


# =====================================================
# BACKUPS
# =====================================================

@financeiro_bp.route(
    "/api/backups",
    methods=["GET"]
)
def api_backups():

    return jsonify(
        listar_backups()
    )


# =====================================================
# RESTAURAR BACKUP
# =====================================================

@financeiro_bp.route(
    "/api/restaurar",
    methods=["POST"]
)
def api_restaurar():

    body = request.json or {}

    arquivo = body.get("arquivo")

    try:

        resultado = restaurar_backup(
            arquivo
        )

        return jsonify(resultado)

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

@financeiro_bp.route("/api/ativos")
def api_buscar_ativos():

    termo = request.args.get(
        "q",
        ""
    )

    if len(termo) < 2:
        return jsonify([])

    return jsonify(
        buscar_ativos(termo)
    )


# =====================================================
# LIMPAR CARTEIRA
# =====================================================

@financeiro_bp.route(
    "/api/limpar-carteira",
    methods=["POST"]
)
def api_limpar_carteira():
    portfolio = load_portfolio()

    if not portfolio:
        return jsonify({
            "error": "A carteira já está vazia."
        }), 400

    # Backup de segurança antes de limpar
    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )
    backup_file = os.path.join(
        BACKUP_DIR,
        f"portfolio_pre_limpeza_{timestamp}.json"
    )
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)

    # Limpar
    save_portfolio([])

    return jsonify({
        "ok": True,
        "message": f"Carteira limpa com sucesso. {len(portfolio)} ativos removidos. Backup salvo.",
        "backup": backup_file
    })