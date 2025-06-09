#// app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify
import yfinance as yf
import plotly.graph_objects as go
import os
import json # Added
import requests # Added
import sqlite3

from functools import wraps
from datetime import datetime, timedelta

from backend.accounts_to_database import ENDPOINT as AccountEndpoint
from trading import TRADING_ENDPOINT as TRADING
from backend.leaderboard import LeaderboardEndpoint
from backend.depot_system import DepotEndpoint

app = Flask(__name__)
app.secret_key = os.urandom(24)

#PyCharms sql modus muss beendet werden
DATABASE_FILE = "backend/StockBroker.db"

# Caching-Variable für das Leaderboard
leaderboard_cache = {"last_updated": None}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_FILE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Schließt die Datenbankverbindung am Ende des Requests."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Decorator für Login-Schutz ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bitte melde dich an, um diese Seite zu sehen.', 'warning')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


ALPHA_VANTAGE_API_KEY = None

def configure_ALPHA_VANTAGE_API():
    global ALPHA_VANTAGE_API_KEY
    try:
        with open('keys.json', 'r') as f:
            keys = json.load(f)
            ALPHA_VANTAGE_API_KEY = keys.get('alpha_vantage_api_key')
            print("key erhalten")
    except FileNotFoundError:
        print("WARNUNG: keys.json nicht gefunden.")
        raise
    except json.JSONDecodeError:
        print("WARNUNG: keys.json ist nicht valides JSON. Alpha Vantage API-Funktionalität ist deaktiviert.")
        raise
    if not ALPHA_VANTAGE_API_KEY:
        print("WARNUNG: Alpha Vantage API Key nicht in keys.json gefunden oder Datei fehlerhaft.")
        raise ValueError # Nur raise geht irgendwie nicht

configure_ALPHA_VANTAGE_API()

# -- Konstanten für Dropdown-Optionen beim Graph --
AVAILABLE_PERIODS = [
    ("5d", "5 Tage"), ("1mo", "1 Monat"), ("3mo", "3 Monate"),
    ("6mo", "6 Monate"), ("1y", "1 Jahr"), ("2y", "2 Jahre"),
    ("5y", "5 Jahre"), ("ytd", "Seit Jahresbeginn"), ("max", "Maximal")
]
AVAILABLE_QUALITIES = [
    ("high", "Hoch"), ("normal", "Normal"), ("low", "Niedrig")
]


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))

    form_data = {}
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()
        form_data['identifier'] = identifier

        if not identifier or not password:
            flash('Bitte Anmeldedaten eingeben.', 'error')
        else:
            conn = get_db()
            result = AccountEndpoint.login(conn, identifier, password)
            if result.get('success'):
                conn.commit()
                session['user_id'] = result.get('user_id')
                session['user_email'] = result.get('email')
                session['username'] = result.get('username')
                flash(result.get('message', 'Login erfolgreich!'), 'success')
                return redirect(url_for('dashboard_page'))
            else:
                flash(result.get('message', 'Login fehlgeschlagen.'), 'error')

    return render_template('auth/login.html', form_data=form_data)


