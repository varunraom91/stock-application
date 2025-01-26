from prophet import Prophet
import yfinance as yf
import pandas as pd
import streamlit as st  # Import Streamlit here


def get_forecast(ticker, periods=365):
    try:
        # Download historical data
        data = yf.download(ticker, period="5y")
        df = data.reset_index()[['Date', 'Close']]
        df.columns = ['ds', 'y']

        # Train model
        model = Prophet()
        model.fit(df)

        # Generate forecast
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

    except Exception as e:
        print(f"Prediction error: {e}")
        return pd.DataFrame()
