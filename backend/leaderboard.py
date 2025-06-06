import sqlite3
from datetime import datetime

database_name = "stock_depot"






class ENDPOINT:
    @staticmethod
    def update_leaderboard():
        pass
def user_update_leaderboard(username, net_worth, joined_date):
    connect()
    sql_command = "INSERT OR REPLACE INTO leaderboard VALUES (?, ?, ?, ?)"

    values_to_insert = (
        username,
        net_worth,
        joined_date,
        datetime.now().strftime('%Y-%m-%d %H:%M:%f')
    )

    cursor.execute(sql_command, values_to_insert)


def is_username_in_db(username) -> bool:
    cursor.execute(f"SELECT username FROM leaderboard WHERE username='{username}'")
    sql_output = cursor.fetchone()
    #print(f"searched username {username}, found: {sql_output}")
    if not sql_output is None:
        return True
    else:
        return False

def connect():
    global connection, cursor
    connection = sqlite3.connect("backend/StockBroker.db")
    cursor = connection.cursor()

def disconnect():
    global connection, cursor
    connection.commit()
    connection.close()