import sqlite3
import hashlib
connection = sqlite3.connect("StockBroker.db")
cursor = connection.cursor()

class PASSWORD:
    password = input("")

class USERNAME:
    username = input("")

class email:
    email = input("")

def account(username, password, email):
    cursor.execute(
        f"INSERT INTO all_users VALUES ('{username}','{my_hash(password)}', '{email}')")
    connection.commit()
    connection.close()
    cursor.execute(f"SELECT username FROM all_users WHERE username = '{username}'")
    if cursor.fetchone()==username:
        return True


def search_username(username) -> bool:
    cursor.execute(f"SELECT username FROM all_users WHERE username='{username}'")
    if username == cursor.fetchone():

        return True
    else:
        return False

def search_password(username, password) -> bool:
    my_hash(password)
    cursor.execute(f"SELECT password_hash FROM all_users WHERE username='{username}'")
    if (my_hash(password) == cursor.fetchone()):
        return True
    else:
        return False


def my_hash(password):
    hashed_password = hashlib.sha256(password.encode())
    return hashed_password

def create_account(username, password, email):
    if search_username(username) :
        print("Username already exists!")
        return False
    else:
        account(username, password, email)
        if search_username(username):
            return True
        return True



def login(username, password):
    if search_username(username) and search_password(username, password):
        my_hash(password)
        cursor.execute(f"SELECT password_hash FROM all_users WHERE username='{username}'")
        if (my_hash(password) == cursor.fetchone()):
            return True

    ...
def is_format_AXA(input:str, x:str):
    if not input.count(x) == 1:  # nur ein x
        return False
    a, b = input.split(x)
    if not a or not b:
        return False
    if a == "" or b == "":
        return False
    return (a, b)



def verify_input(input: str, is_email:bool=False) -> bool:

    if is_email:
        if is_format_AXA(input, "@"):
            address, domain = is_format_AXA(input, "@")
            if is_format_AXA(domain, "."):
                return True

        return False
    return False



print(verify_input("x@x.x", is_email=True))



