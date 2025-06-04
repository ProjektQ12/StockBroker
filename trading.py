from backend.accounts_to_database import ENDPOINT as acc
from backend import stocks_to_database
backend_protokol = {  #Das wird verwendet, um dem Frontend (Laurens) zu kommunizieren, was passiert ist.
    "success":False,
    "user_id": None,
    "user_email": None,
    "message": "",
}
class TRADE:
    protocol = {
        "trade_type":"long, short, option",

        "order_type":"limit, market",
        "limit_price": .0,
        "validity": "",

        "ticker": "",
        "quantity": 0,
        "price": .0,
        "price_sum": .0,
    }
def execute_trade(trade, username):
    out = backend_protokol.copy()
    """
    Simuliert die Ausführung eines Trades.
    In einer echten Anwendung würde hier die Logik zur Interaktion mit einer Broker-API,
    Datenbankaktualisierung etc. stattfinden.
    """
    print("--- Neuer Trade wird ausgeführt ---")
    print(f"Typ: {trade.get('trade_type')}")  # long, short, option
    print(f"Ticker/WKN: {trade.get('ticker')}")
    print(f"Menge: {trade.get('quantity')}")

    trade["price_sum"] = trade.get("price") * trade.get("quantity")
    if acc.get_money(username) < trade.get("price_sum"):
        out["message"] = f"Nicht genug Geld! Du hast nur {acc.get_money(username)}"


    if trade.get('trade_type') == 'long':
        print(f"Order-Typ: {trade.get('order_type')}")  # market, limit
        if trade.get('order_type') == 'limit':
            print(f"Limit-Preis: {trade.get('limit_price')}")
        print(f"Gültigkeit: {trade.get('validity')}")  # day, gtc
        # ... weitere Long-spezifische Daten ...

    elif trade.get('trade_type') == 'short':
        print("Short-spezifische Logik hier...")
        # ...

    elif trade.get('trade_type') == 'option':
        print("Options-spezifische Logik hier...")
        print(f"Options-Typ (Call/Put): {trade.get('option_type')}")
        print(f"Strike-Preis: {trade.get('strike_price')}")
        print(f"Verfallsdatum: {trade.get('expiration_date')}")
        # ...

    print("---------------------------------")
    # Simuliere Erfolg oder Misserfolg
    # In echt: Rückmeldung von der Broker-API
    if trade.get('ticker'):  # Einfache Prüfung
        return {'success': True,
                'message': f"Trade für {trade.get('ticker')} erfolgreich übermittelt (Simulation)."}
    else:
        return {'success': False, 'message': "Fehler: Ticker fehlt (Simulation)."}

