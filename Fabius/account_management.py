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
        "INSERT INTO all_users VALUES ('fabius', '3bc49b73e2fb201924d9dcce5fb6d6fd7cfbf58c49be8cc46439c05dc634b151', 'fabius.werner@outlook.de')")
    cursor.execute("SELECT username FROM all_users WHERE username == 'fabius'")
    connection.commit()
    connection.close()


def search_username(username) -> bool:
    cursor.execute("SELECT username FROM all_users WHERE username='{username}'")
    if username == cursor.fetchone():

        return True
    else:
        return False

def search_password(username, password) -> bool:
    my_hash(password)
    cursor.execute("SELECT password_hash FROM all_users WHERE username='{username}'")
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
        cursor.execute("SELECT password_hash FROM all_users WHERE username='{username}'")
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



