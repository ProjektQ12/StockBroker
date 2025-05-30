from flask import Flask, render_template, request, redirect, url_for, flash, session
import yfinance as yf
import plotly.graph_objects as go
import os
import pandas as pd
from backend.account_management import ENDPOINT as acc
import trading


app = Flask(__name__)
app.secret_key = os.urandom(24)


# -- Konstanten für Dropdown-Optionen (bleiben gleich) --
AVAILABLE_PERIODS = [
    ("5d", "5 Tage"), ("1mo", "1 Monat"), ("3mo", "3 Monate"),
    ("6mo", "6 Monate"), ("1y", "1 Jahr"), ("2y", "2 Jahre"),
    ("5y", "5 Jahre"), ("ytd", "Seit Jahresbeginn"), ("max", "Maximal")
]
AVAILABLE_QUALITIES = [
    ("high", "Hoch"), ("normal", "Normal"), ("low", "Niedrig")
]


@app.route('/login', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))

    form_data = {}  # Für vorausgefüllte Felder bei Fehler
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()  # Kann Email oder Username sein
        password = request.form.get('password', '').strip()
        form_data['identifier'] = identifier  # Merken für erneute Anzeige

        if not identifier or not password:
            flash('Bitte Anmeldedaten eingeben.', 'error')
        else:
            result = acc.login(identifier, password)
            if result.get('success'):
                session['user_id'] = result.get('user_id')
                session['user_email'] = result.get('email')  # acc.login sollte die Email zurückgeben
                session['username'] = result.get('username')  # und den Username
                flash(result.get('message', 'Login erfolgreich!'), 'success')
                return redirect(url_for('dashboard_page'))
            else:
                flash(result.get('message', 'Login fehlgeschlagen.'), 'error')
                # Hier form_data nicht löschen, wird ans Template übergeben

    return render_template('auth/login.html', form_data=form_data)


@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))

    form_data = {}  # Für vorausgefüllte Felder bei Fehler
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()  # NEU
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()

        # Formularwerte für erneute Anzeige merken
        form_data['email'] = email
        form_data['username'] = username

        if not email or not username or not password or not password_confirm:
            flash('Bitte alle Felder ausfüllen.', 'error')
        elif password != password_confirm:
            flash('Die Passwörter stimmen nicht überein.', 'error')
        # Die Prüfung auf Passwortlänge und ob Email/Username existiert,
        # sollte deine acc.create_account() Funktion übernehmen und eine passende Fehlermeldung zurückgeben.
        else:
            # acc.create_account MUSS jetzt auch den Username als Parameter erwarten
            result = acc.create_account(password, email, username)
            if result.get('success'):
                flash(result.get('message', 'Konto erstellt! Bitte logge dich ein.'), 'success')
                return redirect(url_for('login_page'))  # Nach erfolgreicher Registrierung zum Login
            else:
                flash(result.get('message', 'Registrierung fehlgeschlagen.'), 'error')
                # Hier form_data nicht löschen, wird ans Template übergeben

    # Übergebe form_data an das Template, damit Felder bei Fehlern vorausgefüllt werden können
    return render_template('auth/register.html', form_data=form_data)


# --- logout, reset_password_request_page, reset_password_confirm_page, dashboard_page bleiben gleich ---
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
            result = acc.request_password_reset(email)
            flash(result.get('message', 'Anweisungen gesendet, falls Konto existiert.'), 'info')
            email_sent_flag = True  # Um das Formular auszublenden und nur die Nachricht anzuzeigen
    return render_template('auth/reset_request.html', email_sent=email_sent_flag, form_data=form_data)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_confirm_page(token):
    token_verification = acc.verify_reset_token(token)
    if not token_verification.get('success'):
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
            result = acc.reset_password_with_token(token, new_password)
            if result.get('success'):
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
            # Weiterleiten zur Bestätigungsseite mit dem eingegebenen Token
            return redirect(url_for('reset_password_confirm_page', token=token))
    return render_template('auth/reset_enter_token.html')