@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))

    form_data = {}
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()

        form_data['email'] = email
        form_data['username'] = username

        if not email or not username or not password or not password_confirm:
            flash('Bitte alle Felder ausfüllen.', 'error')
        elif password != password_confirm:
            flash('Die Passwörter stimmen nicht überein.', 'error')
        else:
            conn = get_db()
            result = AccountEndpoint.create_account(conn, password, email, username)
            if result.get('success'):
                conn.commit()
                flash(result.get('message', 'Konto erstellt! Bitte logge dich ein.'), 'success')
                return redirect(url_for('login_page'))
            else:
                flash(result.get('message', 'Registrierung fehlgeschlagen.'), 'error')
    return render_template('auth/register.html', form_data=form_data)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('username', None)
    flash('Du wurdest erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('login_page'))


@app.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request_page():
    form_data = {}
    email_sent_flag = False
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        form_data['email'] = email
        if not email:
            flash('Bitte gib deine E-Mail-Adresse ein.', 'error')
        else:
            conn = get_db()
            result = AccountEndpoint.request_password_reset(conn, email)
            flash(result.get('message', 'Anweisungen gesendet, falls Konto existiert.'), 'info')
            email_sent_flag = True
            conn.commit()
    return render_template('auth/reset_request.html', email_sent=email_sent_flag, form_data=form_data)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_confirm_page(token):
    conn = get_db()
    token_verification = AccountEndpoint.verify_reset_token(conn, token)
    if not token_verification.get('success'):
        conn.commit()
        flash(token_verification.get('message', 'Ungültiger oder abgelaufener Link.'), 'error')
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        new_password_confirm = request.form.get('new_password_confirm')

        if not new_password or not new_password_confirm:
            flash('Bitte gib das neue Passwort zweimal ein.', 'error')
        elif new_password != new_password_confirm:
            flash('Die neuen Passwörter stimmen nicht überein.', 'error')
        elif len(new_password) < 6:
            flash('Das neue Passwort muss mindestens 6 Zeichen lang sein.', 'error')
        else:
            #conn wird oben schon gemacht
            result = AccountEndpoint.reset_password_with_token(conn, token, new_password)
            if result.get('success'):
                conn.commit()
                flash(result.get('message', 'Passwort erfolgreich geändert.'), 'success')
                return redirect(url_for('login_page'))
            else:
                flash(result.get('message', 'Fehler beim Ändern des Passworts.'), 'error')
    return render_template('auth/reset_confirm.html', token=token)


@app.route('/reset-password-enter-token', methods=['GET', 'POST'])
def reset_password_enter_token_page():
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        if not token:
            flash('Bitte gib deinen Reset-Code ein.', 'error')
        else:
            return redirect(url_for('reset_password_confirm_page', token=token))
    return render_template('auth/reset_enter_token.html')


@app.route('/trade/<string:ticker_symbol>', methods=['GET', 'POST'])
def trade_page(ticker_symbol):
    if 'user_id' not in session:
        flash('Bitte logge dich ein, um zu handeln.', 'warning')
        return redirect(url_for('login_page', next=request.url))

    ticker_symbol = ticker_symbol.upper()
    basic_info, info_error = get_stock_basic_info_yfinance(ticker_symbol) # Renamed for clarity
    if info_error or not basic_info:
        flash(f"Ticker '{ticker_symbol}' nicht gefunden oder ungültig (yfinance). Handel nicht möglich.", 'error')
        return render_template('trade_error.html', ticker=ticker_symbol)

    trade_mode = request.args.get('mode', 'long')

    current_price = basic_info.get('info_dict', {}).get('currentPrice',
                                                        basic_info.get('info_dict', {}).get('regularMarketPrice',
                                                                                            'N/A'))

    if request.method == 'POST':
        trade_data = {
            "user_id": session.get('user_id'),
            "ticker": ticker_symbol,
            "trade_type": trade_mode,
        }

        if trade_mode == 'long':
            trade_data['quantity'] = request.form.get('quantity', type=int)
            trade_data['order_type'] = request.form.get('order_type')
            if trade_data['order_type'] == 'limit':
                trade_data['limit_price'] = request.form.get('limit_price', type=float)
            else:
                trade_data['price'] = current_price
            trade_data['validity'] = request.form.get('validity')
        elif trade_mode == 'short':
            trade_data['quantity'] = request.form.get('quantity_short', type=int)
        elif trade_mode == 'option':
            trade_data['option_type'] = request.form.get('option_type_select')
            trade_data['strike_price'] = request.form.get('strike_price_option', type=float)
            trade_data['expiration_date'] = request.form.get('expiration_date_option')
            trade_data['quantity_option'] = request.form.get('quantity_option', type=int)

        if not trade_data.get('quantity') and not trade_data.get('quantity_short') and not trade_data.get('quantity_option'):
            flash('Bitte gib eine Menge ein.', 'error')
        else:
            conn = get_db()
            trade_result = TRADING.execute_trade(conn, session.get('username'), trade_data)
            if trade_result.get('success'):
                conn.commit()
                flash(trade_result.get('message'), 'success')
                return redirect(url_for('trade_page', ticker_symbol=ticker_symbol, mode=trade_mode))
            else:
                flash(trade_result.get('message'), 'error')


    #Das geld muss an trading.py
    return render_template('trade_page.html',
                           ticker=ticker_symbol,
                           company_name=basic_info.get('name', ticker_symbol),
                           current_price=current_price,
                           current_mode=trade_mode)

def get_stock_basic_info_yfinance(ticker_symbol): # Renamed to avoid conflict
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        if not info or (info.get('longName') is None and info.get('shortName') is None and info.get('symbol') is None):
            quick_hist = stock.history(period="1d")
            if quick_hist.empty:
                return None, f"Keine Informationen für Ticker '{ticker_symbol}' gefunden (yfinance). Ist der Ticker korrekt?"
            company_name = info.get('symbol', ticker_symbol)
        else:
            company_name = info.get('longName', info.get('shortName', ticker_symbol))
        return {'ticker': ticker_symbol, 'name': company_name, 'info_dict': info}, None
    except Exception as e:
        return None, f"Fehler beim Abrufen der Basisinformationen für '{ticker_symbol}' (yfinance): {str(e)}"

def search_alpha_vantage(keywords):
    """Search for stock symbols using Alpha Vantage API."""
    if not ALPHA_VANTAGE_API_KEY:
        return None, "Alpha Vantage API Key nicht konfiguriert."
    if not keywords:
        return [], None # No keywords, no results, no error

    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={keywords}&apikey={ALPHA_VANTAGE_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        if "bestMatches" in data:
            # Filter out results that are not Common Stock or ETF, or from non-US exchanges if desired
            # For now, return all matches
            return data["bestMatches"], None
        elif "Note" in data: # API limit reached or other API note
             return None, f"Alpha Vantage API Hinweis: {data.get('Note')}"
        elif "Error Message" in data:
             return None, f"Alpha Vantage API Fehler: {data.get('Error Message')}"
        else:
            return [], None # No matches or unexpected response
    except requests.exceptions.RequestException as e:
        return None, f"Netzwerkfehler bei der Verbindung zu Alpha Vantage: {str(e)}"
    except json.JSONDecodeError:
        return None, "Fehler beim Parsen der Alpha Vantage API Antwort."
    except Exception as e:
        return None, f"Unbekannter Fehler bei der Alpha Vantage Suche: {str(e)}"

def get_stock_detailed_data(ticker_symbol):
    stock_data = {'ticker': ticker_symbol, 'error': None}
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        if not info or (info.get('longName') is None and info.get('shortName') is None and info.get('symbol') is None):
            quick_hist = stock.history(period="1d")
            if quick_hist.empty:
                stock_data['error'] = f"Keine detaillierten Informationen für Ticker '{ticker_symbol}' gefunden."
                return stock_data
            stock_data['name'] = info.get('symbol', ticker_symbol) # Fallback to ticker if name is missing
        else:
            stock_data['name'] = info.get('longName', info.get('shortName', ticker_symbol))

        stock_data['info'] = info
        try:
            stock_data['financials_html'] = stock.financials.to_html(classes='table table-sm table-striped table-hover', border=0) if not stock.financials.empty else "Keine Finanzdaten verfügbar."
        except Exception:
            stock_data['financials_html'] = "Finanzdaten konnten nicht geladen werden."

        try:
            stock_data['major_holders_html'] = stock.major_holders.to_html(classes='table table-sm table-striped table-hover', border=0) if stock.major_holders is not None and not stock.major_holders.empty else "Keine Daten zu Haupteignern verfügbar."
        except Exception: stock_data['major_holders_html'] = "Daten zu Haupteignern konnten nicht geladen werden."
        try:
            stock_data['recommendations_html'] = stock.recommendations.tail(5).to_html(classes='table table-sm table-striped table-hover', border=0) if stock.recommendations is not None and not stock.recommendations.empty else "Keine Empfehlungen verfügbar."
        except Exception: stock_data['recommendations_html'] = "Empfehlungen konnten nicht geladen werden."

        quote_info = {
            "Preis": info.get("currentPrice", info.get("regularMarketPrice", "N/A")),
            "Gehandeltes Volumen": info.get("volume", "N/A"),
            "Tageshoch": info.get("dayHigh", "N/A"), "Tagestief": info.get("dayLow", "N/A"),
            "Eröffnung": info.get("open", "N/A"), "Vortagesschluss": info.get("previousClose", "N/A"),
            "Marktkapitalisierung": info.get("marketCap", "N/A"),
            "Dividendenrendite": info.get("dividendYield", "N/A")
        }
        if isinstance(quote_info.get("Marktkapitalisierung"), (int, float)): quote_info["Marktkapitalisierung"] = f"{quote_info['Marktkapitalisierung']:,}"
        if isinstance(quote_info.get("Dividendenrendite"), (int, float)): quote_info["Dividendenrendite"] = f"{quote_info['Dividendenrendite'] * 100:.2f}%"
        stock_data['quote_info'] = quote_info

    except Exception as e:
        stock_data['error'] = f"Allgemeiner Fehler beim Abrufen der Detaildaten für '{ticker_symbol}': {str(e)}"
    return stock_data

def determine_actual_interval_and_period(selected_period, selected_quality):
    actual_period = selected_period
    adjustment_note = None
    if selected_period == "5d":
        if selected_quality == "high": actual_interval = "1m"
        elif selected_quality == "normal": actual_interval = "5m"
        else: actual_interval = "15m"
    elif selected_period == "1mo":
        if selected_quality == "high": actual_interval = "5m"
        elif selected_quality == "normal": actual_interval = "30m"
        else: actual_interval = "1h"
    elif selected_period == "3mo":
        if selected_quality == "high": actual_interval = "30m"
        elif selected_quality == "normal": actual_interval = "1h"
        else: actual_interval = "1d"
    elif selected_period in ["6mo", "ytd"]:
        if selected_quality == "high": actual_interval = "1h"
        elif selected_quality == "normal": actual_interval = "1d"
        else: actual_interval = "1wk"
    elif selected_period in ["1y", "2y"]:
        if selected_quality == "high": actual_interval = "1d"
        elif selected_quality == "normal": actual_interval = "1wk"
        else: actual_interval = "1mo"
    elif selected_period in ["5y", "max"]:
        if selected_quality == "high": actual_interval = "1wk"
        elif selected_quality == "normal": actual_interval = "1mo"
        else: actual_interval = "3mo"
    else: actual_interval = "1d" # Default

    # Anpassungen basierend auf yfinance Limits für Intervalle
    original_period_for_note = actual_period
    # Für 1 m Intervall: max. 7 Tage, aber yfinance sagt oft 5d sei besser für 1 m.
    # yfinance erlaubt 1 m für bis zu 7 Tage, aber Daten sind intraday und haben nur für 5 Handelstage lückenlos.
    # Für die feinsten Auflösungen:
    if actual_interval == "1m" and actual_period not in ["1d", "2d", "3d", "4d", "5d", "7d"]: # Max 7d for 1m data
        actual_period = "5d" # Sicherer Standard für 1 m
    # Für Intervalle <60m: Daten sind für die letzten 60 Tage verfügbar
    elif actual_interval in ["2m", "5m", "15m", "30m"] and actual_period not in ["1d", "5d", "1mo", "2mo", "60d"]:
         if selected_period == "3mo" or selected_period == "6mo": actual_period = "2mo" # yf max 60d
         elif selected_period not in ["1d", "5d", "1mo"]: actual_period = "2mo" # yf max 60d
    # Für stündliche Intervalle (1h, 60m, 90m): Daten sind für die letzten 730 Tage (ca. 2 Jahre) verfügbar
    elif actual_interval in ["60m", "90m", "1h"] and actual_period not in ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "ytd", "730d"]:
        if selected_period in ["5y", "max"]: actual_period = "2y" # yf max 730d

    if original_period_for_note != actual_period:
        period_display_original = next((p[1] for p in AVAILABLE_PERIODS if p[0] == original_period_for_note), original_period_for_note)
        period_display_actual = next((p[1] for p in AVAILABLE_PERIODS if p[0] == actual_period), actual_period)
        quality_display = next((q[1] for q in AVAILABLE_QUALITIES if q[0] == selected_quality), selected_quality)
        adjustment_note = (f"Hinweis: Zeitraum für Qualität '{quality_display}' und ursprüngliche Auswahl '{period_display_original}' "
                           f"auf '{period_display_actual}' angepasst, um Intervall '{actual_interval}' zu unterstützen.")
    return actual_period, actual_interval, adjustment_note

def generate_stock_plotly_chart(ticker_symbol, period="1y", interval="1d", quality_note=None, remove_gaps=True):
    chart_html = None
    error_msg = quality_note if quality_note else None
    company_name = ticker_symbol

    try:
        stock = yf.Ticker(ticker_symbol)
        info_temp = stock.info # Versuch, den Namen zu bekommen
        if info_temp and (info_temp.get('longName') or info_temp.get('shortName')):
            company_name = info_temp.get('longName', info_temp.get('shortName', ticker_symbol))
        elif info_temp and info_temp.get('market') == 'cccrypto_market': # For crypto, name might be in 'name'
             company_name = info_temp.get('name', company_name)


        # prepost=False, da es sonst zu Problemen mit Wochenend-Lücken kommen kann
        hist_data = stock.history(period=period, interval=interval, auto_adjust=True, prepost=False)

        if hist_data.empty:
            current_err = f"Keine Kursdaten für '{ticker_symbol}' mit Periode '{period}' und Intervall '{interval}' gefunden."
            error_msg = (error_msg + " | " if error_msg else "") + current_err
        else:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=hist_data.index,
                                         open=hist_data['Open'], high=hist_data['High'],
                                         low=hist_data['Low'], close=hist_data['Close'],
                                         name=f'{ticker_symbol}'))

            period_display = next((p[1] for p in AVAILABLE_PERIODS if p[0] == period), period)
            interval_map_for_display = {"1m":"1 Min", "2m":"2 Min", "5m":"5 Min", "15m":"15 Min", "30m":"30 Min",
                                        "60m":"1 Std", "1h":"1 Std", "90m":"90 Min", "1d":"Täglich",
                                        "1wk":"Wöchentlich", "1mo":"Monatlich", "3mo":"Quartalsweise"}
            interval_display = interval_map_for_display.get(interval, interval)

            fig.update_layout(
                title=f'Kurs: {company_name} ({ticker_symbol})<br><span style="font-size:0.8em;">Zeitraum: {period_display}, Auflösung: {interval_display}</span>',
                xaxis_title='Datum / Uhrzeit', yaxis_title='Preis',
                xaxis_rangeslider_visible=False,
                margin=dict(l=50, r=20, t=80, b=50) # Adjusted margins
            )

            if remove_gaps:
                # Filter out non-TRADING days more reliably for various intervals
                if interval in ["1d", "1wk", "1mo", "3mo"]: # For daily and longer, Sat/Sun are the primary gaps
                     fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
                elif 'm' in interval or 'h' in interval: # For intraday, also consider typical market non-TRADING times
                    # This is complex as it depends on the exchange.
                    # A general approach is to remove weekends. More specific non-TRADING hours are harder.
                    fig.update_xaxes(rangebreaks=[
                        dict(bounds=["sat", "mon"]), # Weekends
                        # dict(pattern="hour", bounds=[16, 9.5]) # Example for US market, but timezone sensitive
                    ])
            chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    #except Exception as e:
     #   current_err = f"Fehler beim Generieren des Charts (Periode: {period}, Intervall: {interval}): {str(e)}"
      #  if "No data found for this date range" in str(e) or "yfinance failed to decrypt Yahoo data" in str(e):
       #     current_err = f"Keine Daten für '{ticker_symbol}' im Zeitraum '{period}' mit Intervall '{interval}'. Kombination ungültig oder Ticker nicht verfügbar."
        #error_msg = (error_msg + " | " if error_msg else "") + current_err
    except Exception as e:
        exception_str = str(e)
        # Verwende den bereits ermittelten company_name oder den ticker_symbol für die Fehlermeldung
        display_ticker_name = company_name if company_name and company_name != ticker_symbol else ticker_symbol
        current_err_intro = f"Fehler beim Generieren des Charts für '{display_ticker_name}' (Periode: {period}, Intervall: {interval}): "

        if "HTTP Error 404" in exception_str:
            current_err = f"{current_err_intro}Daten nicht gefunden (HTTP 404). Wahrscheinlich ist diese Aktie nicht bei yfinance"
        elif "No data found for this date range" in exception_str or "yfinance failed to decrypt Yahoo data" in exception_str:
            current_err = f"{current_err_intro}Keine Daten für diese Auswahl. Die Kombination ist evtl. ungültig oder der Ticker nicht verfügbar."
        # Spezifischerer Check für "pattern not found" was auf ein Problem mit dem Ticker hindeuten kann
        elif "pattern_forms:" in exception_str and "No pattern found for" in exception_str:  # Bsp: "pattern_forms: No pattern found for stock OQFT.LON"
            current_err = f"{current_err_intro}Das Tickersymbol '{ticker_symbol}' scheint ungültig oder nicht unterstützt zu sein."
        else:
            current_err = f"{current_err_intro}{exception_str}"  # Original-Fallback

        error_msg = (error_msg + " | " if error_msg and error_msg not in current_err else "") + current_err

    return chart_html, error_msg, company_name


