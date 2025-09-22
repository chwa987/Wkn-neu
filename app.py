import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Momentum-Screener", page_icon="📈", layout="wide")

# ---------------------------- #
#            Utils             #
# ---------------------------- #

@st.cache_data(show_spinner=False, ttl=60*60)
def fetch_data(tickers, start, end):
    try:
        data = yf.download(tickers, start=start, end=end, progress=False, group_by="ticker")
        return data
    except Exception as e:
        st.error(f"❌ Fehler beim Laden der Daten: {e}")
        return None

def calculate_indicators(data):
    results = []

    for ticker in data.columns.levels[0]:
        try:
            df = data[ticker].dropna()
            if df.empty:
                continue

            close = df["Adj Close"]

            # Indikatoren
            mom260 = (close.iloc[-1] / close.iloc[-260] - 1) * 100 if len(close) > 260 else np.nan
            momjt = (close.pct_change(20).rolling(12).mean().iloc[-1]) * 100 if len(close) > 260 else np.nan
            rs = (close.iloc[-1] / close.mean() - 1) * 100
            vol_score = df["Volume"].iloc[-20:].mean() / df["Volume"].mean()

            gd20 = close.rolling(20).mean().iloc[-1]
            gd50 = close.rolling(50).mean().iloc[-1]
            gd200 = close.rolling(200).mean().iloc[-1]

            score = sum([
                mom260 / 100,
                momjt / 100,
                rs / 100,
                vol_score
            ])

            results.append({
                "Ticker": ticker,
                "Kurs aktuell": round(close.iloc[-1], 2),
                "MOM260 (%)": round(mom260, 2),
                "MOMJT (%)": round(momjt, 2),
                "Relative Stärke (%)": round(rs, 2),
                "Volumen-Score": round(vol_score, 2),
                "GD20": round(gd20, 2),
                "GD50": round(gd50, 2),
                "GD200": round(gd200, 2),
                "Momentum-Score": round(score, 2)
            })

        except Exception as e:
            st.warning(f"⚠️ Fehler bei {ticker}: {e}")

    return pd.DataFrame(results)

def classify_signals(df):
    """
    Kauf/Halten/Verkaufen Logik:
    - Kaufen: Momentum-Score > 2 und Kurs über GD50 + GD200
    - Halten: Momentum-Score > 0 und Kurs über GD200
    - Verkaufen: Alles andere
    """
    signals = []
    for _, row in df.iterrows():
        if row["Momentum-Score"] > 2 and row["Kurs aktuell"] > row["GD50"] and row["Kurs aktuell"] > row["GD200"]:
            signals.append("Kaufen ✅")
        elif row["Momentum-Score"] > 0 and row["Kurs aktuell"] > row["GD200"]:
            signals.append("Halten ➡️")
        else:
            signals.append("Verkaufen ❌")
    df["Signal"] = signals
    return df

# ---------------------------- #
#           UI-Teil            #
# ---------------------------- #

st.title("📈 Momentum-Screener")

tickers_input = st.text_input("Gib Ticker ein (kommagetrennt):", "AAPL, MSFT, TSLA, NVDA")
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

start_date = st.date_input("Startdatum", datetime(2018, 1, 1))
end_date = st.date_input("Enddatum", datetime.today())

if st.button("Analyse starten"):
    if not tickers:
        st.error("❌ Bitte mindestens einen Ticker eingeben.")
    else:
        data = fetch_data(tickers, start_date, end_date)

        if data is None or data.empty:
            st.error("❌ Keine Kursdaten geladen.")
        else:
            df_results = calculate_indicators(data)

            if df_results.empty:
                st.error("❌ Keine Indikatoren berechnet.")
            else:
                # Sortierung
                df_results = df_results.sort_values(by="Momentum-Score", ascending=False)

                # Tabs
                tab1, tab2 = st.tabs(["📊 Ergebnisse", "🟢 Signale"])

                with tab1:
                    st.subheader("Momentum-Analyse")
                    st.dataframe(df_results)

                with tab2:
                    st.subheader("Kaufen / Halten / Verkaufen")
                    df_signals = classify_signals(df_results)
                    st.dataframe(df_signals[["Ticker", "Momentum-Score", "GD50", "GD200", "Signal"]])

                # CSV Export
                csv = df_results.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Ergebnisse als CSV exportieren", csv, "momentum_ergebnisse.csv", "text/csv")
