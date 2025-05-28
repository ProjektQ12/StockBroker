def execute_trade(trade_data):
    """
    Simuliert die Ausführung eines Trades.
    In einer echten Anwendung würde hier die Logik zur Interaktion mit einer Broker-API,
    Datenbankaktualisierung etc. stattfinden.
    """
    print("--- Neuer Trade wird ausgeführt ---")
    print(f"Typ: {trade_data.get('trade_type')}")  # long, short, option
    print(f"Ticker/WKN: {trade_data.get('ticker')}")
    print(f"Menge: {trade_data.get('quantity')}")

    if trade_data.get('trade_type') == 'long':
        print(f"Order-Typ: {trade_data.get('order_type')}")  # market, limit
        if trade_data.get('order_type') == 'limit':
            print(f"Limit-Preis: {trade_data.get('limit_price')}")
        print(f"Gültigkeit: {trade_data.get('validity')}")  # day, gtc
        # ... weitere Long-spezifische Daten ...

    elif trade_data.get('trade_type') == 'short':
        print("Short-spezifische Logik hier...")
        # ...

    elif trade_data.get('trade_type') == 'option':
        print("Options-spezifische Logik hier...")
        print(f"Options-Typ (Call/Put): {trade_data.get('option_type')}")
        print(f"Strike-Preis: {trade_data.get('strike_price')}")
        print(f"Verfallsdatum: {trade_data.get('expiration_date')}")
        # ...

    print("---------------------------------")
    # Simuliere Erfolg oder Misserfolg
    # In echt: Rückmeldung von der Broker-API
    if trade_data.get('ticker'):  # Einfache Prüfung
        return {'success': True,
                'message': f"Trade für {trade_data.get('ticker')} erfolgreich übermittelt (Simulation)."}
    else:
        return {'success': False, 'message': "Fehler: Ticker fehlt (Simulation)."}