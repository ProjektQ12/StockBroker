from flask import Flask, render_template, request, redirect, url_for
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# datetime wird hier nicht mehr explizit für YTD benötigt, yfinance kann "ytd"

app = Flask(__name__)

# -- Konstanten für Dropdown-Optionen --
AVAILABLE_PERIODS = [
    ("5d", "5 Tage"), ("1mo", "1 Monat"), ("3mo", "3 Monate"),
    ("6mo", "6 Monate"), ("1y", "1 Jahr"), ("2y", "2 Jahre"),
    ("5y", "5 Jahre"), ("ytd", "Seit Jahresbeginn"), ("max", "Maximal")
]

AVAILABLE_QUALITIES = [
    # (Wert, Anzeigename)
    ("high", "Hoch"), ("normal", "Normal"), ("low", "Niedrig")
]


# -- HELPER FUNKTIONEN (get_stock_basic_info, get_stock_detailed_data bleiben unverändert) --
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
    """
    Bestimmt den tatsächlichen Intervall und Zeitraum basierend auf Auswahl und yfinance-Limits.
    Gibt (actual_period, actual_interval, adjustment_note) zurück.
    """
    actual_period = selected_period
    adjustment_note = None

    # Mapping Logik: (Diese Logik ist ein Beispiel und kann verfeinert werden)
    if selected_period == "5d":
        if selected_quality == "high":
            actual_interval = "1m"  # Feinste für kurze Zeit
        elif selected_quality == "normal":
            actual_interval = "5m"
        else:
            actual_interval = "15m"  # Low
    elif selected_period == "1mo":
        if selected_quality == "high":
            actual_interval = "5m"  # yf max 60d für 5m
        elif selected_quality == "normal":
            actual_interval = "30m"
        else:
            actual_interval = "1h"
    elif selected_period == "3mo":
        if selected_quality == "high":
            actual_interval = "30m"  # yf max 60d, also wird Periode angepasst
        elif selected_quality == "normal":
            actual_interval = "1h"
        else:
            actual_interval = "1d"
    elif selected_period in ["6mo", "ytd"]:  # YTD kann kurz oder lang sein
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
            actual_interval = "1wk"  # Für sehr lange Zeiträume ist 1d oft zu viel
        elif selected_quality == "normal":
            actual_interval = "1mo"
        else:
            actual_interval = "3mo"  # yf unterstützt "3mo" Intervall
    else:  # Fallback
        actual_interval = "1d"

    # --- Anpassung der Periode basierend auf yfinance Intervall-Limits ---
    # Wichtig, um Fehler von yfinance zu vermeiden
    original_period_for_note = actual_period
    if actual_interval == "1m" and actual_period not in ["1d", "2d", "3d", "4d", "5d"]:
        actual_period = "5d"
    elif actual_interval in ["2m", "5m", "15m", "30m"] and actual_period not in ["1d", "5d", "1mo", "2mo"]:
        # 2mo ist ca. 60d, was das Limit für diese Intervalle ist
        if selected_period == "3mo":
            actual_period = "2mo"  # Explizit für 3mo, wenn Intervall zu fein
        elif selected_period not in ["1d", "5d", "1mo"]:
            actual_period = "2mo"  # Allgemeiner Fallback
    elif actual_interval in ["60m", "90m", "1h", "4h"] and actual_period not in ["1d", "5d", "1mo", "3mo", "6mo", "1y",
                                                                                 "2y", "ytd"]:
        if selected_period in ["5y", "max"]: actual_period = "2y"  # Max 2 Jahre für stündliche Daten

    if original_period_for_note != actual_period:
        period_display_original = next((p[1] for p in AVAILABLE_PERIODS if p[0] == original_period_for_note),
                                       original_period_for_note)
        period_display_actual = next((p[1] for p in AVAILABLE_PERIODS if p[0] == actual_period), actual_period)
        adjustment_note = f"Hinweis: Zeitraum für Qualität '{selected_quality}' und ursprüngliche Auswahl '{period_display_original}' auf '{period_display_actual}' angepasst, um Intervall '{actual_interval}' zu unterstützen."

    return actual_period, actual_interval, adjustment_note


