# --------------------------
# 1. Initial Setup & Imports
# --------------------------
import streamlit as st
st.set_page_config(page_title="Stock Analysis Pro", layout="wide")

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
from predict import get_forecast
import database
import time

# --------------------------
# 2. Enhanced Helper Functions
# --------------------------
def company_to_ticker(company_name):
    """Convert company name to stock ticker using Yahoo Finance's search API"""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": company_name, "quotes_count": 1}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

        response = requests.get(url, params=params, headers=headers)
        data = response.json()

        if data.get('quotes'):
            return data['quotes'][0]['symbol']
        return None
    except Exception as e:
        print(f"Ticker lookup error: {e}")
        return None

def dcf_model(fcf, growth, terminal_growth, discount_rate, years):
    """Discounted Cash Flow valuation model with negative FCF handling"""
    if terminal_growth >= discount_rate:
        raise ValueError("Terminal growth must be less than discount rate")
    
    cash_flows = []
    current_fcf = fcf
    
    # Explicit forecast period
    for year in range(1, years + 1):
        current_fcf *= (1 + growth/100)
        discounted_cf = current_fcf / ((1 + discount_rate/100) ** year)
        cash_flows.append(discounted_cf)

    # Terminal value handling
    final_year_fcf = current_fcf
    if final_year_fcf < 0:
        # Scenario 1: If company dies after forecast period
        # terminal_value = 0
        
        # Scenario 2: If turnaround expected - use industry average margins
        # revenue = ...  # You would need revenue data here
        # industry_fcf_margin = 0.10  # Example: 10% margin
        # terminal_fcf = revenue * industry_fcf_margin
        # terminal_value = (terminal_fcf * (1 + terminal_growth/100)) / 
        #                 (discount_rate/100 - terminal_growth/100)
        
        raise ValueError("Negative final FCF - terminal value calculation invalid")

    terminal_value = (final_year_fcf * (1 + terminal_growth/100)) / (
        (discount_rate/100 - terminal_growth/100))
    
    terminal_value_discounted = terminal_value / ((1 + discount_rate/100) ** years)
    
    total_value = sum(cash_flows) + terminal_value_discounted
    
    return total_value

def validate_weights(weights):
    """Ensure weights sum to 100%"""
    return abs(sum(weights) - 100.0) < 0.01

# --------------------------
# 3. Main App Logic
# --------------------------
def main():
    # Initialize database
    database.init_db()

    # Sidebar inputs
    st.sidebar.header("🔍 Search Parameters")
    company_name = st.sidebar.text_input("Company Name", "Netflix")

    # Convert company name to ticker
    ticker = company_to_ticker(company_name)

    if not ticker:
        st.error(f"Company '{company_name}' not found! Try these examples:")
        st.write("- Microsoft → MSFT")
        st.write("- Apple → AAPL")
        st.write("- Amazon → AMZN")
        st.stop()

    st.sidebar.success(f"Resolved Ticker: {ticker}")

    # Financial assumptions
    years = st.sidebar.slider("Forecast Period (Years)", 1, 10, 5)
    growth_rate = st.sidebar.slider("Initial Growth Rate (%)", 0.0, 20.0, 10.0)
    terminal_growth = st.sidebar.slider("Terminal Growth Rate (%)", 0.0, 5.0, 3.0)
    discount_rate = st.sidebar.slider("Discount Rate (WACC, %)", 5.0, 15.0, 10.0)

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["Stock Analysis", "Portfolio Manager", "Predictions"])

    # Stock Analysis Tab
    with tab1:
         # DCF Valuation Section
        st.subheader("Free Cash Flow Valuation Model")

        try:
            info = yf.Ticker(ticker).info
            fcf = info.get('freeCashflow', 1e9)
            shares_outstanding = info.get('sharesOutstanding', 1e9)
            current_price = info.get('currentPrice', 0)

            fair_value = dcf_model(fcf, growth_rate, terminal_growth, discount_rate, years)
            fair_price = fair_value / shares_outstanding

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                **DCF Assumptions:**
                - Initial FCF: ${fcf/1e9:.1f}B
                - Growth Rate: {growth_rate}%
                - Terminal Growth: {terminal_growth}%
                - Discount Rate (WACC): {discount_rate}%
                """)
            with col2:
                st.metric("Fair Value Estimate", f"${fair_price:.2f} per share")
                st.write(f"**Current Price**: ${current_price:.2f}")

        except Exception as e:
            st.error(f"Error in DCF calculation: {str(e)}")

    # Portfolio Manager Tab - FIXED
    with tab2:
        st.subheader("📦 Portfolio Management")

        # Create New Portfolio
        with st.expander("➕ Create New Portfolio", expanded=True):
            portfolio_name = st.text_input("Portfolio Name")
            selected_stocks = st.multiselect("Select Stocks",
                                           ["NFLX", "AMZN", "GOOG", "TSLA", "MSFT", "META"])

            weights = []
            if selected_stocks:
                cols = st.columns(len(selected_stocks))
                default_weight = 100/len(selected_stocks)
                for i, stock in enumerate(selected_stocks):
                    with cols[i]:
                        weights.append(st.number_input(
                            f"{stock} Weight (%)",
                            min_value=0.0,
                            max_value=100.0,
                            value=round(default_weight, 2)
                        ))

            if st.button("💾 Save Portfolio") and portfolio_name:
                if abs(sum(weights) - 100.0) < 0.01:
                    try:
                        database.save_portfolio(portfolio_name, selected_stocks, weights)
                        st.success("Portfolio saved!")
                    except sqlite3.IntegrityError:
                        st.error("Portfolio name already exists!")
                else:
                    st.error("Weights must sum to 100%")

        # View Portfolios
        with st.expander("📂 View Portfolios"):
            portfolios = database.load_portfolios()
            if not portfolios:
                st.warning("No portfolios found!")

            for portfolio in portfolios:
                st.subheader(portfolio[1])
                stocks = json.loads(portfolio[2])
                weights = json.loads(portfolio[3])

                col1, col2 = st.columns([3, 1])
                with col1:
                    for stock, weight in zip(stocks, weights):
                        st.write(f"- {stock}: {weight}%")
                with col2:
                    if st.button(f"🗑️ Delete", key=f"delete_{portfolio[0]}"):
                        database.delete_portfolio(portfolio[0])
                        st.experimental_rerun()

                st.markdown("---")

    # Predictions Tab
    with tab3:
          # Price Predictions
        st.subheader("🔮 Price Predictions")
        selected_ticker = st.selectbox("Select Stock", ["NFLX", "AMZN", "GOOG", "TSLA"])

        if st.button("Generate Forecast"):
            with st.spinner("Generating forecast..."):
                try:
                    forecast = get_forecast(selected_ticker)
                    if not forecast.empty:
                        fig = px.line(forecast, x='ds', y='yhat',
                                    title=f"{selected_ticker} Forecast",
                                    labels={'yhat': 'Predicted Price'})
                        st.plotly_chart(fig)
                    else:
                        st.warning("Failed to generate forecast")
                except Exception as e:
                    st.error(f"Prediction error: {str(e)}")
if __name__ == "__main__":
    main()
