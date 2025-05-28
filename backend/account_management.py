import sqlite3
import hashlib
backend_protokol = {  #Das wird verwendet, um dem Frontend (Laurens) zu kommunizieren, was passiert ist.
    "success":False,
    "user_id": None,
    "user_email": None,
    "message": "",
}
#für connect()
connection = None
cursor = None



# ---Ich erkläre dir gerne, warum das nicht geht.---
# class PASSWORD:
#     password = input("")
# class USERNAME:
#     username = input("")
#
# class email:
#     email = input("")
class ENDPOINT:
    """
    Diese Klasse soll alle Funktionen enthalten, die das Frontend aufrufen kann.
    Alle Funktionen geben immer backend_protokoll zurück.
    Dadurch ist es strukturierter und es passieren keine Fehler.
    Das @staticmethod sorgt nur dafür, dass die Funktionen normal aufgerufen werden können,
    denn eigentlich sind sie ja in der Klasse.
    Die funktionen können mit z.b. ENDPOINT.login() aufgerufen werden.
    """



    @staticmethod
    def reset_password_with_token(token, new_password) -> dict:
        output = backend_protokol
        return output

    @staticmethod
    def verify_reset_token(token) -> dict:
        output = backend_protokol
        return output

    @staticmethod
    def request_password_reset() -> dict:
        #SEND EMAIL TU USER
        output = backend_protokol
        return output

    @staticmethod
    def login(username_email, password) -> dict:
        username_email = username_email.lower()
        connect()
        output = backend_protokol
        if is_email(username_email):
            if not is_email_there(username_email):
                output["message"] = "E-mail wurde nicht gefunden. R U 4 real?"
                return output
        else:
            if not is_username_there(username_email):
                output["message"] = "Username wurde nicht gefunden. R U 4 real?"
                return output

        if not is_valid_logindata(username_email, password):
            output["success"] = True
            output["message"] = f"Welcome {username_email}!"
        else:
            output["message"] = "Wrong password. Do not pretend to be someone else's account!"

        return output


    @staticmethod
    def create_account(password, email, username="temp3"):
        output = backend_protokol
        print(password, username, email)
        if password is None or email is None or username is None:
            output["message"] = "Bitte alle Felder ausfüllen, dafür sind sie da!"
            return output

        connect()
        if is_username_there(username):
            output["message"] = "Username schon vergeben! Werde jetzt einzigartig!"
        else:
            if insert_account(username, password, email):
                output["success"] = True
                output["message"] = f"Welcome {username}!"
            else:
                output["message"] = "Fehler beim Login. Sorry :( !"
        disconnect()
        return output

    @staticmethod
    def get_all_users() -> list[dict]:
        sql_command = "SELECT username, password_hash, email, geld FROM all_users"
        keys = ["username", "password_hash", "email", "geld"]
        cursor.execute(sql_command)
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



def insert_account(username, password, email) -> bool: #Habe ich umbenannt, damit klar ist, was passiert
    cursor.execute(
        f"INSERT INTO all_users VALUES ('{username}','{my_hash(password)}', '{email}')")
    cursor.execute(f"SELECT username FROM all_users WHERE username = '{username}'")
    return is_valid_logindata(username, password)

def is_username_there(username) -> bool:
    cursor.execute(f"SELECT username FROM all_users WHERE username='{username}'")
    sql_output = cursor.fetchone()
    #print(f"searched username {username}, found: {sql_output}")
    if not sql_output is None:
        return True
    else:
        return False

def is_email_there(email) -> bool:
    cursor.execute(f"SELECT email FROM all_users WHERE email='{email}'")
    sql_output = cursor.fetchone()
    #print(f"searched username {username}, found: {sql_output}")
    if not sql_output is None:
        return True
    else:
        return False


def is_valid_logindata(username, password) -> bool:
    #my_hash(password) macht nichts
    cursor.execute(f"SELECT password_hash FROM all_users WHERE username='{username}'")
    sql_output = cursor.fetchone()
    if sql_output is None:
        return False
    return my_hash(password) == sql_output[0]

def my_hash(password) -> str:    #Vielleicht hash256() nennen?
    hashed_password = hashlib.sha256(password.encode())
    return str(hashed_password)

def is_format_AXA(input:str, x:str):
    if not input.count(x) == 1:  # nur ein x
        return False
    a, b = input.split(x)
    if not a or not b:
        return False
    if a == "" or b == "":
        return False
    return (a, b)

def is_email(email: str) -> bool:
    if is_format_AXA(input, "@"):
        address, domain = is_format_AXA(input, "@")
        if is_format_AXA(domain, "."):
            return True
    return False



def verify_input(input: str, is_email:bool=False) -> bool:
    if is_email:
        return is_email(input)
    return False


if __name__ == "__main__":   #Wird nur ausgeführt, wenn dieses Skript direct selbst ausgeführt wird.
    print(verify_input("x@x.x", is_email=True))
 #Immer Datenbank speichern


