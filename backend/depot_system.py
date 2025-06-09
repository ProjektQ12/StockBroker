# backend/depot_system.py

import sqlite3
import yfinance as yf
import pandas as pd  # yfinance gibt pandas-Datenstrukturen zurück
from backend.accounts_to_database import ENDPOINT


class DepotEndpoint:
    """Bündelt die Logik zur Abfrage und Berechnung von Depot-Daten."""

    @staticmethod
    def get_depot_details(conn: sqlite3.Connection, user_id: int) -> dict | None:
        """
        Sammelt alle relevanten Informationen für die Depot-Ansicht eines Benutzers.
        - Barbestand
        - Aktienpositionen
        - Aktuelle Kurse und Werte
        - Gesamtvermögen
        """
        cursor = conn.cursor()

        # 1. Barbestand holen
        cash_balance = ENDPOINT.get_balance(conn, username=None, user_id=user_id)
        if cash_balance is None:
            return None

        # 2. Alle Positionen des Users aus dem Depot holen
        cursor.execute(
            "SELECT ticker, quantity, average_purchase_price FROM stock_depot WHERE user_id_fk = ?",
            (user_id,)
        )
        positions_raw = cursor.fetchall()

        tickers = [pos[0] for pos in positions_raw]
        portfolio_value = 0.0
        positions_detailed = []

        # 3. Aktuelle Kurse für alle Ticker im Depot abfragen (falls vorhanden)
        if tickers:
            try:
                # Batch-Download für bessere Performance
                data = yf.download(tickers, period="1d", progress=False, group_by='ticker')

                for ticker, quantity, avg_price in positions_raw:
                    current_price = None
                    current_value = None
                    if not data.empty and ticker in data and not pd.isna(data[ticker]['Close'].iloc[-1]):
                        current_price = data[ticker]['Close'].iloc[-1]
                        current_value = quantity * current_price
                        portfolio_value += current_value

                    positions_detailed.append({
                        "ticker": ticker,
                        "quantity": quantity,
                        "average_purchase_price": avg_price,
                        "current_price": current_price,
                        "current_value": current_value
                    })

            except Exception as e:
                print(f"Fehler beim Abrufen der Depot-Preise: {e}")
                # Fallback, um das Depot auch ohne Live-Preise anzuzeigen
                for ticker, quantity, avg_price in positions_raw:
                    positions_detailed.append({
                        "ticker": ticker, "quantity": quantity, "average_purchase_price": avg_price,
                        "current_price": None, "current_value": None
                    })

        # 4. Gesamtergebnis zusammenstellen
        total_net_worth = cash_balance + portfolio_value

        return {
            "user_id": user_id,
            "cash_balance": cash_balance,
            "portfolio_value": portfolio_value,
            "total_net_worth": total_net_worth,
            "positions": positions_detailed
        }