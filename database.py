import sqlite3
import json

def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS portfolios
                (id INTEGER PRIMARY KEY,
                 name TEXT UNIQUE,
                 stocks TEXT,
                 weights TEXT)''')
    conn.commit()
    conn.close()

def save_portfolio(name, stocks, weights):
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO portfolios (name, stocks, weights)
                     VALUES (?, ?, ?)''',
                  (name, json.dumps(stocks), json.dumps(weights)))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Portfolio name already exists")
    finally:
        conn.close()

def load_portfolios():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('SELECT * FROM portfolios')
    portfolios = c.fetchall()
    conn.close()
    return portfolios

def delete_portfolio(portfolio_id):
    """Delete a portfolio by ID"""
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('DELETE FROM portfolios WHERE id = ?', (portfolio_id,))
    conn.commit()
    conn.close()
