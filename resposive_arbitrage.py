import sys
import asyncio
from PyQt6.QtWidgets import ( 
    QApplication, 
    QMainWindow,
    QGridLayout, 
    QTableWidget, 
    QTableWidgetItem, 
    QDoubleSpinBox,
    QWidget, 
    QLabel, 
    QPushButton,
    QHeaderView
)
from pyqt6_multiselect_combobox import MultiSelectComboBox
from PyQt6.QtCore import QThread, pyqtSignal
import ccxt.async_support as ccxt

from utils.exchanges import exchanges_list, order_sizes, build_list_of_exchanges_from_selection
from utils.environement import load_environment
from utils.exchanges import symbols

class AsyncDataFetcher(QThread):
    data_fetched = pyqtSignal(dict)  # Signal to send data to the UI

    def __init__(self, parent=None):
        super().__init__(parent)
        self.form = None
        self.running = False  # Initially, the task is not running
    
    async def fetch_data(self):
        await self.check_requirements()
        exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        try:
            while self.running:
                await self.check_arbitrage_opportunities()
                await asyncio.sleep(1) # Adjust polling interval
                
        except Exception as e:
            print(f"Error fetching data: {e}")
        finally:
            await exchange.close()
    
    async def get_last_prices(self):
        tasks = [exchange.fetch_tickers(self.form["pairs"]) for exchange in self.form['exchanges']]
        results = await asyncio.gather(*tasks)
        return results
      
    async def check_arbitrage_opportunities(self):
        prices = await self.get_last_prices()
        
        for symbol in self.form['pairs']:

            symbol_prices = [exchange_prices[symbol]['last'] for exchange_prices in prices]

            min_price = min(symbol_prices)
            max_price = max(symbol_prices)

            order_size = order_sizes[symbol]

            min_exchange = self.form['exchanges'][symbol_prices.index(min_price)]
            max_exchange = self.form['exchanges'][symbol_prices.index(max_price)]

            min_exchange_fee = min_exchange.fees['trading']['taker']
            min_fee = order_size * min_price * min_exchange_fee

            max_exchange_fee = max_exchange.fees['trading']['taker']
            max_fee = order_size * max_price * max_exchange_fee

            price_profit = max_price - min_price
            profit = (price_profit * order_size) - min_fee - max_fee

            if profit > self.form['min_profit']:  # not taking into account slippage or order book depth
                result = {
                    "symbol": symbol,
                    "buy": min_exchange.id,
                    "min_price": min_price,
                    "sell": max_exchange.id,
                    "max_price": max_price,
                    "profit": profit,
                }
                
                self.data_fetched.emit(result) # type: ignore
            else:
                result = {
                    "symbol": symbol,
                    "buy": min_exchange.id,
                    "min_price": min_price,
                    "sell": max_exchange.id,
                    "max_price": max_price,
                    "profit": "no opportunity",
                }
                
                self.data_fetched.emit(result) # type: ignore
                
    async def check_requirements(self):
        self.form['info_label'].setText("Checking if exchanges support fetchTickers and the symbols we want to trade")
        
        for exchange in self.form['exchanges']:
            if not exchange.has['fetchTickers']:
                print(exchange.id, "does not support fetchTickers")
                sys.exit()
            await exchange.load_markets()

            for symbol in self.form['pairs']:
                if symbol not in exchange.markets:
                    print(exchange.id, "does not support", symbol)
                    sys.exit()

    def run(self):
        asyncio.run(self.fetch_data())

    def stop(self):
        """Stop the data fetching task."""
        self.running = False

    def start_fetching(self, form):
        """Start the data fetching task."""
        self.running = True
        self.form = form
        self.start()  # Start the thread that will call `run`

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spot Arbitrage Scanner")
        # initialize window variables
        self.processing_label = None
        self.maximal_profit = None
        self.run_arbitrage_button = None
        self.arbitrage_table = None
        self.minimal_profit = None
        self.list_coin_pairs_box = None
        self.list_exchanges_box = None
        self.wait_time = 5
        self.API_KEY, self.API_SECRET, self.BYBIT_API_KEY, self.BYBIT_API_SECRET = load_environment()
        
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Layout setup
        layout = QGridLayout()
        container = QWidget()

        layout.addWidget(QLabel("Tracked exchanges:"), 0, 0)
        self.list_exchanges_box = MultiSelectComboBox()
        self.list_exchanges_box.addItems(exchanges_list)
        self.list_exchanges_box.setDisplayType("text")
        self.list_exchanges_box.setOutputType("data")
        self.list_exchanges_box.setDisplayDelimiter(", ")
        layout.addWidget(self.list_exchanges_box, 1, 0)

        layout.addWidget(QLabel("Tracked Pairs:"), 0, 1)
        self.list_coin_pairs_box = MultiSelectComboBox()
        self.list_coin_pairs_box.addItems(symbols)
        self.list_coin_pairs_box.setDisplayType("text")
        self.list_coin_pairs_box.setOutputType("data")
        self.list_coin_pairs_box.setDisplayDelimiter(", ")
        layout.addWidget(self.list_coin_pairs_box, 1, 1)

        layout.addWidget(QLabel("Minimal transaction amount in $:"), 0, 2)
        transaction_amount = QDoubleSpinBox()
        transaction_amount.setRange(0, 1000)
        transaction_amount.setDecimals(1)
        transaction_amount.setValue(0)
        transaction_amount.setSuffix("$")
        layout.addWidget(transaction_amount, 1 , 2)

        layout.addWidget(QLabel("Minimal Profit % (Min. 0.001%):"), 0, 3)
        self.minimal_profit = QDoubleSpinBox()
        self.minimal_profit.setRange(0, 5)
        self.minimal_profit.setDecimals(3)
        self.minimal_profit.setSingleStep(0.1)
        self.minimal_profit.setValue(0)
        self.minimal_profit.setSuffix("%")
        layout.addWidget(self.minimal_profit, 1, 3)

        layout.addWidget(QLabel("Maximal Profit % (Min. 5%):"), 0, 4)        
        self.maximal_profit = QDoubleSpinBox()
        self.maximal_profit.setRange(0, 5)
        self.maximal_profit.setDecimals(1)
        self.maximal_profit.setValue(0)
        self.maximal_profit.setSuffix("%")
        layout.addWidget(self.maximal_profit, 1, 4)
        
        self.start_btn = QPushButton("Start Scanning...")
        layout.addWidget(self.start_btn, 2, 0, 1, 3)
        
        self.close_btn = QPushButton("Stop Scan")
        layout.addWidget(self.close_btn, 2, 3, 1, 2)
        
        self.processing_label = QLabel("Please, choose your setting and click the button to start scanning !")
        layout.addWidget(self.processing_label, 3, 0, 1, 5)

        self.close_btn.clicked.connect(self.stop_task) # type: ignore
        self.start_btn.clicked.connect(self.start_task) # type: ignore
        
        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Exchange 1", "Best Ask",
            "Exchange 2", "Best Bid", "Profit"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table, 4, 0, 1, 5)
        
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Initialize the data fetcher
        self.fetcher = AsyncDataFetcher()
        self.fetcher.data_fetched.connect(self.update_table) # type: ignore

    def update_table(self, data):
        
        # Insert new row at the top
        self.table.insertRow(0)
        self.table.setItem(0, 0, QTableWidgetItem(f"{data['symbol']}"))
        self.table.setItem(0, 1, QTableWidgetItem(f"{data['buy']}"))
        self.table.setItem(0, 2, QTableWidgetItem(f"{data['min_price']}"))
        self.table.setItem(0, 3, QTableWidgetItem(f"{data['sell']}"))
        self.table.setItem(0, 4, QTableWidgetItem(f"{data['max_price']}"))
        self.table.setItem(0, 5, QTableWidgetItem(f"{data['profit']}"))

        # Limit rows to a maximum number to prevent UI overload
        max_rows = 100
        if self.table.rowCount() > max_rows:
            self.table.removeRow(self.table.rowCount() - 1)
    
    def list_selected_exchanges(self):
        return build_list_of_exchanges_from_selection(self.list_exchanges_box.currentData())

    def list_selected_pairs(self):
        return self.list_coin_pairs_box.currentData()
    
    def stop_task(self):
        """Stop the data fetching task when the 'Stop Task' button is clicked."""
        self.processing_label.setText("Stopping Scan ... please wait !")
        self.fetcher.stop()
        self.fetcher.wait()
        self.processing_label.setText("Scan Stopped !")
        print("Task stopped.")

    def start_task(self):
        """Start the data fetching task when the 'Start Task' button is clicked."""
        self.processing_label.setText("Processing arbitrage opportunities ... please wait !")
        form_values = {
            "exchanges" : self.list_selected_exchanges(),
            "pairs" : self.list_selected_pairs(),
            "min_profit": self.minimal_profit.value(),
            "info_label" : self.processing_label 
        }
        self.fetcher.start_fetching(form_values)  # Start fetching data in a new thread
        print("Task started.")

    def closeEvent(self, event):
        """Handle window close event."""
        self.fetcher.stop()
        self.fetcher.wait()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setMinimumSize(1200, 700)
    window.show()
    sys.exit(app.exec())
