#aktiein liste zu depot hinzufügen können
#depot von user ausgeben
# hat user anlage bei wkn
import sqlite3
from datetime import datetime

database_name = "stock_depot"
keys = ("username", "wkn", "amount", "bought_price", "bought_date", "displayname")


class ENDPOINT:
    @staticmethod
    def get_stocks(username):
        connect()
        sql_command = f"SELECT {', '.join(keys)} FROM stock_depot WHERE username = '{username}'"
        cursor.execute(sql_command)
        out = [{k: v for k, v in zip(keys, values)} for values in cursor.fetchall()]
        disconnect()
        return out

    @staticmethod
    def insert_stock(username, wkn, amount, bought_price, bought_date, displayname):
        connect()
        cursor.execute(
            f"INSERT INTO {database_name} VALUES ('{username}','{wkn}', '{amount}', '{bought_price}', '{datetime.now().strftime('%Y-%m-%d %H:%M:%f')}', '{displayname}')"
        )
        disconnect()
        return True

    @staticmethod
    def get_all_stocks_of_user(username) -> list:
        cursor.execute(
            f"SELECT all FROM stock_depot WHERE username = '{username}'"
        )
        out = [{k: v for k, v in zip(keys, values)} for values in cursor.fetchall()]
        return out



def connect():
    global connection, cursor
    connection = sqlite3.connect("backend/StockBroker.db")
    cursor = connection.cursor()

def disconnect():
    global connection, cursor
    connection.commit()
    connection.close()

