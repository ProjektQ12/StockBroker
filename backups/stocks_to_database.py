#aktiein liste zu depot hinzufügen können
#depot von user ausgeben
# hat user anlage bei wkn
from datetime import datetime

database_name = "stock_depot"
keys = ("username", "wkn", "amount", "bought_price", "bought_date", "displayname")


class ENDPOINT:
    @staticmethod
    def get_stocks(conn, username):
        cursor = conn.cursor()
        sql_command = f"SELECT {', '.join(keys)} FROM stock_depot WHERE username = '{username}'"
        cursor.execute(sql_command)
        out = [{k: v for k, v in zip(keys, values)} for values in cursor.fetchall()]
        return out

    @staticmethod
    def insert_stock(conn, username, wkn, amount, bought_price, bought_date, displayname):
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO {database_name} VALUES ('{username}','{wkn}', '{amount}', '{bought_price}', '{datetime.now().strftime('%Y-%m-%d %H:%M:%f')}', '{displayname}')"
        )
        return True

    @staticmethod
    def get_all_stocks_of_user(conn, username) -> list:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT all FROM stock_depot WHERE username = '{username}'"
        )
        out = [{k: v for k, v in zip(keys, values)} for values in cursor.fetchall()]
        return out




