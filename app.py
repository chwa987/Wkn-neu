import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Momentum-Screener", layout="wide")

# ---------------------------- #
# Daten laden
# ---------------------------- #
@st.cache_data
def fetch_data(tickers, start, end):
    data = {}
    for t in tickers:
        try:
            df = yf.download(t, start=start, end=end, progress=False)
            if not df.empty:
                data[t] = df
        except Exception as e:
            st.warning(f"⚠️ Fehler bei {t}: {e}")
    return data

# ---------------------------- #
# Kennzahlen berechnen
# ---------------------------- #
def calculate_indicators(data):
    results = []
    for ticker, df in data.items():
        try:
            df["GD200"] = df["Adj Close"].rolling(200).mean()
            df["GD130"] = df["Adj Close"].rolling(130).mean()
            df["GD50"] = df["Adj Close"].rolling(50).mean()

            mom260 = (df["Adj Close"].pct_change(260) * 100).iloc[-1]
            momjt = ((df["Adj Close"].iloc[-1] / df["Adj Close"].iloc[-120]) - 1) * 100

            rs = (df["Adj Close"].iloc[-1] / df["GD130"].iloc[-1] - 1) * 100
            vol_score = df["Volume"].iloc[-20:].mean() / df["Volume"].mean()

            gd20_signal = "Über GD20" if df["Adj Close"].iloc[-1] > df["Adj Close"].rolling(20).mean().iloc[-1] else "Unter GD20"

            momentum_score = mom260*0.4 + momjt*0.3 + rs*0.2 + vol_score*0.1

            results.append({
                "Ticker": ticker,
                "Kurs aktuell": round(df["Adj Close"].iloc[-1], 2),
                "MOM260 (%)": round(mom260, 2),
                "MOMJT (%)": round(momjt, 2),
                "Relative Stärke (%)": round(rs, 2),
                "Volumen-Score": round(vol_score, 2),
                "Abstand GD50 (%)": round(((df["Adj Close"].iloc[-1] / df["GD50"].iloc[-1]) - 1) * 100, 2),
                "Abstand GD200 (%)": round(((df["Adj Close"].iloc[-1] / df["GD200"].iloc[-1]) - 1) * 100, 2),
                "GD20-Signal": gd20_signal,
                "Momentum-Score": round(momentum_score, 2)
            })
        except Exception as e:
            st.error(f"❌ Fehler bei {ticker}: {e}")
    return pd.DataFrame(results)

# ---------------------------- #
# UI
# ---------------------------- #
st.title("📈 Momentum-Screener")

uploaded_file = st.file_uploader("CSV mit 'Ticker' (und optional 'Name') hochladen", type=["csv"])

if uploaded_file is not None:
    df_upload = pd.read_csv(uploaded_file)
    if "Ticker" not in df_upload.columns:
        st.error("❌ CSV muss mindestens eine Spalte 'Ticker' enthalten.")
        st.stop()
    tickers = df_upload["Ticker"].dropna().unique().tolist()
    st.success(f"{len(tickers)} Ticker aus CSV geladen.")
else:
    ticker_input = st.text_area("Oder Ticker manuell eingeben (kommagetrennt):", "AAPL, MSFT, TSLA, NVDA")
    tickers = [t.strip() for t in ticker_input.split(",") if t.strip()]

start_date = st.date_input("Startdatum", datetime(2018, 1, 1))
end_date = st.date_input("Enddatum", datetime.today())

if st.button("Analyse starten"):
    if not tickers:
        st.warning("⚠️ Bitte gib Ticker ein oder lade eine CSV hoch.")
    else:
        data = fetch_data(tickers, start_date, end_date)
        if not data:
            st.error("❌ Keine Daten geladen.")
        else:
            df_results = calculate_indicators(data)
            df_results = df_results.sort_values(by="Momentum-Score", ascending=False).reset_index(drop=True)
            st.dataframe(df_results)

            # Export
            csv = df_results.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Ergebnisse als CSV exportieren", data=csv, file_name="momentum_results.csv", mime="text/csv")
