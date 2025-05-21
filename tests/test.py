import sqlite3
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Flask App und LoginManager initialisieren
app = Flask(__name__)
app.secret_key = 'dein_secret_key'  # Ersetze dies mit einem sicheren Schlüssel

login_manager = LoginManager()
login_manager.init_app(app)

# Funktion, um eine Verbindung zur SQLite-Datenbank herzustellen
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Benutzerklasse für Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Route für die Startseite
@app.route('/')
def home():
    return render_template('index.html')

# Route für das Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)

        if user and check_password_hash(user['password'], password):
            user_obj = User(id=user['id'], username=user['username'], password=user['password'])
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            flash('Ungültige Anmeldedaten, bitte versuche es noch einmal.', 'danger')

    return render_template('login.html')

# Dashboard-Route (geschützt, nur für eingeloggte Benutzer zugänglich)
@app.route('/dashboard')
@login_required
def dashboard():
    return f'Hallo {current_user.username}, du bist eingeloggt!'

# Logout-Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Benutzer für LoginManager laden
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(id=user['id'], username=user['username'], password=user['password'])
    return None

# Benutzer nach Benutzernamen suchen
def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

# Benutzer in der Datenbank erstellen (für das Beispiel)
def create_sample_user():
    conn = get_db_connection()
    hashed_password = generate_password_hash('password123')
    conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('testuser', hashed_password))
    conn.commit()
    conn.close()

# Datenbank mit Tabelle erstellen
def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    # Optional: Ein Beispielbenutzer wird erstellt
    app.run(debug=True)
