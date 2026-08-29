import json
import os
import math
import yfinance as yf
from datetime import datetime

from models import db, HistoricoAporte, CompraAtivo

from .storage import (
    load_portfolio,
    save_portfolio,
    PORTFOLIO_FILE,
    HISTORICO_FILE,
    BACKUP_DIR
)
import concurrent.futures

def _fetch_single_price(item):
    symbol = formatar_ticker_yahoo(item["ticker"])
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if hist is None or hist.empty:
            return item["display"], None
            
        valid_close = hist["Close"].dropna()
            
        price = valid_close.iloc[-1]
        
        if math.isnan(price):
            return item["display"], None
        return item["display"], round(float(price), 2)
    except Exception as e:
        print(f"Erro ao buscar {symbol}: {e}")
        return item["display"], None

def fetch_prices(portfolio):
    prices = {}
    if not portfolio:
        return prices
        
    usd_brl_rate = 1.0
    has_usd = any("-USD" in item["ticker"].upper() for item in portfolio)
    if has_usd:
        try:
            hist = yf.Ticker("BRL=X").history(period="5d")
            valid_brl = hist["Close"].dropna()
            if not valid_brl.empty:
                usd_brl_rate = float(valid_brl.iloc[-1])
        except Exception as e:
            print(f"Erro ao buscar cotacao do dolar: {e}")
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_fetch_single_price, item) for item in portfolio]
        for future in concurrent.futures.as_completed(futures):
            display, price = future.result()
            
            if price is not None and "-USD" in display.upper():
                price = round(price * usd_brl_rate, 2)
                
            prices[display] = price
            
    return prices

def calcular_rebalanceamento(
    portfolio,
    precos,
    aporte=0,
    tolerancia=0.5
):

    ativos = []

    # --------------------------------
    # 1. Base
    # --------------------------------

    for item in portfolio:

        ticker = item["display"]

        preco = (
            precos.get(ticker, 0)
            or 0
        )

        qtd = item.get(
            "quantidade",
            0
        )

        peso_alvo = item.get(
            "peso",
            0
        )

        valor_atual = preco * qtd

        ativos.append({

            "display": ticker,

            "quantidade": qtd,

            "preco_atual": preco,

            "valor_atual": valor_atual,

            "peso_alvo": peso_alvo,

            "peso_atual": 0,

            "peso_recomendado":
                peso_alvo * 100,

            "delta_peso": 0,

            "necessidade": 0,

            "orientacao":
                "Peso aceitável",

            "css_class": "ok",

            "sugestao_qtd": 0,

            "sugestao_valor": 0,
            
            "ignorar": item.get("ignorar", False),
        })

    valor_carteira = sum(
        a["valor_atual"]
        for a in ativos
    )

    valor_carteira_ativa = sum(
        a["valor_atual"]
        for a in ativos if not a["ignorar"]
    )

    valor_total_ativo = (
        valor_carteira_ativa +
        aporte
    )
    if valor_total_ativo == 0:
        valor_total_ativo = 1

    valor_total = (
        valor_carteira +
        aporte
    )

    if valor_total == 0:
        valor_total = 1

    # --------------------------------
    # 2. Métricas
    # --------------------------------

    for a in ativos:

        peso_atual = (
            a["valor_atual"]
            / valor_total
        ) * 100

        a["peso_atual"] = round(
            peso_atual,
            2
        )

        if a["ignorar"]:
            a["peso_alvo"] = peso_atual / 100
            a["peso_recomendado"] = round(peso_atual, 2)
            a["delta_peso"] = 0
            a["necessidade"] = 0
            a["orientacao"] = "Ignorado"
            a["css_class"] = "zero"
        else:
            peso_alvo_ativo = a["peso_alvo"] * 100
            peso_atual_ativo = (a["valor_atual"] / valor_total_ativo) * 100
            delta_ativo = peso_atual_ativo - peso_alvo_ativo

            a["delta_peso"] = round(delta_ativo, 2)
            a["necessidade"] = (a["peso_alvo"] * valor_total_ativo) - a["valor_atual"]

            if abs(delta_ativo) <= tolerancia:
                a["orientacao"] = "Peso aceitável"
                a["css_class"] = "ok"
            elif delta_ativo < -tolerancia:
                a["orientacao"] = "Comprar"
                a["css_class"] = "buy"
            else:
                a["orientacao"] = "Manter"
                a["css_class"] = "sell"

    # --------------------------------
    # 3. Distribuição
    # --------------------------------

    candidatos = [

        a for a in ativos

        if a["necessidade"] > 0
        and a["preco_atual"] > 0
    ]

    soma_necessidade = sum(
        a["necessidade"]
        for a in candidatos
    ) or 1

    saldo = aporte

    for a in candidatos:

        if saldo <= 0:
            break

        fatia = (
            a["necessidade"]
            / soma_necessidade
        ) * aporte

        valor = min(
            fatia,
            saldo
        )

        qtd = int(
            valor //
            a["preco_atual"]
        )

        a["sugestao_qtd"] = qtd

        a["sugestao_valor"] = round(
            qtd *
            a["preco_atual"],
            2
        )

        saldo -= (
            qtd *
            a["preco_atual"]
        )

    # --------------------------------
    # 4. Recalcular
    # --------------------------------

    valor_investido = (
        aporte - saldo
    )

    valor_total_final = (
        valor_carteira +
        valor_investido
    )

    valor_total_ativo_final = (
        valor_carteira_ativa +
        valor_investido
    )
    if valor_total_ativo_final == 0:
        valor_total_ativo_final = 1

    for a in ativos:

        qtd_final = (
            a["quantidade"] +
            a["sugestao_qtd"]
        )

        valor_final = (
            qtd_final *
            a["preco_atual"]
        )

        a["peso_atual"] = round(
            (
                valor_final /
                valor_total_final
            ) * 100
            if valor_total_final > 0
            else 0,
            2
        )

        if a["ignorar"]:
            a["delta_peso"] = 0
        else:
            peso_atual_ativo_final = (valor_final / valor_total_ativo_final) * 100
            a["delta_peso"] = round(
                peso_atual_ativo_final - (a["peso_alvo"] * 100),
                2
            )

    # --------------------------------
    # 5. Retorno
    # --------------------------------

    return {

        "ativos": ativos,

        "valor_carteira": round(
            valor_carteira,
            2
        ),

        "valor_total": round(
            valor_total,
            2
        ),

        "aporte": aporte,

        "saldo_nao_investido":
            round(
                saldo,
                2
            ),

        "tolerancia":
            tolerancia
    }

