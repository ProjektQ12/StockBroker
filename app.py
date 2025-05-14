from flask import Flask, render_template, request, redirect, url_for
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime  # Für YTD-Berechnung (optional, yfinance kann "ytd" oft direkt)

app = Flask(__name__)

# -- Konstanten für Dropdown-Optionen --
AVAILABLE_PERIODS = [
    # (Wert für yfinance, Anzeigename)
    ("5d", "5 Tage"),
    ("1mo", "1 Monat"),
    ("3mo", "3 Monate"),
    ("6mo", "6 Monate"),
    ("1y", "1 Jahr"),
    ("2y", "2 Jahre"),
    ("5y", "5 Jahre"),
    ("ytd", "Seit Jahresbeginn (YTD)"),
    ("max", "Maximal")
]

AVAILABLE_INTERVALS = [
    # (Wert für yfinance, Anzeigename)
    ("1m", "1 Minute"),
    ("2m", "2 Minuten"),
    ("5m", "5 Minuten"),
    ("15m", "15 Minuten"),
    ("30m", "30 Minuten"),
    ("60m", "1 Stunde"),  # yfinance versteht auch '1h'
    ("90m", "90 Minuten"),
    ("4h", "4 Stunden"),  # Wird von yfinance unterstützt
    ("1d", "Täglich"),
    ("1wk", "Wöchentlich"),
    ("1mo", "Monatlich"),
]


# -- HELPER FUNKTIONEN (get_stock_basic_info, get_stock_detailed_data bleiben wie im vorherigen Schritt) --
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


def generate_stock_plotly_chart(ticker_symbol, period="1y", interval="1d"):
    chart_html = None
    error_msg = None
    company_name = ticker_symbol
    adjusted_info = None  # Für Hinweise auf Anpassungen

    # Logik zur Anpassung von 'period' basierend auf 'interval'
    # yfinance hat Limits: 1m (max 7d, real eher 5d), 2m-30m (max 60d), 60m/1h/90m/4h (max 730d)
    original_period = period
    if interval == "1m":
        if period not in ["1d", "2d", "3d", "4d", "5d"]: period = "5d"
    elif interval in ["2m", "5m", "15m", "30m"]:
        if period not in ["1d", "5d", "1mo", "2mo", "ytd"]: period = "2mo"  # 2mo ~ 60d
    elif interval in ["60m", "90m", "1h", "4h"]:  # 1h ist Alias für 60m
        if period not in ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "ytd"]: period = "2y"

    if original_period != period:
        adjusted_info = f"Hinweis: Zeitraum für Intervall '{interval}' auf '{period}' angepasst (ursprünglich '{original_period}')."
        print(adjusted_info)  # Für Server-Log

    print(f"Chart-Generierung: Ticker={ticker_symbol}, Period={period}, Interval={interval}")

    try:
        stock = yf.Ticker(ticker_symbol)
        info_temp = stock.info
        if info_temp and (info_temp.get('longName') or info_temp.get('shortName')):
            company_name = info_temp.get('longName', info_temp.get('shortName', ticker_symbol))

        hist_data = stock.history(period=period, interval=interval, auto_adjust=True,
                                  prepost=False)  # auto_adjust für Split-bereinigte Kurse

        if hist_data.empty:
            error_msg = f"Keine Kursdaten für '{ticker_symbol}' mit Periode '{period}' und Intervall '{interval}' gefunden."
        else:
            fig = go.Figure()

            # Candlestick oder Linienchart basierend auf Intervall?
            # Für sehr feine Intervalle (z.B. 1m auf 5d) kann ein Linienchart übersichtlicher sein
            # Hier bleiben wir bei Candlestick für Konsistenz
            fig.add_trace(go.Candlestick(x=hist_data.index,
                                         open=hist_data['Open'],
                                         high=hist_data['High'],
                                         low=hist_data['Low'],
                                         close=hist_data['Close'],
                                         name=f'{ticker_symbol}'))

            # Anzeigename für Intervall im Titel
            interval_display_name = next((name for val, name in AVAILABLE_INTERVALS if val == interval), interval)
            period_display_name = next((name for val, name in AVAILABLE_PERIODS if val == period), period)
            if original_period != period:  # Wenn angepasst, zeige das im Titel
                period_display_name = f"{next((name for val, name in AVAILABLE_PERIODS if val == period), period)} (angepasst von {next((name for val, name in AVAILABLE_PERIODS if val == original_period), original_period)})"

            fig.update_layout(
                title=f'Kurs: {company_name} ({ticker_symbol})<br><span style="font-size:0.8em;">Zeitraum: {period_display_name}, Intervall: {interval_display_name}</span>',
                xaxis_title='Datum / Uhrzeit',
                yaxis_title='Preis',
                xaxis_rangeslider_visible=False,  # Kann bei Bedarf wieder aktiviert werden
                margin=dict(l=40, r=20, t=80, b=40)  # Mehr Platz für Titel
            )

            # Lücken bei Wochenenden entfernen (für tägliche und längere Intervalle)
            if interval in ["1d", "1wk", "1mo"]:
                fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
            # Für Intraday (m, h) bleiben nächtliche Lücken erstmal sichtbar, um Komplexität zu vermeiden
            # da Börsenzeiten variieren. Wochenenden werden hier auch durch die Datenstruktur von yf oft schon gefiltert.

            chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
            if adjusted_info and error_msg:
                error_msg += " " + adjusted_info
            elif adjusted_info:
                error_msg = adjusted_info


    except Exception as e:
        current_error = f"Fehler beim Generieren des Charts für '{ticker_symbol}' (Periode: {period}, Intervall: {interval}): {str(e)}"
        print(f"Fehler in generate_stock_plotly_chart: {e}")
        if "No data found for this date range" in str(e) or "No data found, symbol may be delisted" in str(
                e) or "yfinance failed to decrypt Yahoo data" in str(e):
            current_error = f"Keine Daten für '{ticker_symbol}' im Zeitraum '{period}' mit Intervall '{interval}' gefunden. Die Kombination könnte ungültig sein oder der Ticker ist delisted."
        elif "404 Client Error" in str(e) or "No data found" in str(e).lower():
            current_error = f"Keine Chartdaten für '{ticker_symbol}' gefunden. Ticker könnte falsch oder dekotiert sein."
        elif "429 Client Error" in str(e):
            current_error = f"Zu viele Anfragen an den Datenprovider. Bitte später erneut versuchen."

        error_msg = (error_msg + " | " if error_msg else "") + current_error  # Kombiniere mit evtl. adjusted_info

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
                # Standardmäßig mit 1 Jahr und täglichem Intervall starten
                return redirect(url_for('stock_detail_page', ticker_symbol=ticker_query, period='1y', interval='1d'))
    return render_template('search_page.html', error=error, query=request.form.get('ticker_query', ''))


