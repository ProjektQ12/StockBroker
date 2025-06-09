# trading_system.py
"""
Implementiert das Handelssystem mit einer dedizierten Endpunkt-Klasse.
Nutzt die UTILITIES-Klasse für allgemeine Datenbankabfragen.
"""

import sqlite3
from datetime import datetime

# GEÄNDERT: Importiert die UTILITIES und den AccountEndpoint aus dem Account-Modul
from backend.accounts_to_database import UTILITIES, ENDPOINT as AccountEndpoint


# --- Private Hilfsfunktionen für das Trading-System ---

def _update_portfolio_position(conn: sqlite3.Connection, user_id: int, ticker: str, quantity_change: int, price: float):
    """
    Aktualisiert eine Position im Portfolio.
    VERWENDET JETZT DEN TABELLENNAMEN 'stock_depot'.
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute(
        "SELECT quantity, average_purchase_price FROM stock_depot WHERE user_id_fk = ? AND ticker = ?",
        (user_id, ticker)
    )
    position = cursor.fetchone()

    if position:
        # UPDATEN
        # ... (Logik wie zuvor) ...
        current_quantity, current_avg_price = position
        new_quantity = current_quantity + quantity_change
        new_avg_price = ((current_quantity * current_avg_price) + (quantity_change * price)) / new_quantity
        sql = "UPDATE stock_depot SET quantity = ?, average_purchase_price = ?, last_updated = ? WHERE user_id_fk = ? AND ticker = ?"
        cursor.execute(sql, (new_quantity, new_avg_price, now, user_id, ticker))
    else:
        # NEU ANLEGEN
        sql = "INSERT INTO stock_depot (user_id_fk, ticker, quantity, average_purchase_price, last_updated) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(sql, (user_id, ticker, quantity_change, price, now))


# --- Klassen für die verschiedenen Trade-Typen (bleiben intern) ---

class BaseTrade:
    def __init__(self, trade_data: dict, username: str):
        # ... (wie zuvor) ...
        self.trade_type = trade_data.get("trade_type")
        self.ticker = trade_data.get("ticker")
        self.quantity = int(trade_data.get("quantity", 0))
        self.price = float(trade_data.get("price", 0.0))
        self.price_sum = self.quantity * self.price
        self.username = username

        if not all([self.ticker, self.quantity > 0, self.price > 0]):
            raise ValueError("Ungültige Auftragsdaten: Ticker, Menge und Preis müssen angegeben werden.")

    def execute(self, conn: sqlite3.Connection) -> dict:
        raise NotImplementedError("Muss in Unterklasse implementiert werden.")


class LongTrade(BaseTrade):
    def execute(self, conn: sqlite3.Connection) -> dict:
        # GEÄNDERT: Nutzt jetzt die zentrale UTILITIES-Klasse
        user_id = UTILITIES.get_user_id(conn, self.username)
        if not user_id:
            return {"success": False, "message": "Benutzer nicht gefunden."}

        current_balance = AccountEndpoint.get_balance(conn, username=self.username)
        if current_balance is None or current_balance < self.price_sum:
            return {"success": False,
                    "message": f"Nicht genug Geld. Benötigt: {self.price_sum:.2f}€, Verfügbar: {current_balance:.2f}€"}

        try:
            AccountEndpoint.update_balance(conn, self.username, -self.price_sum)
            _update_portfolio_position(conn, user_id, self.ticker, self.quantity, self.price)
            return {"success": True,
                    "message": f"Kauf von {self.quantity}x {self.ticker} für {self.price_sum:.2f}€ erfolgreich."}
        except Exception as e:
            return {"success": False, "message": f"Trade fehlgeschlagen: {e}"}


# ... (ShortTrade, OptionTrade Klassen wie zuvor) ...

# --- Factory-Funktion (bleibt intern) ---

def _create_trade(trade_data: dict, username: str) -> BaseTrade:
    trade_type = trade_data.get("trade_type")
    if trade_type == "long":
        return LongTrade(trade_data, username)
    # ... (Rest der Factory wie zuvor) ...
    else:
        raise ValueError(f"Unbekannter Trade-Typ: {trade_type}")


# --- NEU: Die öffentliche Endpunkt-Klasse für das Trading ---

class TRADING_ENDPOINT:
    """
    Diese Klasse ist der öffentliche Einstiegspunkt für alle Handelsoperationen.
    Sie kapselt die Komplexität der Trade-Erstellung und -Ausführung.
    """

    @staticmethod
    def execute_trade(conn: sqlite3.Connection, username: str, trade_data: dict) -> dict:
        """
        Nimmt Handelsdaten entgegen, erstellt das passende Trade-Objekt und führt es aus.
        Gibt ein standardisiertes Protokoll-Dictionary zurück.
        """
        # Holt das Basisprotokoll aus der zentralen Utility-Klasse
        output = UTILITIES.get_base_protocol()
        try:
            # Die interne Factory erstellt das richtige Objekt
            trade_object = _create_trade(trade_data, username)
            # Das Objekt führt sich selbst aus
            result = trade_object.execute(conn)
            return result

        except (ValueError, NotImplementedError) as e:
            output["message"] = str(e)
            return output
        except Exception as e:
            # Fängt unerwartete Fehler ab
            output["message"] = f"Ein unerwarteter Fehler ist aufgetreten: {e}"
            return output