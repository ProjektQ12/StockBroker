from flask import Flask, render_template, request, redirect, url_for
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

app = Flask(__name__)


# -- HELPER FUNKTIONEN für yfinance --

def get_stock_basic_info(ticker_symbol):
    """
    Ruft grundlegende Informationen zu einem Ticker ab (hauptsächlich für Validierung und Namen).
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        if not info or (info.get('longName') is None and info.get('shortName') is None and info.get('symbol') is None):
            # Wenn Info leer ist, versuche einen kleinen History-Abruf als letzten Test
            quick_hist = stock.history(period="1d")  # Nur 1 Tag für minimalen Aufwand
            if quick_hist.empty:
                return None, f"Keine Informationen für Ticker '{ticker_symbol}' gefunden. Ist der Ticker korrekt?"
            company_name = info.get('symbol', ticker_symbol)  # Fallback
        else:
            company_name = info.get('longName', info.get('shortName', ticker_symbol))

        return {'ticker': ticker_symbol, 'name': company_name, 'info_dict': info}, None
    except Exception as e:
        return None, f"Fehler beim Abrufen der Basisinformationen für '{ticker_symbol}': {str(e)}"


def get_stock_detailed_data(ticker_symbol):
    """
    Ruft detailliertere Daten (Info, Financials, etc.) für einen Ticker ab.
    """
    stock_data = {'ticker': ticker_symbol, 'error': None}
    try:
        stock = yf.Ticker(ticker_symbol)

        # 1. Info (ausführlich)
        info = stock.info
        if not info or (info.get('longName') is None and info.get('shortName') is None and info.get('symbol') is None):
            # Erneute Prüfung, falls der Ticker zwar ein Objekt erstellt, aber keine sinnvollen Infos liefert
            quick_hist = stock.history(period="1d")
            if quick_hist.empty:
                stock_data['error'] = f"Keine detaillierten Informationen für Ticker '{ticker_symbol}' gefunden."
                return stock_data  # Frühzeitiger Ausstieg
            stock_data['name'] = info.get('symbol', ticker_symbol)
        else:
            stock_data['name'] = info.get('longName', info.get('shortName', ticker_symbol))

        stock_data['info'] = info  # Das gesamte Info-Dictionary

        # 2. Weitere Datenpunkte (Beispiele)
        # Die `.to_html()` Methode von Pandas DataFrames ist nützlich für die Template-Darstellung
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
            # Quote-ähnliche Infos aus stock.info extrahieren, da yf.Ticker kein direktes .quote hat
            quote_info = {
                "Preis": info.get("currentPrice", info.get("regularMarketPrice", "N/A")),
                "Gehandeltes Volumen": info.get("volume", "N/A"),
                "Tageshoch": info.get("dayHigh", "N/A"),
                "Tagestief": info.get("dayLow", "N/A"),
                "Eröffnung": info.get("open", "N/A"),
                "Vortagesschluss": info.get("previousClose", "N/A"),
                "Marktkapitalisierung": info.get("marketCap", "N/A"),
                "Dividendenrendite": info.get("dividendYield", "N/A")
            }
            # Formatieren für schönere Anzeige
            if isinstance(quote_info.get("Marktkapitalisierung"), (int, float)):
                quote_info["Marktkapitalisierung"] = f"{quote_info['Marktkapitalisierung']:,}"
            if isinstance(quote_info.get("Dividendenrendite"), (int, float)):
                quote_info["Dividendenrendite"] = f"{quote_info['Dividendenrendite'] * 100:.2f}%"

            stock_data['quote_info'] = quote_info
        except Exception as e:
            stock_data['quote_info_error'] = f"Kursinformationen konnten nicht extrahiert werden: {e}"


    except Exception as e:
        stock_data['error'] = f"Allgemeiner Fehler beim Abrufen der Detaildaten für '{ticker_symbol}': {str(e)}"
        print(f"Fehler in get_stock_detailed_data für {ticker_symbol}: {e}")

    return stock_data


def generate_stock_plotly_chart(ticker_symbol, period="1y"):
    """
    Generiert das HTML für einen Plotly Candlestick-Chart für einen gegebenen Ticker und Zeitraum.
    """
    chart_html = None
    error_msg = None
    company_name = ticker_symbol  # Fallback

    try:
        stock = yf.Ticker(ticker_symbol)

        # Name für den Titel holen (optional, könnte auch von außen kommen)
        info_temp = stock.info
        if info_temp and (info_temp.get('longName') or info_temp.get('shortName')):
            company_name = info_temp.get('longName', info_temp.get('shortName', ticker_symbol))

        hist_data = stock.history(period=period)

        if hist_data.empty:
            error_msg = f"Keine historischen Kursdaten für '{ticker_symbol}' im Zeitraum '{period}' gefunden."
        else:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=hist_data.index,
                                         open=hist_data['Open'],
                                         high=hist_data['High'],
                                         low=hist_data['Low'],
                                         close=hist_data['Close'],
                                         name=f'{ticker_symbol}'))

            fig.update_layout(
                title=f'Kursverlauf: {company_name} ({ticker_symbol}) - {period}',
                xaxis_title='Datum',
                yaxis_title='Preis',
                xaxis_rangeslider_visible=True,
                margin=dict(l=20, r=20, t=50, b=20)
            )
            chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    except Exception as e:
        error_msg = f"Fehler beim Generieren des Charts für '{ticker_symbol}': {str(e)}"
        print(f"Fehler in generate_stock_plotly_chart für {ticker_symbol}: {e}")
        if "404 Client Error" in str(e) or "No data found" in str(e).lower():
            error_msg = f"Keine Chartdaten für '{ticker_symbol}' gefunden. Der Ticker könnte falsch oder dekotiert sein."
        elif "429 Client Error" in str(e):
            error_msg = f"Zu viele Anfragen an den Datenprovider für '{ticker_symbol}'. Bitte später erneut versuchen."

    return chart_html, error_msg, company_name


# -- FLASK ROUTEN --

@app.route('/', methods=['GET'])
def landing_page():
    # Leitet direkt zur Suchseite weiter oder zeigt eine einfache Willkommensnachricht
    return redirect(url_for('search_stock_page'))
    # Alternativ: return render_template('landing_page.html')


@app.route('/search', methods=['GET', 'POST'])
def search_stock_page():
    error = None
    if request.method == 'POST':
        ticker_query = request.form.get('ticker_query', '').strip().upper()
        if not ticker_query:
            error = "Bitte gib einen Aktien-Ticker ein."
        else:
            # Validieren, ob der Ticker grundlegende Infos liefert
            basic_info, info_error = get_stock_basic_info(ticker_query)
            if info_error or not basic_info:
                error = info_error if info_error else f"Ticker '{ticker_query}' nicht gefunden oder ungültig."
            else:
                # Wenn valide, zur Detailseite weiterleiten
                return redirect(url_for('stock_detail_page', ticker_symbol=ticker_query))

    # Bei GET oder wenn Fehler im POST auftritt, Suchseite anzeigen
    return render_template('search_page.html', error=error, query=request.form.get('ticker_query', ''))


@app.route('/stock/<string:ticker_symbol>')
def stock_detail_page(ticker_symbol):
    ticker_symbol = ticker_symbol.upper()  # Sicherstellen, dass Ticker groß geschrieben ist

    # 1. Detaillierte Daten abrufen
    stock_details = get_stock_detailed_data(ticker_symbol)

    # 2. Chart generieren (Standardmäßig 1 Jahr)
    chart_period = request.args.get('period', '1y')  # Erlaube Zeitraumänderung über URL-Parameter
    chart_html, chart_error, _ = generate_stock_plotly_chart(ticker_symbol, period=chart_period)

    # Wenn get_stock_detailed_data einen Fehler hatte, diesen anzeigen
    if stock_details.get('error') and not chart_error:  # Wenn Detail-Fehler, aber Chart-Fehler vielleicht nicht
        overall_error = stock_details['error']
    else:
        overall_error = chart_error  # oder der Chart Fehler

    return render_template('stock_detail_page.html',
                           ticker=ticker_symbol,
                           details=stock_details,  # Enthält .name, .info, .financials_html etc. und evtl. .error
                           chart_html=chart_html,
                           current_period=chart_period,
                           error=overall_error)  # Übergibt den Fehler an das Template


@app.route('/test_graph')
def test_graph_page():
    fixed_ticker = "AAPL"  # Test-Ticker
    period = "6mo"  # Test-Zeitraum

    chart_html, error_msg, company_name = generate_stock_plotly_chart(fixed_ticker, period=period)

    return render_template('test_graph_page.html',
                           ticker=fixed_ticker,
                           company_name=company_name,
                           chart_html=chart_html,
                           error=error_msg,
                           period=period)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)