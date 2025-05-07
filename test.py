import plotly.graph_objects as go
import yfinance
tsla = yfinance.Ticker("TSLA")
hist = tsla.history(period="1y")
hist.head()