@app.route('/dashboard')
@login_required
def dashboard_page():
    user_id = session['user_id']
    db = get_db()
    depot_data = DepotEndpoint.get_depot_details(db, user_id)

    if depot_data is None:
        flash("Fehler: Dein Benutzerkonto konnte nicht gefunden werden.", 'error')
        return redirect(url_for('logout'))

    return render_template('depot.html', depot=depot_data)


@app.route('/', methods=['GET'])
def landing_page():
    # Redirect to search page instead of login if not logged in, or dashboard if logged in
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))
    return redirect(url_for('search_stock_page'))


@app.route('/search', methods=['GET']) # Changed to only GET, search query via args
def search_stock_page():
    query = request.args.get('keywords', '').strip()
    results = None
    error = None

    if query:
        if not ALPHA_VANTAGE_API_KEY:
            error = "Alpha Vantage API Key nicht konfiguriert. Die Suche ist deaktiviert."
            flash(error, 'error')
        else:
            results, error = search_alpha_vantage(query)
            if error:
                flash(error, 'error')
            elif not results:
                flash(f"Keine Ergebnisse für '{query}' gefunden.", 'info')
    # If no query, just show the search page
    return render_template('search_page.html', query=query, results=results, error=error)


@app.route('/stock/<string:ticker_symbol>')
def stock_detail_page(ticker_symbol):
    ticker_symbol = ticker_symbol.upper()
    stock_details = get_stock_detailed_data(ticker_symbol) # Uses yfinance

    selected_period = request.args.get('period', '1y')
    selected_quality = request.args.get('quality', 'normal')
    remove_gaps_str = request.args.get('remove_gaps', 'on')
    remove_gaps_bool = remove_gaps_str == 'on'

    if not any(p[0] == selected_period for p in AVAILABLE_PERIODS): selected_period = '1y'
    if not any(q[0] == selected_quality for q in AVAILABLE_QUALITIES): selected_quality = 'normal'

    actual_period, actual_interval, adjustment_note = determine_actual_interval_and_period(selected_period, selected_quality)

    chart_html, chart_error_msg, _ = generate_stock_plotly_chart(ticker_symbol,
                                                                 period=actual_period,
                                                                 interval=actual_interval,
                                                                 quality_note=adjustment_note,
                                                                 remove_gaps=remove_gaps_bool)

    overall_error = chart_error_msg if chart_error_msg else stock_details.get('error')
    if overall_error and adjustment_note and "Hinweis:" in adjustment_note and "Fehler:" not in adjustment_note:
        # If there's an error but also a non-error adjustment note, prioritize the note if it's just informational
        if not chart_error_msg and not stock_details.get('error'): # if the only "error" is the note
             overall_error = adjustment_note
        elif adjustment_note not in overall_error : # append note if not already part of error
             overall_error = f"{adjustment_note} | {overall_error}"


    return render_template('stock_detail_page.html',
                           ticker=ticker_symbol,
                           details=stock_details,
                           chart_html=chart_html,
                           error=overall_error,
                           current_period=selected_period,
                           current_quality=selected_quality,
                           current_remove_gaps=remove_gaps_bool,
                           available_periods=AVAILABLE_PERIODS,
                           available_qualities=AVAILABLE_QUALITIES)