@app.route('/trade/<string:ticker_symbol>', methods=['GET', 'POST'])
def trade_page(ticker_symbol):
    if 'user_id' not in session:  # Login erforderlich
        flash('Bitte logge dich ein, um zu handeln.', 'warning')
        return redirect(url_for('login_page', next=request.url))

    ticker_symbol = ticker_symbol.upper()
    # Prüfen, ob der Ticker gültig ist (rudimentär mit yfinance)
    basic_info, info_error = get_stock_basic_info(ticker_symbol)
    if info_error or not basic_info:
        flash(f"Ticker '{ticker_symbol}' nicht gefunden oder ungültig. Handel nicht möglich.", 'error')
        return render_template('trade_error.html', ticker=ticker_symbol)

    # Aktueller Trade-Modus (long, short, option) aus URL oder Default
    trade_mode = request.args.get('mode', 'long')  # Standardmäßig 'long'

    if request.method == 'POST':
        # Sammle Daten aus dem Formular - abhängig vom trade_mode
        trade_data = {
            "user_id": session.get('user_id'),
            "ticker": ticker_symbol,
            "trade_type": trade_mode,  # Wichtig für trading.py
            "timestamp": pd.Timestamp.now().isoformat()  # Zeitstempel
        }

        if trade_mode == 'long':
            trade_data['quantity'] = request.form.get('quantity', type=int)
            trade_data['order_type'] = request.form.get('order_type')  # 'market' or 'limit'
            if trade_data['order_type'] == 'limit':
                trade_data['limit_price'] = request.form.get('limit_price', type=float)
            trade_data['validity'] = request.form.get('validity')  # 'day' or 'gtc'
            # Füge hier weitere Felder für Long hinzu, falls nötig

        elif trade_mode == 'short':
            # Hier Felder für Short-Orders sammeln
            trade_data['quantity'] = request.form.get('quantity_short', type=int)
            # ... (weitere Short-spezifische Felder)
            pass  # Platzhalter

        elif trade_mode == 'option':
            # Hier Felder für Options-Orders sammeln
            trade_data['option_type'] = request.form.get('option_type_select')  # 'call' or 'put'
            trade_data['strike_price'] = request.form.get('strike_price_option', type=float)
            trade_data['expiration_date'] = request.form.get('expiration_date_option')
            trade_data['quantity_option'] = request.form.get('quantity_option', type=int)
            # ... (weitere Options-spezifische Felder)
            pass  # Platzhalter

        # Validierung der Eingaben (Beispiel)
        if not trade_data.get('quantity') and not trade_data.get('quantity_short') and not trade_data.get(
                'quantity_option'):
            flash('Bitte gib eine Menge ein.', 'error')
        else:
            # Übergabe an das trading-Modul
            trade_result = trading.execute_trade(trade_data)
            if trade_result.get('success'):
                flash(trade_result.get('message'), 'success')
                # Ggf. Weiterleitung zu einer Order-Bestätigungsseite oder Depotübersicht
                return redirect(url_for('trade_page', ticker_symbol=ticker_symbol, mode=trade_mode))
            else:
                flash(trade_result.get('message'), 'error')

    # Hole aktuelle Preisinfo für Anzeige (optional, aber nützlich)
    current_price = basic_info.get('info_dict', {}).get('currentPrice',
                                                        basic_info.get('info_dict', {}).get('regularMarketPrice',
                                                                                            'N/A'))

    return render_template('trade_page.html',
                           ticker=ticker_symbol,
                           company_name=basic_info.get('name', ticker_symbol),
                           current_price=current_price,
                           current_mode=trade_mode)

# Beispiel für eine Seite, die Login erfordert
@app.route('/dashboard')  # Deine geschützte Hauptseite
def dashboard_page():  # Name geändert, um Kollision mit YFinance-Index zu vermeiden
    if 'user_id' not in session:
        flash('Bitte logge dich ein, um diese Seite zu sehen.', 'warning')
        return redirect(url_for('login_page'))
    user_email = session.get('user_email', 'Unbekannter User')
    return render_template('dashboard.html', user_email=user_email)


