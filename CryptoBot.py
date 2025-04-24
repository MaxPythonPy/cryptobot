import sys
import asyncio
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QTextEdit, QWidget
from PyQt6.QtCore import QThread, pyqtSignal
from utils.environement import load_env_variables
import ccxt.pro as ccxtpro

if sys.platform.startswith('win'):
    print('System is Windows')
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class ArbitrageWorker(QThread):
    log_signal = pyqtSignal(str)  # Signal to send log messages to the UI

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_key, self.secret = load_env_variables()
        self.exchange_name = "binance"
        self.min_trade_volume_threshold = 0.01
        self.market_paths = [
            ["BTC/USDT", "ETH/BTC", "ETH/USDT"],  # market path for test purpose
            ["ADA/USDT", "BTC/ADA", "BTC/USDT"]
        ]

    async def run_arbitrage_async(self):
        """Run the arbitrage function asynchronously."""
        await run_arbitrage(
            self.exchange_name,
            self.api_key,
            self.secret,
            self.min_trade_volume_threshold,
            self.market_paths,
            self.log_signal.emit
        )

    def run(self):
        """Run the event loop for the asynchronous function."""
        asyncio.run(self.run_arbitrage_async())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arbitrage Bot")
        self.setGeometry(100, 100, 800, 600)

        # Create UI components
        self.start_button = QPushButton("Run Arbitrage")
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        # Set up layout
        layout = QVBoxLayout()
        layout.addWidget(self.start_button)
        layout.addWidget(self.log_area)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Connect button
        self.start_button.clicked.connect(self.run_arbitrage)

        # Worker thread for asynchronous tasks
        self.worker = ArbitrageWorker()
        self.worker.log_signal.connect(self.log_message)

    def run_arbitrage(self):
        """Start the worker thread."""
        self.log_area.clear()
        self.worker.start()

    def log_message(self, message):
        """Log messages to the text area."""
        self.log_area.append(message)


async def get_portfolio_and_choose_coin(exchange_name, api_key, secret, min_trade_volume_threshold):
    """
    Fetch the user's portfolio and determine the best coin for arbitrage.
    """
    try:
        exchange_class = getattr(ccxtpro, exchange_name)
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
        })

        await exchange.load_markets()
        balance = await exchange.fetch_balance()
        portfolio = balance['total']  # Total balance (available + reserved)

        # Filter coins eligible for arbitrage
        eligible_coins = {coin: amount for coin, amount in portfolio.items() if amount >= min_trade_volume_threshold}

        if not eligible_coins:
            return None, 0

        # Choose the best coin for arbitrage (e.g., highest balance)
        best_coin = max(eligible_coins, key=eligible_coins.get)
        best_coin_balance = eligible_coins[best_coin]

        return best_coin, best_coin_balance

    except Exception as e:
        return None, 0

    finally:
        await exchange.close()


async def calculate_arbitrage_profit(exchange, market_path, start_coin, start_amount):
    """
    Calculate the arbitrage profit for the given market path.
    """
    amount = start_amount
    try:
        for market in market_path:
            ticker = await exchange.fetch_ticker(market)
            bid_price = ticker['bid']
            ask_price = ticker['ask']

            if market.startswith(start_coin):
                amount *= bid_price  # Simulate selling start_coin
            else:
                amount /= ask_price  # Simulate buying start_coin

        return amount - start_amount  # Profit

    except Exception as e:
        return 0


async def run_arbitrage(exchange_name, api_key, secret, min_trade_volume_threshold, market_paths, log_callback):
    """
    Main function to run arbitrage.
    """
    exchange_class = getattr(ccxtpro, exchange_name)
    exchange = exchange_class({
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
    })

    try:
        # Step 1: Retrieve Portfolio and Best Coin
        best_coin, best_coin_balance = await get_portfolio_and_choose_coin(
            exchange_name, api_key, secret, min_trade_volume_threshold
        )

        if not best_coin:
            log_callback("No suitable coin found for arbitrage.")
            return

        log_callback(f"Using {best_coin} with balance {best_coin_balance} for arbitrage.")

        # Step 2: Iterate Through Market Paths and Calculate Profit
        for market_path in market_paths:
            profit = await calculate_arbitrage_profit(exchange, market_path, best_coin, best_coin_balance)
            log_callback(f"Market Path: {market_path} | Profit: {profit}")

            if profit > 0:
                log_callback(f"Arbitrage Opportunity Found: {market_path} | Profit: {profit}")

    except Exception as e:
        log_callback(f"Error during arbitrage: {e}")

    finally:
        await exchange.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
