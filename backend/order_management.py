# backend/order_management.py

import sqlite3
import uuid
from datetime import datetime, UTC



class OrderEndpoint:
    """
    Stellt statische Methoden für die Verwaltung von Handelsaufträgen bereit.
    Alle Methoden erwarten ein aktives Datenbankverbindungsobjekt 'conn'.
    """

    @staticmethod
    def place_order(conn: sqlite3.Connection, user_id: int, symbol: str, quantity: float, order_type: str, limit_price: float = None, stop_price: float = None) -> dict:
        """
        Platziert eine neue bedingte Order in der Datenbank.
        """
        if order_type not in ['LIMIT_BUY', 'LIMIT_SELL', 'STOP_SELL']:
             return {"success": False, "message": "Ungültiger Order-Typ."}

        order_id = str(uuid.uuid4())
        try:
            cursor = conn.cursor()
            sql = """
                INSERT INTO orders (order_id, user_id_fk, ticker, order_type, quantity, limit_price, stop_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """
            cursor.execute(sql, (order_id, user_id, symbol.upper(), order_type, quantity, limit_price, stop_price))
            return {"success": True, "order_id": order_id, "message": "Order erfolgreich platziert."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Datenbankfehler beim Platzieren der Order: {e}"}

    @staticmethod
    def cancel_order(conn: sqlite3.Connection, order_id: str, user_id: int) -> dict:
        """
        Storniert eine offene Order. Stellt sicher, dass nur der Besitzer die Order stornieren kann.
        """
        try:
            cursor = conn.cursor()
            # Überprüfen, ob die Order existiert, dem User gehört und offen ist.
            cursor.execute("SELECT order_id FROM orders WHERE order_id = ? AND user_id_fk = ? AND status = 'OPEN'", (order_id, user_id))
            if cursor.fetchone() is None:
                return {"success": False, "message": "Order nicht gefunden, bereits ausgeführt oder keine Berechtigung."}

            sql = "UPDATE orders SET status = 'CANCELED' WHERE order_id = ?"
            cursor.execute(sql, (order_id,))
            if cursor.rowcount > 0:
                return {"success": True, "message": "Order erfolgreich storniert."}
            else:
                 return {"success": False, "message": "Stornierung fehlgeschlagen."} # Sollte nicht eintreten
        except sqlite3.Error as e:
            return {"success": False, "message": f"Datenbankfehler: {e}"}

    @staticmethod
    def get_user_orders(conn: sqlite3.Connection, user_id: int) -> list[dict]:
        """Ruft alle Orders eines bestimmten Benutzers ab."""
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE user_id_fk = ? ORDER BY created_at DESC", (user_id,))
        orders = [dict(row) for row in cursor.fetchall()]
        conn.row_factory = None
        return orders

    @staticmethod
    def get_all_open_orders(conn: sqlite3.Connection) -> list[dict]:
        """Ruft alle Orders mit dem Status 'OPEN' ab. Für den Scheduler."""
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE status = 'OPEN'")
        orders = [dict(row) for row in cursor.fetchall()]
        conn.row_factory = None
        return orders

    @staticmethod
    def close_order(conn: sqlite3.Connection, order_id: str):
        """Ändert den Status einer Order zu 'CLOSED' und setzt die Ausführungszeit."""
        try:
            now = datetime.now(UTC)
            sql = "UPDATE orders SET status = 'CLOSED', executed_at = ? WHERE order_id = ?"
            conn.execute(sql, (now, order_id))
        except sqlite3.Error as e:
            print(f"Fehler beim Schließen der Order {order_id}: {e}")