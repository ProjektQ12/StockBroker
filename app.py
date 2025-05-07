import os
import requests
from flask import Flask, render_template, request, url_for, redirect, json # json hinzufügen
from datetime import datetime, timedelta # Für Zeitberechnungen bei der Filterung (optional serverseitig)

#Für neues Graphing
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

app = Flask(__name__)

# ... (API Key, URL, search_alpha_vantage, get_quote_alpha_vantage bleiben gleich) ...
API_KEY = '7OSPTVFEGLEN69W7' # Wieder der Hinweis: Besser Umgebungsvariable
ALPHA_VANTAGE_URL = 'https://www.alphavantage.co/query'

def search_alpha_vantage(keywords):
    # ... (unverändert) ...
    params = {
        'function': 'SYMBOL_SEARCH',
        'keywords': keywords,
        'apikey': API_KEY
    }


    try:
        response = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'Error Message' in data:
            return None, f"API Fehler: {data['Error Message']}"
        if 'Note' in data:
            print(f"API Hinweis: {data['Note']}")

        results = []
        if 'bestMatches' in data:
            for match in data['bestMatches']:
                results.append({
                    'symbol': match.get('1. symbol'),
                    'name': match.get('2. name'),
                    'region': match.get('4. region'),
                    'currency': match.get('8. currency')
                })
            return results, None
        else:
            return [], None

    except requests.exceptions.RequestException as e:
        return None, f"Netzwerkfehler: {e}"
    except Exception as e:
        return None, f"Unerwarteter Fehler bei der Suche: {e}"

def get_quote_alpha_vantage(symbol):
    # ... (unverändert) ...
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': symbol,
        'apikey': API_KEY
    }
    try:
        response = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'Error Message' in data:
            return None, f"API Fehler: {data['Error Message']}"
        if 'Note' in data:
            print(f"API Hinweis (Quote): {data['Note']}")

        if 'Global Quote' in data and data['Global Quote']:
            quote_data = data['Global Quote']
            quote = {
                'symbol': quote_data.get('01. symbol'),
                'open': quote_data.get('02. open'),
                'high': quote_data.get('03. high'),
                'low': quote_data.get('04. low'),
                'price': quote_data.get('05. price'),
                'volume': quote_data.get('06. volume'),
                'latest_trading_day': quote_data.get('07. latest trading day'),
                'previous_close': quote_data.get('08. previous close'),
            }
            if '.' in symbol and symbol.split('.')[-1].upper() == 'DE':
                 quote['currency'] = 'EUR'
            else:
                 quote['currency'] = ''

            return quote, None
        elif 'Global Quote' in data and not data['Global Quote']:
             return None, f"Keine Kursdaten für das Symbol '{symbol}' gefunden (leere 'Global Quote')."
        else:
             return None, "Unerwartetes Format der API-Antwort für Quote."

    except requests.exceptions.RequestException as e:
        return None, f"Netzwerkfehler beim Abrufen des Quotes: {e}"
    except Exception as e:
        return None, f"Unerwarteter Fehler beim Abrufen des Quotes: {e}"


def get_time_series_daily(symbol):
    """ Ruft TIME_SERIES_DAILY (full) von Alpha Vantage ab und bereitet Daten für Chart.js vor. """
    params = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': symbol,
        'outputsize': 'full', # 'compact' für nur 100 Punkte, 'full' für mehr
        'apikey': API_KEY
    }
    try:
        response = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=20) # Längerer Timeout für 'full'
        response.raise_for_status()
        data = response.json()

        if 'Error Message' in data:
            return None, None, f"API Fehler (Zeitreihe): {data['Error Message']}"
        if 'Note' in data:
             # Wichtig bei 'full', da das Limit schnell erreicht werden kann
            print(f"API Hinweis (Zeitreihe): {data['Note']}")
            # Wenn ein Hinweis kommt, können trotzdem Daten vorhanden sein! Weiter versuchen.

        if 'Time Series (Daily)' in data:
            time_series = data['Time Series (Daily)']
            # Daten sind als Dict {datum_str: {werte}}, wir brauchen Listen
            # Sortieren nach Datum (Schlüssel des Dicts) aufsteigend
            sorted_dates = sorted(time_series.keys())

            dates = []
            prices = []
            for date_str in sorted_dates:
                # Nur gültige Datumsformate verarbeiten
                try:
                    datetime.strptime(date_str, '%Y-%m-%d') # Validierung
                    dates.append(date_str)
                    # Nimm den Schlusskurs ('4. close')
                    prices.append(float(time_series[date_str].get('4. close', 0))) # Als float speichern
                except (ValueError, TypeError):
                    print(f"Überspringe ungültigen Datumseintrag: {date_str}")
                    continue

            if not dates: # Fallback, falls trotz 'Time Series (Daily)' keine gültigen Daten drin waren
                 return None, None, "Keine gültigen Zeitreihendaten gefunden nach der Verarbeitung."

            return dates, prices, None # Listen (Labels, Datenpunkte), kein Fehler
        else:
            # Fehler, wenn trotz erfolgreicher Antwort der erwartete Key fehlt
             error_msg = "Antwort enthält keinen 'Time Series (Daily)'-Schlüssel."
             if 'Information' in data: # Manchmal gibt es Infos statt Fehlern
                 error_msg += f" Info: {data['Information']}"
             return None, None, error_msg


    except requests.exceptions.RequestException as e:
        return None, None, f"Netzwerkfehler bei Zeitreihenabruf: {e}"
    except Exception as e:
        return None, None, f"Unerwarteter Fehler bei Zeitreihenabruf: {e}"

