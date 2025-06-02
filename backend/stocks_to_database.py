#aktiein liste zu depot hinzufügen können
#depot von user ausgeben
# hat user anlage bei wkn
import sqlite3



def get_stocks(username):
    connect()
    keys = ("username", "wkn", "amount", "bought_price", "bought_date")
    sql_command = f"SELECT {', '.join(keys)} FROM stock_depot WHERE username = '{username}'"
    cursor.execute(sql_command)
    out = [{k: v for k, v in zip(keys, values)} for values in cursor.fetchall()]
    disconnect()
    return out

def connect():
    global connection, cursor
    connection = sqlite3.connect("backend/StockBroker.db")
    cursor = connection.cursor()

def disconnect():
    global connection, cursor
    connection.commit()
    connection.close()