def generate_stock_plotly_chart(ticker_symbol, period="1y", interval="1d", quality_note=None):
    chart_html = None
    error_msg = quality_note if quality_note else None  # Start mit evtl. Anpassungshinweis
    company_name = ticker_symbol

    print(f"Chart-Generierung: Ticker={ticker_symbol}, Period={period}, Interval={interval}")
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
            # Finde Anzeigename für Intervall (etwas umständlich, da AVAILABLE_INTERVALS anders strukturiert ist als yf Werte)
            interval_map_for_display = {"1m": "1 Min", "5m": "5 Min", "15m": "15 Min", "30m": "30 Min", "60m": "1 Std",
                                        "1h": "1 Std", "90m": "90 Min", "4h": "4 Std", "1d": "Täglich",
                                        "1wk": "Wöchentlich", "1mo": "Monatlich", "3mo": "Quartalsweise"}
            interval_display = interval_map_for_display.get(interval, interval)

            fig.update_layout(
                title=f'Kurs: {company_name} ({ticker_symbol})<br><span style="font-size:0.8em;">Zeitraum: {period_display}, Auflösung: {interval_display}</span>',
                xaxis_title='Datum / Uhrzeit', yaxis_title='Preis',
                xaxis_rangeslider_visible=False,
                margin=dict(l=40, r=20, t=80, b=40)
            )
            if interval in ["1d", "1wk", "1mo", "3mo"]:
                fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
            chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    except Exception as e:
        current_err = f"Fehler beim Generieren des Charts (Periode: {period}, Intervall: {interval}): {str(e)}"
        print(f"Fehler in generate_stock_plotly_chart für {ticker_symbol}: {current_err}")
        # Spezifischere Fehlermeldungen von yfinance
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
                # Standardmäßig mit 1 Jahr und normaler Qualität starten
                return redirect(url_for('stock_detail_page', ticker_symbol=ticker_query, period='1y', quality='normal'))
    return render_template('search_page.html', error=error, query=request.form.get('ticker_query', ''))


@app.route('/stock/<string:ticker_symbol>')
def stock_detail_page(ticker_symbol):
    ticker_symbol = ticker_symbol.upper()
    stock_details = get_stock_detailed_data(ticker_symbol)

    selected_period = request.args.get('period', '1y')
    selected_quality = request.args.get('quality', 'normal')  # Standard 'normal'

    # Sicherstellen, dass die übergebenen Werte in unseren Listen sind, sonst Default
    if not any(p[0] == selected_period for p in AVAILABLE_PERIODS): selected_period = '1y'
    if not any(q[0] == selected_quality for q in AVAILABLE_QUALITIES): selected_quality = 'normal'

    # Eigentliche Periode und Intervall bestimmen
    actual_period, actual_interval, adjustment_note = determine_actual_interval_and_period(selected_period,
                                                                                           selected_quality)

    chart_html, chart_error_msg, _ = generate_stock_plotly_chart(ticker_symbol,
                                                                 period=actual_period,
                                                                 interval=actual_interval,
                                                                 quality_note=adjustment_note)  # Hinweis übergeben

    overall_error = chart_error_msg if chart_error_msg else stock_details.get('error')

    return render_template('stock_detail_page.html',
                           ticker=ticker_symbol,
                           details=stock_details,
                           chart_html=chart_html,
                           error=overall_error,
                           current_period=selected_period,  # Behalte die ursprüngliche Auswahl für die Dropdowns
                           current_quality=selected_quality,
                           # Für die Anzeige im Chart-Titel etc. könnten wir auch actual_period/interval übergeben
                           # Falls der User sehen soll, was WIRKLICH verwendet wurde.
                           # Hier übergeben wir die ursprüngliche Auswahl für die Dropdown-Vorauswahl.
                           available_periods=AVAILABLE_PERIODS,
                           available_qualities=AVAILABLE_QUALITIES)


@app.route('/test_graph')
def test_graph_page():+
    fixed_ticker = "AAPL"
    selected_period = request.args.get("period", "6mo")
    selected_quality = request.args.get("quality", "high")

    if not any(p[0] == selected_period for p in AVAILABLE_PERIODS): selected_period = '6mo'
    if not any(q[0] == selected_quality for q in AVAILABLE_QUALITIES): selected_quality = 'high'

    actual_period, actual_interval, adjustment_note = determine_actual_interval_and_period(selected_period,
                                                                                           selected_quality)

    chart_html, error_msg, company_name = generate_stock_plotly_chart(fixed_ticker,
                                                                      period=actual_period,
                                                                      interval=actual_interval,
                                                                      quality_note=adjustment_note)

    return render_template('test_graph_page.html',
                           ticker=fixed_ticker,
                           company_name=company_name,
                           chart_html=chart_html,
                           error=error_msg,
                           current_period=selected_period,
                           current_quality=selected_quality,
                           # Infos für den Titel im Test-Template
                           actual_period_used=actual_period,
                           actual_interval_used=actual_interval,
                           available_periods=AVAILABLE_PERIODS,
                           available_qualities=AVAILABLE_QUALITIES)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)