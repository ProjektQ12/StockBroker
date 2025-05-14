import yfinance as yf
import pandas as pd
import requests  # Wird für einen grundlegenden Netzwerktest verwendet

# --- Konfiguration ---
VALID_TICKER = "AAPL"  # Ein bekannter, liquider Ticker (z.B. Apple)
INVALID_TICKER = "NONEXISTENTTICKERXYZ123"  # Ein Ticker, der sehr wahrscheinlich nicht existiert
YAHOO_TEST_URL = "https://finance.yahoo.com"  # Eine URL für den grundlegenden Netzwerktest

# Deaktiviere Pandas' Warnung über zukünftige Änderungen im String-Caching (optional, für saubere Ausgabe)
try:
    pd.options.mode.string_storage = "python"
except AttributeError:
    pass  # Ältere Pandas-Versionen haben diese Option möglicherweise nicht


def print_test_header(title):
    print(f"\n--- {title} ---")


def print_success(message):
    print(f"[SUCCESS] {message}")


def print_warning(*message):
    print(f"[WARNING] {message}")


def print_error(message, e=None):
    print(f"[ERROR] {message}")
    if e:
        print(f"        Details: {type(e).__name__}: {e}")


def low_level_yfinance_tests():
    """Führt eine Reihe von Low-Level-Tests mit yfinance durch."""

    # 1. Grundlegender Netzwerk- und DNS-Test mit 'requests'
    print_test_header(f"1. Grundlegender Netzwerk-Test zu {YAHOO_TEST_URL}")
    try:
        pass
        #response = requests.get(YAHOO_TEST_URL, timeout=10)  # 10 Sekunden Timeout
        #response.raise_for_status()  # Löst einen Fehler aus für HTTP-Fehlercodes (4xx oder 5xx)
        #print_success(f"HTTP GET-Anfrage an {YAHOO_TEST_URL} erfolgreich (Status: {response.status_code}).")
        #if "fc.yahoo.com" in response.text or "finance.yahoo.com" in response.text:
            #print_success("Antwort scheint von Yahoo zu stammen.")
        #else:
            #print_warning("Antwort erhalten, aber Inhalt nicht wie erwartet von Yahoo Finance.")
    except requests.exceptions.ConnectionError as e:
        print_error(f"Verbindungsfehler zu {YAHOO_TEST_URL}. Mögliches DNS- oder Netzwerkproblem.", e)
        if "Could not resolve host" in str(e):
            print_warning("Dies deutet stark auf ein DNS-Problem hin.")
        return  # Weitere yfinance-Tests machen wenig Sinn, wenn dies fehlschlägt
    except requests.exceptions.Timeout as e:
        print_error(f"Timeout bei der Verbindung zu {YAHOO_TEST_URL}.", e)
        return
    except requests.exceptions.RequestException as e:
        print_error(f"Fehler bei der Anfrage an {YAHOO_TEST_URL}.", e)
        return

    # 2. Ticker-Objekt Erstellung
    print_test_header(f"2. yf.Ticker Objekt-Erstellung für '{VALID_TICKER}'")
    try:
        stock = yf.Ticker(VALID_TICKER)
        print_success(f"yf.Ticker('{VALID_TICKER}') Objekt erfolgreich erstellt.")
    except Exception as e:
        print_error(f"Konnte kein Ticker-Objekt für '{VALID_TICKER}' erstellen.", e)
        return  # Weitere Tests mit diesem Ticker machen keinen Sinn

    # 3. Abruf von .info
    print_test_header(f"3. Abruf von '.info' für '{VALID_TICKER}'")
    try:
        info = stock.info
        if info and isinstance(info, dict) and 'symbol' in info:
            print_success(
                f"'.info' erfolgreich abgerufen. Symbol: {info.get('symbol')}, Name: {info.get('shortName', 'N/A')}")
            print(f"        Einige Info-Keys: {list(info.keys())[:5]}...")  # Zeige einige Keys
            if not info.get('regularMarketPrice') and not info.get('currentPrice'):
                print_warning(
                    "'.info' abgerufen, aber 'regularMarketPrice' oder 'currentPrice' fehlen. Daten könnten unvollständig sein.")
        elif not info:
            print_warning(
                "'.info' hat ein leeres Wörterbuch oder None zurückgegeben. Ticker könnte delisted sein oder es gibt Probleme.")
        else:
            print_warning(f"'.info' zurückgegeben, aber Format unerwartet oder 'symbol' fehlt. Typ: {type(info)}")
    except Exception as e:
        print_error("Fehler beim Abruf von '.info'.", e)
        if "404 Client Error" in str(e) or "No data found" in str(e):
            print_warning(
                "Dies könnte bedeuten, dass der Ticker nicht (mehr) existiert oder keine Info-Daten verfügbar sind.")

    # 4. Abruf historischer Daten
    print_test_header(f"4. Abruf von '.history(period=\"5d\")' für '{VALID_TICKER}'")
    try:
        hist = stock.history(period="5d")
        if not hist.empty:
            print_success(f"Historische Daten (letzte 5 Tage) erfolgreich abgerufen. {len(hist)} Zeilen.")
            print(f"        Spalten: {hist.columns.tolist()}")
            print(hist.head(2))
        else:
            print_warning("Historische Daten zurückgegeben, aber der DataFrame ist leer.")
    except Exception as e:
        print_error("Fehler beim Abruf historischer Daten.", e)

    # 5. Abruf von "actions" (Dividenden, Splits)
    print_test_header(f"5. Abruf von '.actions' für '{VALID_TICKER}'")
    try:
        actions = stock.actions
        if actions is not None and not actions.empty:
            print_success(f"'.actions' erfolgreich abgerufen. {len(actions)} Aktionen gefunden.")
            print(actions.tail(2))  # Zeige die letzten paar Aktionen
        elif actions is not None and actions.empty:
            print_success(
                "'.actions' erfolgreich abgerufen, aber keine Aktionen für diesen Ticker im Standardzeitraum gefunden.")
        else:
            print_warning("'.actions' hat None oder ein unerwartetes Format zurückgegeben.")
    except Exception as e:
        print_error("Fehler beim Abruf von '.actions'.", e)

    # 6. Abruf von Finanzdaten (Jahresbasis)
    print_test_header(f"6. Abruf von '.financials' für '{VALID_TICKER}'")
    try:
        financials = stock.financials
        if financials is not None and not financials.empty:
            print_success(f"'.financials' erfolgreich abgerufen. Shape: {financials.shape}")
            print(financials.head(2))
        elif financials is not None and financials.empty:
            print_warning(
                f"'.financials' abgerufen, aber DataFrame ist leer. Möglicherweise keine Finanzdaten für {VALID_TICKER} verfügbar.")
        else:
            print_warning("'.financials' hat None oder ein unerwartetes Format zurückgegeben.")
    except Exception as e:
        print_error("Fehler beim Abruf von '.financials'.", e)

    # 7. Abruf von Optionsverfallsdaten
    print_test_header(f"7. Abruf von '.options' (Optionsverfallstermine) für '{VALID_TICKER}'")
    try:
        options_dates = stock.options
        if options_dates:
            print_success(
                f"Optionsverfallstermine erfolgreich abgerufen: {options_dates[:3]}...")  # Zeige die ersten paar
            # Optional: Teste das Abrufen einer Optionskette
            # opt_chain = stock.option_chain(options_dates[0])
            # print_success(f"Optionskette für {options_dates[0]} erfolgreich abgerufen. Calls: {len(opt_chain.calls)}, Puts: {len(opt_chain.puts)}")
        elif isinstance(options_dates, tuple) and not options_dates:
            print_success(
                f"'.options' erfolgreich abgerufen, aber keine Optionsverfallstermine für '{VALID_TICKER}' gefunden (oder keine Optionen handelbar).")
        else:
            print_warning(f"'.options' hat ein unerwartetes Format zurückgegeben: {type(options_dates)}")
    except Exception as e:
        print_error("Fehler beim Abruf von '.options'.", e)
        if "has no attribute 'options'" in str(e).lower() or "No options data found" in str(
                e):  # Ältere yfinance Versionen / keine Daten
            print_warning(
                "Der Ticker hat möglicherweise keine handelbaren Optionen oder die yfinance Version ist veraltet.")

    # 8. Abruf von Nachrichten
    print_test_header(f"8. Abruf von '.news' für '{VALID_TICKER}'")
    try:
        news = stock.news
        if news and isinstance(news, list) and isinstance(news[0], dict):
            print_success(f"'.news' erfolgreich abgerufen. {len(news)} Nachrichtenartikel gefunden.")
            print(f"        Erster Nachrichten-Titel: {news[0].get('title', 'N/A')}")
        elif isinstance(news, list) and not news:
            print_success(
                f"'.news' erfolgreich abgerufen, aber keine Nachrichtenartikel für '{VALID_TICKER}' gefunden.")
        else:
            print_warning(f"'.news' hat ein unerwartetes Format zurückgegeben oder ist leer. Typ: {type(news)}")
    except Exception as e:
        print_error("Fehler beim Abruf von '.news'.", e)

    # 9. Test mit ungültigem Ticker
    print_test_header(f"9. Test mit (wahrscheinlich) ungültigem Ticker '{INVALID_TICKER}'")
    try:
        invalid_stock = yf.Ticker(INVALID_TICKER)
        print_success(
            f"yf.Ticker('{INVALID_TICKER}') Objekt erstellt (erwartet, da die Prüfung oft erst beim Datenabruf erfolgt).")

        invalid_info = invalid_stock.info
        if not invalid_info or (isinstance(invalid_info, dict) and len(invalid_info) <= 1 and (
                not invalid_info.get('regularMarketPrice') and not invalid_info.get(
                'longName'))):  # Oft gibt es für ungültige Ticker ein fast leeres Dict zurück
            print_success(f"'.info' für '{INVALID_TICKER}' ist erwartungsgemäß leer oder minimal.")
        else:
            print_warning(f"'.info' für '{INVALID_TICKER}' hat unerwartete Daten zurückgegeben: {invalid_info}")

        invalid_hist = invalid_stock.history(period="1d")
        if invalid_hist.empty:
            print_success(f"'.history()' für '{INVALID_TICKER}' ist erwartungsgemäß leer.")
        else:
            print_warning(f"'.history()' für '{INVALID_TICKER}' hat unerwartet Daten zurückgegeben.")

    except Exception as e:
        # yfinance kann hier je nach Situation unterschiedliche Fehler werfen
        # Manchmal kommt kein direkter Fehler, sondern leere Daten.
        print_warning(
            f"Ein Fehler oder unerwartetes Verhalten beim Testen von '{INVALID_TICKER}'. Das ist oft erwartet.", e)


if __name__ == "__main__":
    print("Starte yfinance Low-Level Tests...")
    print(f"Verwendete yfinance Version: {yf.__version__}")
    print(f"Verwendete pandas Version: {pd.__version__}")
    print(f"Verwendete requests Version: {requests.__version__}")

    low_level_yfinance_tests()

    print("\n--- Tests abgeschlossen ---")
    print("Bitte überprüfe die [ERROR] und [WARNING] Meldungen.")
    print(
        "Wenn der 'Grundlegende Netzwerk-Test' fehlschlägt, liegt wahrscheinlich ein DNS- oder allgemeines Netzwerkproblem vor.")