@app.route('/stock/<string:ticker_symbol>')
def stock_detail_page(ticker_symbol):
    ticker_symbol = ticker_symbol.upper()
    stock_details = get_stock_detailed_data(ticker_symbol)

    chart_period = request.args.get('period', '1y')
    chart_interval = request.args.get('interval', '1d')

    # Sicherstellen, dass die übergebenen Werte in unseren Listen sind, sonst Default
    if not any(p[0] == chart_period for p in AVAILABLE_PERIODS): chart_period = '1y'
    if not any(i[0] == chart_interval for i in AVAILABLE_INTERVALS): chart_interval = '1d'

    chart_html, chart_error_msg, _ = generate_stock_plotly_chart(ticker_symbol,
                                                                 period=chart_period,
                                                                 interval=chart_interval)

    # Gesamte Fehlermeldung (kann von Details oder Chart kommen)
    # Chart-Fehler (inkl. Anpassungshinweis) hat Vorrang, wenn vorhanden
    overall_error = chart_error_msg if chart_error_msg else stock_details.get('error')

    return render_template('stock_detail_page.html',
                           ticker=ticker_symbol,
                           details=stock_details,
                           chart_html=chart_html,
                           error=overall_error,
                           current_period=chart_period,
                           current_interval=chart_interval,
                           available_periods=AVAILABLE_PERIODS,
                           available_intervals=AVAILABLE_INTERVALS)


@app.route('/test_graph')  # test_graph_page bleibt für schnelles Testen
def test_graph_page():
    fixed_ticker = "AAPL"
    period = request.args.get("period", "1d")
    interval = request.args.get("interval", "1m")  # Standard auf feines Intraday

    chart_html, error_msg, company_name = generate_stock_plotly_chart(fixed_ticker, period=period, interval=interval)

    return render_template('test_graph_page.html',
                           ticker=fixed_ticker,
                           company_name=company_name,
                           chart_html=chart_html,
                           error=error_msg,
                           period=period,
                           interval=interval,
                           available_periods=AVAILABLE_PERIODS,  # Auch hier übergeben für Konsistenz
                           available_intervals=AVAILABLE_INTERVALS)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)