@app.route('/leaderboard')
def leaderboard_page():
    db = get_db()
    now = datetime.now()

    last_update = leaderboard_cache.get("last_updated")
    if not last_update or (now - last_update) > timedelta(minutes=10):
        print("Leaderboard wird neu berechnet...")
        LeaderboardEndpoint.update_all_net_worths(db)
        db.commit()
        leaderboard_cache["last_updated"] = now

    page = request.args.get('page', 1, type=int)
    page_size = 50
    leaderboard_data = LeaderboardEndpoint.get_paginated_leaderboard(db, page=page, page_size=page_size)

    # Gesamtanzahl der Einträge für die Seitennavigation holen
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM leaderboard")
    total_entries = cursor.fetchone()[0]
    total_pages = (total_entries + page_size - 1) // page_size

    return render_template('leaderboard.html', leaderboard_data=leaderboard_data, current_page=page,
                           total_pages=total_pages)

#------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bitte melde dich an, um diese Seite zu sehen.', 'warning')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/api/refresh-depot', methods=['POST'])
@login_required
def api_refresh_depot():
    now = datetime.now()
    last_refresh = session.get('last_depot_refresh')

    # Timezone-naive datetime Objekte für den Vergleich erstellen
    if last_refresh and (now - datetime.fromisoformat(last_refresh)) < timedelta(minutes=1):
        return jsonify({"success": False, "message": "Bitte warte eine Minute vor der nächsten Aktualisierung."}), 429

    user_id = session['user_id']
    db = get_db()
    depot_data = DepotEndpoint.get_depot_details(db, user_id)

    session['last_depot_refresh'] = now.isoformat()
    flash('Depot erfolgreich aktualisiert!', 'success')
    return jsonify({"success": True, "data": depot_data})