def aplicar_rebalanceamento(data):

    ativos = data.get("ativos", [])
    aporte = float(data.get("aporte", 0))
    saldo = float(data.get("saldo_nao_investido", 0))

    compras = [a for a in ativos if a.get("sugestao_qtd", 0) > 0]

    if not compras:
        raise ValueError("Nenhuma compra sugerida para aplicar.")

    portfolio = load_portfolio()

    # Cria o histórico de aporte no banco
    novo_historico = HistoricoAporte(
        aporte=aporte,
        saldo_nao_investido=saldo
    )
    db.session.add(novo_historico)

    for compra in compras:
        ticker = compra["display"]

        # Atualiza a carteira localmente
        for ativo in portfolio:
            if ativo["display"] == ticker:
                ativo["quantidade"] += compra["sugestao_qtd"]
                break

        # Salva o registro da compra no banco vinculado ao histórico
        nova_compra = CompraAtivo(
            historico=novo_historico,
            ticker=ticker,
            quantidade=compra["sugestao_qtd"],
            preco=compra["preco_atual"],
            valor=compra["sugestao_valor"]
        )
        db.session.add(nova_compra)

    # Salva a nova configuração da carteira no banco
    save_portfolio(portfolio)
    
    # Obs: o db.session.commit() já é chamado dentro de save_portfolio, 
    # o que salvará o novo_historico e as compras que adicionamos à sessão.

    return {
        "ok": True,
        "message": "Alterações aplicadas com sucesso."
    }
def formatar_ticker_yahoo(
    ticker: str
) -> str:

    ticker = ticker.upper()

    # Criptos
    if "-USD" in ticker:
        return ticker

    # Já vem formatado
    if ticker.endswith(".SA"):
        return ticker

    # Se terminar com número (Padrão B3: PETR4, BOVA11, AAPL34), adiciona .SA
    if ticker[-1].isdigit():
        return f"{ticker}.SA"

    # Caso contrário (Padrão Americano: AAPL, PBR, MSFT), retorna como está
    return ticker

def buscar_ativos(termo):
    """
    Busca ativos pelo nome ou ticker.
    """

    try:

        resultados = yf.Search(
            termo,
            max_results=15
        )

        ativos = []

        for item in resultados.quotes:

            ticker = item.get("symbol")

            nome = item.get("shortname") \
                or item.get("longname") \
                or ticker

            if ticker:

                ativos.append({
                    "ticker": ticker.replace(".SA", ""),
                    "nome": nome
                })

        return ativos

    except Exception:

        return []