@app.route('/', methods=['GET'])
def search_page():
    # ... (unverändert) ...
    query = request.args.get('query', None)
    results = None
    error = None
    if query:
        results, error = search_alpha_vantage(query)
    return render_template('search.html', query=query, results=results, error=error)

@app.route('/graph', methods=['GET', 'POST'])
def index():
    chart_html = None
    error = None
    current_ticker = None
    company_name = None

    if request.method == 'POST':
        ticker_symbol = request.form.get('ticker', '').strip().upper()
        current_ticker = ticker_symbol

        if not ticker_symbol:
            error = "Bitte gib einen Aktien-Ticker ein."
        else:
            try:
                stock = yf.Ticker(ticker_symbol)
                # Versuche, grundlegende Informationen abzurufen, um die Gültigkeit zu prüfen
                info = stock.info
                if not info or 'shortName' not in info: # Manchmal ist info leer für ungültige Ticker
                    error = f"Keine Informationen für Ticker '{ticker_symbol}' gefunden. Ist der Ticker korrekt?"
                else:
                    company_name = info.get('longName', info.get('shortName', ticker_symbol))

                    # Hole historische Daten (z.B. für das letzte Jahr)
                    # Weitere Optionen für period: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
                    hist_data = stock.history(period="1y")

                    if hist_data.empty:
                        error = f"Keine historischen Daten für '{ticker_symbol}' gefunden."
                    else:
                        # Erstelle den Plotly Chart
                        fig = go.Figure()

                        # Candlestick Chart
                        fig.add_trace(go.Candlestick(x=hist_data.index,
                                        open=hist_data['Open'],
                                        high=hist_data['High'],
                                        low=hist_data['Low'],
                                        close=hist_data['Close'],
                                        name='Candlestick'))

                        # Optional: Gleitender Durchschnitt hinzufügen
                        # hist_data['MA20'] = hist_data['Close'].rolling(window=20).mean()
                        # fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA20'], mode='lines', name='MA20', line=dict(color='orange')))


                        fig.update_layout(
                            title=f'Aktienkurs: {company_name} ({ticker_symbol})',
                            xaxis_title='Datum',
                            yaxis_title='Preis (USD)', # Annahme: USD, kann je nach Aktie variieren
                            xaxis_rangeslider_visible=False # Schaltet den Range Slider unter dem Chart an/aus
                        )

                        # Konvertiere den Plotly Chart in HTML
                        # include_plotlyjs='cdn' lädt Plotly.js von einem CDN, sodass es nicht lokal eingebunden werden muss.
                        chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

            except Exception as e:
                # yfinance kann verschiedene Fehler werfen, z.B. wenn der Ticker nicht existiert
                error = f"Fehler beim Abrufen der Daten für '{ticker_symbol}': {str(e)}"
                print(f"Ein Fehler ist aufgetreten: {e}") # Für Debugging in der Konsole

    return render_template('graph.html',
                           chart_html=chart_html,
                           error=error,
                           current_ticker=current_ticker,
                           company_name=company_name)

@app.route('/stock', methods=['GET'])
def stock_detail_page():
    """ Zeigt die Detailseite mit Quote und Chart. """
    symbol = request.args.get('symbol', None)
    quote = None
    quote_error = None
    chart_dates = None
    chart_prices = None
    chart_error = None

    if not symbol:
        return redirect(url_for('search_page'))

    # Quote abrufen
    quote, quote_error = get_quote_alpha_vantage(symbol)

    # Zeitreihe für Chart abrufen
    chart_dates, chart_prices, chart_error = get_time_series_daily(symbol)

    # Währung aus Quote holen (falls vorhanden) für Chart-Label
    currency = quote.get('currency', '') if quote else ''

    # Daten für das Template vorbereiten
    # WICHTIG: Übergebe Daten als JSON-String, damit JavaScript sie direkt nutzen kann
    # Flask's `tojson` Filter ist sicher dafür
    template_data = {
        "symbol": symbol,
        "quote": quote,
        "quote_error": quote_error,
        "chart_dates_json": json.dumps(chart_dates) if chart_dates else 'null',
        "chart_prices_json": json.dumps(chart_prices) if chart_prices else 'null',
        "chart_error": chart_error,
        "currency": currency
    }

    return render_template('stock_detail.html', **template_data) # Entpackt das Dict als Keyword-Argumente


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)