@app.route('/test_graph')
def test_graph_page():
    # Use a common ticker for testing, e.g., AAPL or one passed as arg
    fixed_ticker = request.args.get("ticker", "AAPL").upper()
    selected_period = request.args.get("period", "6mo")
    selected_quality = request.args.get("quality", "high")
    remove_gaps_str = request.args.get('remove_gaps', 'on')
    remove_gaps_bool = remove_gaps_str == 'on'

    if not any(p[0] == selected_period for p in AVAILABLE_PERIODS): selected_period = '6mo'
    if not any(q[0] == selected_quality for q in AVAILABLE_QUALITIES): selected_quality = 'high'

    actual_period, actual_interval, adjustment_note = determine_actual_interval_and_period(selected_period, selected_quality)

    chart_html, error_msg, company_name = generate_stock_plotly_chart(fixed_ticker,
                                                                      period=actual_period,
                                                                      interval=actual_interval,
                                                                      quality_note=adjustment_note,
                                                                      remove_gaps=remove_gaps_bool)
    # Logic to display company name if ticker is not the default
    if fixed_ticker != "AAPL" and not company_name or company_name == fixed_ticker:
        basic_info, _ = get_stock_basic_info_yfinance(fixed_ticker)
        if basic_info and basic_info.get('name'):
            company_name = basic_info.get('name')

    return render_template('test_graph_page.html',
                           ticker=fixed_ticker,
                           company_name=company_name,
                           chart_html=chart_html,
                           error=error_msg,
                           current_period=selected_period,
                           current_quality=selected_quality,
                           current_remove_gaps=remove_gaps_bool,
                           actual_period_used=actual_period,
                           actual_interval_used=actual_interval,
                           available_periods=AVAILABLE_PERIODS,
                           available_qualities=AVAILABLE_QUALITIES)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False) #Wir nutzen 5001 wegen Mac