# -- HELPER FUNKTIONEN (get_stock_basic_info, get_stock_detailed_data, determine_actual_interval_and_period bleiben wie im vorherigen Schritt) --
def get_stock_basic_info(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        if not info or (info.get('longName') is None and info.get('shortName') is None and info.get('symbol') is None):
            quick_hist = stock.history(period="1d")
            if quick_hist.empty:
                return None, f"Keine Informationen für Ticker '{ticker_symbol}' gefunden. Ist der Ticker korrekt?"
            company_name = info.get('symbol', ticker_symbol)
        else:
            company_name = info.get('longName', info.get('shortName', ticker_symbol))
        return {'ticker': ticker_symbol, 'name': company_name, 'info_dict': info}, None
    except Exception as e:
        return None, f"Fehler beim Abrufen der Basisinformationen für '{ticker_symbol}': {str(e)}"


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
            stock_data['name'] = info.get('symbol', ticker_symbol)
        else:
            stock_data['name'] = info.get('longName', info.get('shortName', ticker_symbol))

        stock_data['info'] = info
        try:
            stock_data['financials_html'] = stock.financials.to_html(classes='table table-sm table-striped',
                                                                     border=0) if not stock.financials.empty else "Keine Finanzdaten verfügbar."
        except Exception:
            stock_data['financials_html'] = "Finanzdaten konnten nicht geladen werden."
        try:
            stock_data['major_holders_html'] = stock.major_holders.to_html(classes='table table-sm table-striped',
                                                                           border=0) if stock.major_holders is not None and not stock.major_holders.empty else "Keine Daten zu Haupteignern verfügbar."
        except Exception:
            stock_data['major_holders_html'] = "Daten zu Haupteignern konnten nicht geladen werden."
        try:
            stock_data['recommendations_html'] = stock.recommendations.tail(5).to_html(
                classes='table table-sm table-striped',
                border=0) if stock.recommendations is not None and not stock.recommendations.empty else "Keine Empfehlungen verfügbar."
        except Exception:
            stock_data['recommendations_html'] = "Empfehlungen konnten nicht geladen werden."
        try:
            quote_info = {
                "Preis": info.get("currentPrice", info.get("regularMarketPrice", "N/A")),
                "Gehandeltes Volumen": info.get("volume", "N/A"),
                "Tageshoch": info.get("dayHigh", "N/A"), "Tagestief": info.get("dayLow", "N/A"),
                "Eröffnung": info.get("open", "N/A"), "Vortagesschluss": info.get("previousClose", "N/A"),
                "Marktkapitalisierung": info.get("marketCap", "N/A"),
                "Dividendenrendite": info.get("dividendYield", "N/A")
            }
            if isinstance(quote_info.get("Marktkapitalisierung"), (int, float)):
                quote_info["Marktkapitalisierung"] = f"{quote_info['Marktkapitalisierung']:,}"
            if isinstance(quote_info.get("Dividendenrendite"), (int, float)):
                quote_info["Dividendenrendite"] = f"{quote_info['Dividendenrendite'] * 100:.2f}%"
            stock_data['quote_info'] = quote_info
        except Exception as e:
            stock_data['quote_info_error'] = f"Kursinformationen konnten nicht extrahiert werden: {e}"
    except Exception as e:
        stock_data['error'] = f"Allgemeiner Fehler beim Abrufen der Detaildaten für '{ticker_symbol}': {str(e)}"
    return stock_data


def determine_actual_interval_and_period(selected_period, selected_quality):
    actual_period = selected_period
    adjustment_note = None
    if selected_period == "5d":
        if selected_quality == "high":
            actual_interval = "1m"
        elif selected_quality == "normal":
            actual_interval = "5m"
        else:
            actual_interval = "15m"
    elif selected_period == "1mo":
        if selected_quality == "high":
            actual_interval = "5m"
        elif selected_quality == "normal":
            actual_interval = "30m"
        else:
            actual_interval = "1h"
    elif selected_period == "3mo":
        if selected_quality == "high":
            actual_interval = "30m"
        elif selected_quality == "normal":
            actual_interval = "1h"
        else:
            actual_interval = "1d"
    elif selected_period in ["6mo", "ytd"]:
        if selected_quality == "high":
            actual_interval = "1h"
        elif selected_quality == "normal":
            actual_interval = "1d"
        else:
            actual_interval = "1wk"
    elif selected_period in ["1y", "2y"]:
        if selected_quality == "high":
            actual_interval = "1d"
        elif selected_quality == "normal":
            actual_interval = "1wk"
        else:
            actual_interval = "1mo"
    elif selected_period in ["5y", "max"]:
        if selected_quality == "high":
            actual_interval = "1wk"
        elif selected_quality == "normal":
            actual_interval = "1mo"
        else:
            actual_interval = "3mo"
    else:
        actual_interval = "1d"

    original_period_for_note = actual_period
    if actual_interval == "1m" and actual_period not in ["1d", "2d", "3d", "4d", "5d"]:
        actual_period = "5d"
    elif actual_interval in ["2m", "5m", "15m", "30m"] and actual_period not in ["1d", "5d", "1mo", "2mo"]:
        if selected_period == "3mo":
            actual_period = "2mo"
        elif selected_period not in ["1d", "5d", "1mo"]:
            actual_period = "2mo"
    elif actual_interval in ["60m", "90m", "1h", "4h"] and actual_period not in ["1d", "5d", "1mo", "3mo", "6mo", "1y",
                                                                                 "2y", "ytd"]:
        if selected_period in ["5y", "max"]: actual_period = "2y"

    if original_period_for_note != actual_period:
        period_display_original = next((p[1] for p in AVAILABLE_PERIODS if p[0] == original_period_for_note),
                                       original_period_for_note)
        period_display_actual = next((p[1] for p in AVAILABLE_PERIODS if p[0] == actual_period), actual_period)
        adjustment_note = f"Hinweis: Zeitraum für Qualität '{selected_quality}' und ursprüngliche Auswahl '{period_display_original}' auf '{period_display_actual}' angepasst, um Intervall '{actual_interval}' zu unterstützen."
    return actual_period, actual_interval, adjustment_note


def generate_stock_plotly_chart(ticker_symbol, period="1y", interval="1d", quality_note=None,
                                remove_gaps=True):  # Neuer Parameter
    chart_html = None
    error_msg = quality_note if quality_note else None
    company_name = ticker_symbol

    print(f"Chart-Generierung: Ticker={ticker_symbol}, Period={period}, Interval={interval}, RemoveGaps={remove_gaps}")
    try:
        stock = yf.Ticker(ticker_symbol)
        info_temp = stock.info
        if info_temp and (info_temp.get('longName') or info_temp.get('shortName')):
            company_name = info_temp.get('longName', info_temp.get('shortName', ticker_symbol))

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
            interval_map_for_display = {"1m": "1 Min", "2m": "2 Min", "5m": "5 Min", "15m": "15 Min", "30m": "30 Min",
                                        "60m": "1 Std", "1h": "1 Std", "90m": "90 Min", "4h": "4 Std", "1d": "Täglich",
                                        "1wk": "Wöchentlich", "1mo": "Monatlich", "3mo": "Quartalsweise"}
            interval_display = interval_map_for_display.get(interval, interval)

            fig.update_layout(
                title=f'Kurs: {company_name} ({ticker_symbol})<br><span style="font-size:0.8em;">Zeitraum: {period_display}, Auflösung: {interval_display}</span>',
                xaxis_title='Datum / Uhrzeit', yaxis_title='Preis',
                xaxis_rangeslider_visible=False,
                margin=dict(l=40, r=20, t=80, b=40)
            )

            if remove_gaps:
                print(f"DEBUG: remove_gaps ist True. Versuche Wochenenden zu entfernen.")
                print(f"DEBUG: X-Achsen-Typ vor rangebreak: {fig.layout.xaxis.type}")
                if not hist_data.empty:
                    print(
                        f"DEBUG: Erster Zeitstempel: {hist_data.index[0]}, Letzter Zeitstempel: {hist_data.index[-1]}")
                    print(f"DEBUG: Zeitzone des Index: {hist_data.index.tz}")

                fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
                # Test: Was passiert, wenn wir den Typ explizit setzen?
                # fig.update_layout(xaxis_type='date') # Normalerweise nicht nötig, Plotly sollte es erkennen
            else:
                print(f"DEBUG: remove_gaps ist False. Wochenenden werden nicht entfernt.")

            chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    except Exception as e:
        current_err = f"Fehler beim Generieren des Charts (Periode: {period}, Intervall: {interval}): {str(e)}"
        print(f"Fehler in generate_stock_plotly_chart für {ticker_symbol}: {current_err}")
        if "No data found for this date range" in str(e) or "yfinance failed to decrypt Yahoo data" in str(e):
            current_err = f"Keine Daten für '{ticker_symbol}' im Zeitraum '{period}' mit Intervall '{interval}'. Die Kombination ist evtl. ungültig oder der Ticker nicht verfügbar."
        error_msg = (error_msg + " | " if error_msg else "") + current_err

    return chart_html, error_msg, company_name


# -- FLASK ROUTEN (landing_page, search_stock_page bleiben unverändert) --
@app.route('/', methods=['GET'])
def landing_page():
    return redirect(url_for('search_stock_page'))


@app.route('/search', methods=['GET', 'POST'])
def search_stock_page():
    error = None
    if request.method == 'POST':
        ticker_query = request.form.get('ticker_query', '').strip().upper()
        if not ticker_query:
            error = "Bitte gib einen Aktien-Ticker ein."
        else:
            basic_info, info_error = get_stock_basic_info(ticker_query)
            if info_error or not basic_info:
                error = info_error if info_error else f"Ticker '{ticker_query}' nicht gefunden oder ungültig."
            else:
                # Standardmäßig mit 1 Jahr, normaler Qualität und Lücken entfernt starten
                return redirect(url_for('stock_detail_page',
                                        ticker_symbol=ticker_query,
                                        period='1y',
                                        quality='normal',
                                        remove_gaps='on'))  # Standard 'on'
    return render_template('search_page.html', error=error, query=request.form.get('ticker_query', ''))


@app.route('/stock/<string:ticker_symbol>')
def stock_detail_page(ticker_symbol):
    ticker_symbol = ticker_symbol.upper()
    stock_details = get_stock_detailed_data(ticker_symbol)

    selected_period = request.args.get('period', '1y')
    selected_quality = request.args.get('quality', 'normal')
    # Neuer Parameter für Lücken, Standard 'on' (Checkbox ist gecheckt)
    # HTML-Checkboxen senden den Wert nur, wenn sie gecheckt sind.
    # Wenn nicht gecheckt, ist der Parameter nicht im request.args.
    # Wir interpretieren 'on' als True, alles andere (oder Fehlen) als Standard True.
    # Oder besser: Wenn der Parameter fehlt, ist es der erste Aufruf oder der User hat ihn nicht explizit geändert
    # Wir können den Default im Template setzen und hier den Wert aus request.args.get('remove_gaps', 'on') nehmen
    remove_gaps_str = request.args.get('remove_gaps', 'on')  # Standardmäßig 'on'
    remove_gaps_bool = remove_gaps_str == 'on'

    if not any(p[0] == selected_period for p in AVAILABLE_PERIODS): selected_period = '1y'
    if not any(q[0] == selected_quality for q in AVAILABLE_QUALITIES): selected_quality = 'normal'

    actual_period, actual_interval, adjustment_note = determine_actual_interval_and_period(selected_period,
                                                                                           selected_quality)

    chart_html, chart_error_msg, _ = generate_stock_plotly_chart(ticker_symbol,
                                                                 period=actual_period,
                                                                 interval=actual_interval,
                                                                 quality_note=adjustment_note,
                                                                 remove_gaps=remove_gaps_bool)

    overall_error = chart_error_msg if chart_error_msg else stock_details.get('error')

    return render_template('stock_detail_page.html',
                           ticker=ticker_symbol,
                           details=stock_details,
                           chart_html=chart_html,
                           error=overall_error,
                           current_period=selected_period,
                           current_quality=selected_quality,
                           current_remove_gaps=remove_gaps_bool,  # Den Boolean-Wert an das Template geben
                           available_periods=AVAILABLE_PERIODS,
                           available_qualities=AVAILABLE_QUALITIES)


@app.route('/test_graph')
def test_graph_page():
    fixed_ticker = "AAPL"
    selected_period = request.args.get("period", "6mo")
    selected_quality = request.args.get("quality", "high")
    remove_gaps_str = request.args.get('remove_gaps', 'on')
    remove_gaps_bool = remove_gaps_str == 'on'

    if not any(p[0] == selected_period for p in AVAILABLE_PERIODS): selected_period = '6mo'
    if not any(q[0] == selected_quality for q in AVAILABLE_QUALITIES): selected_quality = 'high'

    actual_period, actual_interval, adjustment_note = determine_actual_interval_and_period(selected_period,
                                                                                           selected_quality)

    chart_html, error_msg, company_name = generate_stock_plotly_chart(fixed_ticker,
                                                                      period=actual_period,
                                                                      interval=actual_interval,
                                                                      quality_note=adjustment_note,
                                                                      remove_gaps=remove_gaps_bool)

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
    app.run(host='0.0.0.0', port=5000, debug=True)