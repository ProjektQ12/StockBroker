import yfinance as yf
from backend.order_management import OrderManagement
from trading import Trading

# Der Datenbankpfad kann hier definiert oder übergeben werden.
# Für die Integration in die App ist es sauberer, wenn die Instanzen
# den Pfad von einer zentralen Konfiguration erhalten.
DATABASE_PATH = 'database.db'


def get_current_price(symbol):
    """Holt den aktuellen Marktpreis für ein Symbol über yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.info.get('regularMarketPrice') or ticker.info.get('currentPrice')
        if price is None:
            hist = ticker.history(period="2d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
        if price:
            return float(price)
        print(f"Warnung: Konnte keinen gültigen Preis für {symbol} finden.")
        return None
    except Exception as e:
        print(f"Fehler beim Abrufen des Preises für {symbol}: {e}")
        return None


def process_orders():
    """
    Die Hauptlogik zur Verarbeitung offener Orders. Diese Funktion wird
    vom Scheduler periodisch aufgerufen.
    """
    print("Scheduler-Job gestartet: Prüfe offene Orders...")
    order_manager = OrderManagement(db_path=DATABASE_PATH)
    trading_system = Trading()  # Stellt sicher, dass diese Klasse auch den DB-Pfad kennt, falls nötig
    open_orders = order_manager.get_all_open_orders()

    if not open_orders:
        print("Scheduler: Keine offenen Orders zur Verarbeitung gefunden.")
        return

    symbols_to_fetch = list(set([order['symbol'] for order in open_orders]))
    current_prices = {symbol: get_current_price(symbol) for symbol in symbols_to_fetch}

    for order in open_orders:
        order_id = order['order_id']
        user_id = order['user_id']
        symbol = order['symbol']
        order_type = order['order_type']
        quantity = order['quantity']

        current_price = current_prices.get(symbol)
        if current_price is None:
            continue

        execute_trade = False
        execution_price = None

        if order_type == 'LIMIT_BUY' and current_price <= order['limit_price']:
            execute_trade = True
            execution_price = order['limit_price']

        elif order_type == 'LIMIT_SELL' and current_price >= order['limit_price']:
            execute_trade = True
            execution_price = order['limit_price']

        elif order_type == 'STOP_LOSS' and current_price <= order['stop_price']:
            execute_trade = True
            execution_price = order['stop_price']

        if execute_trade:
            try:
                success = False
                if order_type == 'LIMIT_BUY':
                    success = trading_system.buy_stock(user_id, symbol, quantity, price=execution_price)
                elif order_type in ['LIMIT_SELL', 'STOP_LOSS']:
                    success = trading_system.sell_stock(user_id, symbol, quantity, price=execution_price)

                if success:
                    print(f"Scheduler: Trade für Order {order_id} erfolgreich. Schließe Order.")
                    order_manager.update_order_status(order_id, 'CLOSED', executed_price=execution_price)
                else:
                    print(
                        f"Scheduler: Trade für Order {order_id} fehlgeschlagen. Guthaben/Bestand prüfen. Order bleibt offen.")

            except Exception as e:
                print(f"Scheduler: Ein Fehler ist bei der Ausführung von Order {order_id} aufgetreten: {e}")

    print("Scheduler-Job beendet.")

# Die main-Funktion und der __main__-Block werden entfernt,
# da die Ausführung nun von app.py gesteuert wird.
