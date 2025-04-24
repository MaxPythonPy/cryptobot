import sys
import asyncio
import sqlite3
import logging
import time
from datetime import datetime

# Use uvloop if available
if sys.platform.startswith('win'):
    import uvloop
    uvloop.install()
# Fix for aiodns on Windows: Use SelectorEventLoop
if sys.platform.startswith('win'):
    print('system is windows')
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    # Use the default event loop policy for macOS/Linux
    pass

from PyQt6.QtCore import pyqtSignal, QSize, QThread
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QDialog, QMessageBox, QTableWidgetItem, QHBoxLayout, \
    QPushButton

import ccxt.pro as ccxtpro
from ui.main_window import Ui_MainWindow
from ui.manage_api import Ui_api_keys_list
from ui.new_exchange import Ui_new_echange_window
from utils.utils import connect_or_create_db, list_available_coins, available_trading_pairs, tradable_pairs

# Database Path
DB_PATH = "data/crypto_boy.sqlite"

logging.basicConfig(filename="debug.log", level=logging.INFO, format="%(asctime)s - %(message)s")


# Main Window
# Main Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.trade_able_pairs = None
        self.available_trading_pairs = None
        self.new_exchange_dialog = None
        self.manage_api_window = None
        self.worker = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.populate_list_exchanges()
        # self.populate_list_coins()
        self.ui.stop_scan.setDisabled(True)

        # Connect actions to methods
        self.ui.actionAPI_MANAGEMENT.triggered.connect(self.open_manage_api)
        self.ui.start_scan.clicked.connect(self.run_start_process_scan)
        self.ui.stop_scan.clicked.connect(self.stop_process_scan)
        self.ui.reset_black_list.clicked.connect(self.reset_selection)

        # Connect exchange selection change to populate coins
        self.ui.exchange_list.currentIndexChanged.connect(self.on_exchange_selected)

    def on_exchange_selected(self):
        """Triggered when the user selects an exchange from the combobox."""
        exchange_id = self.ui.exchange_list.currentText().lower()
        if exchange_id:
            self.populate_list_coins(exchange_id)

    def populate_list_coins(self, exchange_id):
        """Populate the list of coins based on the selected exchange."""
        self.ui.black_list_symbols.clear()  # Clear the current list

        # Create and start the async worker
        self.async_worker = AsyncWorker(exchange_id)
        self.async_worker.finished.connect(self.update_coin_list)
        self.async_worker.start()

    def update_coin_list(self, spot_pairs):
        """Update the UI with the retrieved spot market pairs."""
        if spot_pairs:
            # Extract unique coins from the spot pairs
            coins = set()
            coins = list_available_coins(spot_pairs)

            # Add coins to the blacklist symbols combobox
            self.ui.black_list_symbols.addItems(sorted(coins))
            self.pre_set_black_list_symbols()
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch spot market pairs.")

    def open_manage_api(self):
        """Open Manage API Window"""
        self.manage_api_window = ManageAPIWindow()
        self.manage_api_window.show()

    def populate_list_exchanges(self):
        rows = self.get_list_active_exchanges()
        if not rows:
            self.ui.warning_message.setText("You have not configured any exchange api yet, please do so first!!!")
            self.ui.config_warnings.show()
        else:
            for row in rows:
                exchange_id, exchange_name = row
                self.ui.exchange_list.addItem(exchange_name, exchange_id)

    def get_list_active_exchanges(self):
        connection = init_db()
        cursor = connection.cursor()

        # Query data
        query = "SELECT exchange_id, exchange_name FROM exchanges WHERE exchange_id IN (SELECT exchange_ext_id FROM exchanges_api_config)"
        cursor.execute(query)
        rows = cursor.fetchall()

        # Close connection
        connection.close()
        return rows

    def stop_process_scan(self):
        self.enable_controls()
        self.print_to_console("********************************************", "red")
        self.print_to_console("CryptoBot", "red")
        self.print_to_console("____________________________________________", "red")
        self.print_to_console("Stopping Scan ... please wait !", "red")
        self.print_to_console("********************************************", "red")
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait()  # Wait for the thread to finish
            self.print_to_console("Scan Stopped!", "red")

    def get_exchange_config(self, exchange_id):
        connection = init_db()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM exchanges_api_config WHERE exchange_ext_id = ?", (exchange_id,))
        config = cursor.fetchone()
        api_config = {}
        if config:
            api_config['apiKey'] = config[1]
            api_config['secret'] = config[2]
            api_config['enableRateLimit'] = True
            api_config['uid'] = config[3] or None
            api_config['login'] = config[6] or None
            api_config['password'] = config[7] or None
            api_config['twofa'] = config[8] or None
            api_config['privateKey'] = config[9] or None
            api_config['walletAddress'] = config[10] or None
            api_config['token'] = config[11] or None
        return api_config

    def run_start_process_scan(self):
        exchange_id = self.ui.exchange_list.currentData()
        self.disable_controls()
        self.save_black_list_config()
        black_list_symbols = self.ui.black_list_symbols.currentData()
        self.ui.console.clear()
        # Start the scan
        self.print_to_console("********************************************", "green")
        self.print_to_console("CryptoBot V1", "green")
        self.print_to_console("____________________________________________", "green")
        self.print_to_console(f"Exchange ID: {self.ui.exchange_list.currentText()}", "green")
        self.print_to_console(f"Blacklisted Symbols: {black_list_symbols}", "green")
        self.print_to_console("____________________________________________", "green")
        self.print_to_console("Starting scan...", "green")
        self.print_to_console("********************************************", "green")

        self.start_process_scan(exchange_id, black_list_symbols)

    def start_process_scan(self, exchange_id, black_list_symbols):
        is_sandbox = self.ui.sandbox_mode.isChecked()
        if not exchange_id:
            QMessageBox.warning(self, "Validation Error", "Please select an exchange to start the scan.")
            return

        if not black_list_symbols:
            QMessageBox.warning(self, "Validation Error", "Please enter a list of symbols to exclude from the scan.")
            return

        exchange_config = self.get_exchange_config(exchange_id)

        self.worker = ArbitrageWorker(
            exchange=self.ui.exchange_list.currentText().lower(),
            exchange_config=exchange_config,
            black_listed_coins=black_list_symbols,
            sandbox_mode=is_sandbox,
            min_trade_volume_threshold=self.ui.min_transaction_amount.value()
        )
        self.worker.result_signal.connect(self.print_to_console)
        self.worker.start()

    def print_to_console(self, text, color="white"):
        console_output_template = f"<span style='color: {color}'>{text}</span>"
        self.ui.console.append(console_output_template)

        cursor = self.ui.console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.ui.console.setTextCursor(cursor)

    def reset_selection(self):
        self.ui.black_list_symbols.clear()

    def disable_controls(self):
        self.ui.exchange_list.setDisabled(True)
        self.ui.black_list_symbols.setDisabled(True)
        self.ui.start_scan.setDisabled(True)
        self.ui.reset_black_list.setDisabled(True)
        self.ui.stop_scan.setDisabled(False)

    def enable_controls(self):
        self.ui.exchange_list.setDisabled(False)
        self.ui.black_list_symbols.setDisabled(False)
        self.ui.start_scan.setDisabled(False)
        self.ui.reset_black_list.setDisabled(False)
        self.ui.stop_scan.setDisabled(True)

    def save_black_list_config(self):
        connection = init_db()
        cursor = connection.cursor()
        blacklisted_symbols = self.load_black_list_symbols()
        currently_selected_coins = self.build_blacklist()
        if blacklisted_symbols is not None:
            symbol_id, symbol_code = blacklisted_symbols
            query = """
                UPDATE black_list_symbols set symbol_code = ? WHERE symbol_id = ?
            """
            cursor.execute(query, (currently_selected_coins, symbol_id))
        else:
            query = """
                        INSERT INTO black_list_symbols (symbol_code)
                        VALUES (?)
                    """
            cursor.execute(query, (currently_selected_coins,))
        connection.commit()

    def load_black_list_symbols(self):
        connection = init_db()
        cursor = connection.cursor()
        cursor.execute("SELECT symbol_id, symbol_code FROM black_list_symbols ORDER BY symbol_id DESC LIMIT 1")
        config = cursor.fetchone()
        return config

    def pre_set_black_list_symbols(self):
        symbols = self.load_black_list_symbols()
        if symbols is not None:
            symbol_id, symbol_code = symbols
            list_preset = list()
            for code in symbol_code.split(','):
                index = self.ui.black_list_symbols.findText(code.strip())  # Find the index of the text
                if index != -1:  # Ensure the text exists in the combo box
                    list_preset.append(index)
            self.ui.black_list_symbols.setCurrentIndexes(list_preset)

    def build_blacklist(self):
        selected_coins = self.ui.black_list_symbols.currentData()
        return ','.join(selected_coins)
    
# Manage API Window
class ManageAPIWindow(QWidget):
    new_exchange_dialog: QDialog

    def __init__(self):
        super().__init__()
        self.ui = Ui_api_keys_list()
        self.ui.setupUi(self)
        self.populate_list_exchanges_config()
        self.ui.add_new_api.clicked.connect(self.open_new_exchange)

    def open_new_exchange(self):
        """Open New Exchange Dialog"""
        self.new_exchange_dialog = NewExchangeDialog()
        self.new_exchange_dialog.data_saved.connect(self.reload_table)  # type: ignore  # Connect signal to method
        self.new_exchange_dialog.exec()

    def populate_list_exchanges_config(self):
        """Populate the API Keys Table"""
        self.ui.list_apis_table.setRowCount(0)  # Clear the table first
        connection = init_db()
        cursor = connection.cursor()
        query = """SELECT
                config.exchange_config_id,
                ex.exchange_name,
                config.api_key,
                config.api_secret,
                config.passphrase,
                config.uid,
                ex.exchange_keygen_url
                FROM exchanges_api_config config
                LEFT JOIN exchanges ex ON config.exchange_ext_id = ex.exchange_id;"""
        cursor.execute(query)
        rows = cursor.fetchall()

        # Set up the table
        self.ui.list_apis_table.setRowCount(len(rows))
        self.ui.list_apis_table.resizeRowsToContents()
        self.ui.list_apis_table.setColumnCount(6)  # 5 for data + 1 for action buttons

        for row_idx, row_data in enumerate(rows):
            # Populate exchange_name, api_key, api_secret, passphrase, uid, exchange_keygen_url,
            self.ui.list_apis_table.setRowHeight(row_idx, 40)
            self.ui.list_apis_table.setItem(row_idx, 0, QTableWidgetItem(row_data[1]))  # Exchange Name
            self.ui.list_apis_table.setItem(row_idx, 1, QTableWidgetItem(row_data[2]))  # API Key
            self.ui.list_apis_table.setItem(row_idx, 2, QTableWidgetItem(row_data[3]))  # API Secret
            self.ui.list_apis_table.setItem(row_idx, 3, QTableWidgetItem(row_data[4]))  # API Passphrase
            self.ui.list_apis_table.setItem(row_idx, 4, QTableWidgetItem(row_data[5]))  # API UID

            # Create buttons
            action_layout = QHBoxLayout()
            action_widget = QWidget()
            # Button with an icon, a text, and a parent widget
            open_button = QPushButton(
                icon=QIcon("./assets/icons/web-circle.svg"),
                parent=self
            )
            open_button.setToolTip("Open URL")
            open_button.setFixedSize(30, 30)
            open_button.setIconSize(QSize(30, 30))
            open_button.setStyleSheet("QPushButton{\n"
                                      "    background: #fff;\n"
                                      "}")
            open_button.clicked.connect(lambda _, url=row_data[6]: self.open_url(url))  # type: ignore # Exchange URL
            action_layout.addWidget(open_button)

            edit_button = QPushButton(
                icon=QIcon("./assets/icons/edit-circle.svg"),
                parent=self
            )
            edit_button.setToolTip("Edit")
            edit_button.setFixedSize(30, 30)
            edit_button.setIconSize(QSize(30, 30))
            edit_button.setStyleSheet("QPushButton{\n"
                                      "    background: #fff;\n"
                                      "}")
            edit_button.clicked.connect(lambda _, row_id=row_data[0]: self.edit_entry(row_id))  # type: ignore
            action_layout.addWidget(edit_button)

            delete_button = QPushButton(
                icon=QIcon("./assets/icons/close-circle.svg"),
                parent=self
            )
            delete_button.setToolTip("Delete")
            delete_button.setFixedSize(30, 30)
            delete_button.setIconSize(QSize(30, 30))
            delete_button.setStyleSheet("QPushButton{\n"
                                        "    background: #fff;\n"
                                        "}")
            delete_button.clicked.connect(lambda _, row_id=row_data[0]: self.delete_entry(row_id))  # type: ignore
            action_layout.addWidget(delete_button)

            action_widget.setLayout(action_layout)
            self.ui.list_apis_table.setCellWidget(row_idx, 5, action_widget)

        connection.close()

    def reload_table(self):
        """Reload the API Keys Table"""
        self.populate_list_exchanges_config()

    def delete_entry(self, row_id):
        connection = init_db()
        cursor = connection.cursor()

        # Confirm deletion
        reply = QMessageBox.question(
            self, 'Confirm Deletion',
            f"Are you sure you want to delete entry with ID: {row_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            cursor.execute("DELETE FROM exchanges_api_config WHERE exchange_config_id = ?", (row_id,))
            connection.commit()
            self.reload_table()  # Refresh the table
            QMessageBox.information(self, "Deleted", f"Entry with ID: {row_id} has been deleted.")

        connection.close()

    def edit_entry(self, row_id):
        """Open the edit dialog for the selected entry"""
        self.new_exchange_dialog = NewExchangeDialog(row_id=row_id)
        self.new_exchange_dialog.data_saved.connect(self.reload_table)  # type: ignore  # Refresh the table after saving
        self.new_exchange_dialog.exec()

    def open_url(self, url):
        if url:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(url))


# New Exchange Dialog
class NewExchangeDialog(QDialog):
    data_saved = pyqtSignal()  # Signal to notify that data has been saved

    def __init__(self, row_id=None):
        super().__init__()
        self.ui = Ui_new_echange_window()
        self.ui.setupUi(self)

        # Connect Save button
        self.ui.buttonBox.accepted.connect(self.save_to_db)
        # self.populate_list_exchanges()
        self.row_id = row_id  # Store the row_id for editing purposes

        if self.row_id:
            self.load_data()  # Load data if editing
        else:
            self.populate_list_exchanges()

    def load_data(self):
        """Load existing data for editing"""
        try:
            connection = init_db()
            cursor = connection.cursor()
            query = """
                SELECT api_key, api_secret, uid, passphrase, login, password, twofa, privateKey, walletAddress, token, exchange_ext_id
                FROM exchanges_api_config
                WHERE exchange_config_id = ?
                """
            cursor.execute(query, (self.row_id,))
            row = cursor.fetchone()

            if row:
                api_key, api_secret, uid, passphrase, login, password, twofa, private_key, wallet_address, token, exchange_ext_id = row
                self.ui.api_key.setText(api_key)
                self.ui.api_secret.setText(api_secret)
                self.ui.api_passphrase.setText(passphrase or "")
                self.ui.uid.setText(uid or "")
                self.ui.api_login.setText(login or "")
                self.ui.api_password.setText(password or "")
                self.ui.api_2fa.setText(twofa or "")
                self.ui.api_token.setText(token or "")
                self.ui.api_private_key.setText(private_key or "")
                self.ui.api_walled_address.setText(wallet_address or "")
                self.populate_list_exchanges(selected_exchange_id=exchange_ext_id)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
        finally:
            connection.close()

    def populate_list_exchanges(self, selected_exchange_id=None):
        """Populate the dropdown with exchanges and optionally select one"""
        connection = init_db()
        cursor = connection.cursor()

        # Query data
        if selected_exchange_id is None:
            query = "SELECT exchange_id, exchange_name FROM exchanges WHERE exchange_id NOT IN(SELECT exchange_ext_id FROM exchanges_api_config)"
        else:
            query = "SELECT exchange_id, exchange_name FROM exchanges"
        cursor.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            exchange_id, exchange_name = row
            self.ui.list_exchanges.addItem(exchange_name, exchange_id)

            if selected_exchange_id and exchange_id == selected_exchange_id:
                self.ui.list_exchanges.setCurrentIndex(self.ui.list_exchanges.count() - 1)

        connection.close()

    def save_to_db(self):
        """Save the edited or new exchange data to the database"""
        exchange_id = self.ui.list_exchanges.currentData()
        api_key = self.ui.api_key.text().strip()
        api_secret = self.ui.api_secret.text().strip()
        api_passphrase = self.ui.api_passphrase.text().strip() or None
        uid = self.ui.uid.text().strip() or None
        login = self.ui.api_login.text() or None
        password = self.ui.api_password.text() or None
        twofa = self.ui.api_2fa.text() or None
        private_key = self.ui.api_private_key.text().strip() or None
        wallet_address = self.ui.api_walled_address.text().strip() or None
        token = self.ui.api_token.text().strip() or None

        if not api_key or not api_secret or not exchange_id:
            QMessageBox.warning(self, "Validation Error", "A missing Exchange or API Key or and Secret are required.")
            return

        try:
            connection = init_db()
            cursor = connection.cursor()

            if self.row_id:
                # Update existing entry
                query = """
                    UPDATE exchanges_api_config SET 
                    api_key = ?,
                    api_secret = ?, 
                    uid = ?, 
                    passphrase = ?, 
                    login = ?,
                    password = ?,
                    twofa = ?,
                    privateKey = ?,
                    walletAddress = ?,
                    token = ?,
                    exchange_ext_id = ?
                    WHERE exchange_config_id = ?
                """
                cursor.execute(query, (
                    api_key,
                    api_secret,
                    uid,
                    api_passphrase,
                    login,
                    password,
                    twofa,
                    private_key,
                    wallet_address,
                    token,
                    exchange_id,
                    self.row_id
                ))
            else:
                # Insert new entry
                query = """
                    INSERT INTO exchanges_api_config (
                    api_key = ?,
                    api_secret = ?, 
                    uid = ?, 
                    passphrase = ?, 
                    login = ?,
                    password = ?,
                    twofa = ?,
                    privateKey = ?,
                    walletAddress = ?,
                    token = ?,
                    exchange_ext_id = ?)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    api_key,
                    api_secret,
                    uid,
                    api_passphrase,
                    login,
                    password,
                    twofa,
                    private_key,
                    wallet_address,
                    token,
                    exchange_id
                ))

            connection.commit()
            self.data_saved.emit()  # type: ignore  # Emit signal
            QMessageBox.information(self, "Success", "Exchange data saved successfully.")

        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Database Error", "Duplicate entry detected.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
        finally:
            connection.close()


class ArbitrageWorker(QThread):
    """
    Worker thread to run the triangular arbitrage calculation.
    """
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, exchange, exchange_config, black_listed_coins, sandbox_mode=True, min_trade_volume_threshold=1):
        super().__init__()
        self.running = True
        self.black_listed_coins = black_listed_coins
        self.sandbox_mode = sandbox_mode
        self.exchange = exchange
        self.exchange_config = exchange_config
        self.min_trade_volume_threshold = min_trade_volume_threshold  # Default threshold
        self.task = None  # Main task
        self.running_tasks = set()  # Track all running tasks
        self.loop = asyncio.new_event_loop() # Use QEventLoop for asynchronous tasks

    async def run_arbitrage(self):
        """Run the arbitrage function asynchronously."""
        try:
            await run_arbitrage(
                running=lambda: self.running,
                exchange_id=self.exchange,
                exchange_config=self.exchange_config,
                result_signal=self.result_signal.emit,
                error_signal=self.error_signal.emit,
                min_trade_volume_threshold=self.min_trade_volume_threshold,
                running_tasks=self.running_tasks,  # Pass the running tasks set
                black_listed_coins=self.black_listed_coins
            )
        except asyncio.CancelledError:
            self.result_signal.emit("Arbitrage task was canceled.")
        except Exception as e:
            self.error_signal.emit(f"Error in arbitrage: {str(e)}")

    def run(self):
        """Run the event loop for the asynchronous function."""
        asyncio.set_event_loop(self.loop)  # Set the event loop for this thread
        self.task = self.loop.run_until_complete(self.run_arbitrage())

    def stop(self):
        """Stop all running tasks and clean up."""
        print("Stopping scan...")
        self.running = False
        for task in self.running_tasks:
            task.cancel()
        self.running_tasks.clear()
        self.loop.stop()  # Stop the event loop


# Worker class for running async tasks
# Class OK
class AsyncWorker(QThread):
    finished = pyqtSignal(list)  # Signal to emit the result

    def __init__(self, exchange_id):
        super().__init__()
        self.exchange_id = exchange_id

    def run(self):
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(fetch_spot_markets(self.exchange_id))
        self.finished.emit(result)  # Emit the result when done

# Function OK
async def fetch_spot_markets(exchange_id):
    # Initialize the exchange
    exchange = getattr(ccxtpro, exchange_id)({
        'enableRateLimit': True,  # Enable rate limiting to avoid being banned
    })

    try:
        # Fetch all markets
        markets = await exchange.fetch_markets()

        # Filter for spot markets
        spot_markets = [market for market in markets if market['spot']]

        # Extract trading pairs
        spot_pairs = [market['symbol'] for market in spot_markets]

        return spot_pairs

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the exchange connection
        await exchange.close()

async def run_arbitrage(running, exchange_id, exchange_config, result_signal, error_signal, min_trade_volume_threshold, running_tasks, black_listed_coins):
    """Run the arbitrage detection and emit results."""
    print("run_arbitrage")
    exchange = get_exchange(exchange_id, exchange_config, result_signal)
    try:
        profitable_trades = []
        await initialize_exchange(exchange, result_signal)
        result_signal("Market Data fetched !")
        result_signal("Building and analizing triangular opportunities")
        task = asyncio.create_task(get_triangulation_opportunities(exchange, min_trade_volume_threshold, result_signal, running_tasks, black_listed_coins))
        running_tasks.add(task)
        task.add_done_callback(lambda t: running_tasks.discard(t))  # Remove task from the set when done
        try:
            profitable_trades = await task
        except ValueError as e:
            result_signal(f'{e}')
        while running:
            for trade in profitable_trades:
                profit_info = (
                    f"Profitable Triangle: {trade['triangle']}\n"
                    f"Profit: {trade['profit']:.6f} units\n"
                    f"Details: {trade['details']}\n"
                )
                result_signal(profit_info)

            await asyncio.sleep(1)
    except asyncio.CancelledError:
        result_signal("Arbitrage task was stopped.")
    except Exception as e:
        print(f"arbitrage detection error : {e}")
        logging.info(f"arbitrage detection error : {e}")
        error_signal(f"arbitrage detection error : {str(e)}")
    finally:
        if exchange:
            await exchange.close()

# Function Call OK
async def get_triangulation_opportunities(exchange, min_trade_volume_threshold, result_signal, running_tasks, white_listed_coins):
    print("get_triangulation_opportunities")
    available_pairs = list(exchange.markets.keys())
    task = asyncio.create_task(get_portfolio_and_choose_coin(
        exchange, min_trade_volume_threshold, running_tasks
    ))
    running_tasks.add(task)
    task.add_done_callback(lambda t: running_tasks.discard(t))  # Remove task from the set when done

    best_coin, best_coin_balance, eligible_coins = await task
    if best_coin and best_coin_balance and eligible_coins :
        result_signal(f"Best suited coin in your ballance is {best_coin} with a balance of {best_coin_balance}")
        result_signal(f"Other eligible coins are {', '.join(eligible_coins)}")
    else:
        result_signal(f"Your portfolio does not seems to have any balance, check your API KEY/ API Secret for potential error !")
    try:
        triangular_pairs = tradable_pairs(available_pairs, eligible_coins, white_listed_coins)
        result_signal('list of triangular paris are :')
        result_signal(triangular_pairs)
    except ValueError as err:
        result_signal(f"The exchange you selected does not contain any coin : {err}")
        raise ValueError('Arbitrage aborted not enough coins on the exchange to perform actions')
    return await calculate_arbitrage_profit(exchange, triangular_pairs, min_trade_volume_threshold, result_signal, running_tasks)

# function OK
async def get_portfolio_and_choose_coin(exchange, min_trade_volume_threshold, running_tasks):
    """
    Fetch the user's portfolio and determine eligible coins for trading.
    """
    print("get_portfolio_and_choose_coin")
    try:
        # await exchange.load_markets()
        task = asyncio.create_task(exchange.fetch_balance())
        running_tasks.add(task)
        task.add_done_callback(lambda t: running_tasks.discard(t))  # Remove task from the set when done
        
        balance = await task
        portfolio = balance['total']  # Total balance (available + reserved)

        # Filter coins eligible for arbitrage
        eligible_coins = {coin: amount for coin, amount in portfolio.items() if amount >= min_trade_volume_threshold}

        if not eligible_coins:
            return None, 0, []

        # Choose the best coin for arbitrage (e.g., highest balance)
        best_coin = max(eligible_coins, key=eligible_coins.get)
        best_coin_balance = eligible_coins[best_coin]

        # Get the list of eligible coins
        eligible_coin_list = list(eligible_coins.keys())

        #to-do : for testing purpose
        return 'SOL', 100, ['SOL', 'USDT', 'BTC', 'ETH']
        
        return best_coin, best_coin_balance, eligible_coin_list

    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        logging.info(f"Error fetching portfolio: {e}")
        return None, 0, []

    finally:
        await exchange.close()

# Global Variables
semaphore = asyncio.Semaphore(10)  # Limit concurrent requests to 10
cache = {}  # Cache for storing order books
cache_ttl = 60  # Time-to-live for cached order books in seconds


async def fetch_order_book(
    exchange,
    pair,
    result_signal,
    running_tasks,
    retries=3,
    backoff=1,
    throttle_delay=0.1,
):
    """
    Fetch the order book for a given pair with concurrency limiting, throttling, caching, and retries.
    Args:
        exchange: The exchange instance.
        pair: The trading pair (e.g., 'BTC/USDT').
        retries: Number of retries on failure.
        backoff: Base delay for exponential backoff (in seconds).
        throttle_delay: Delay between requests to prevent throttling (in seconds).
    Returns:
        The order book for the given pair or None on failure.
    """
    print(f"Fetching order book for pair: {pair}")
    result_signal(f"Fetching order book for pair: {pair}")
    # Check if the pair is in the cache and still valid
    current_time = time.time()
    if pair in cache:
        cached_time, cached_order_book = cache[pair]
        if current_time - cached_time < cache_ttl:  # Cache is still valid
            logging.info(f"Using cached order book for pair: {pair}")
            return pair, cached_order_book  # Return as a tuple

    # Throttling: Introduce a small delay before making the request
    await asyncio.sleep(throttle_delay)

    # Fetch the order book with concurrency limiting and retries
    async with semaphore:
        for attempt in range(1, retries + 1):
            try:
                logging.info(f"Fetching order book for pair: {pair} (Attempt {attempt})")
                result_signal(f"Fetching order book for pair: {pair} (Attempt {attempt})")
                
                task = asyncio.create_task(exchange.fetch_order_book(pair))
                running_tasks.add(task)
                task.add_done_callback(lambda t: running_tasks.discard(t))  # Remove task from the set when done
                
                order_book = await task

                # Cache the result
                cache[pair] = (time.time(), order_book)

                return pair, order_book  # Return as a tuple
            except Exception as e:
                logging.error(
                    f"Error fetching order book for {pair} on attempt {attempt}: {e}"
                )
                if attempt < retries:
                    await asyncio.sleep(backoff * (2 ** (attempt - 1)))  # Exponential backoff
                else:
                    logging.error(f"Failed to fetch order book for pair: {pair} after {retries} retries.")
                    return pair, None  # Return pair with None

async def calculate_arbitrage_profit(exchange, triangular_pairs, min_trade_volume_threshold, result_signal, running_tasks):
    result_signal("calculating arbitrage profit starting...")
    fees = exchange.fees.get('trading', {}).get('taker', 0.001)  # Default fee
    print("fees")
    print(fees)
    all_pairs = set(triangle[pair] for triangle in triangular_pairs for pair in ['pair_a', 'pair_b', 'pair_c'])
    tasks = [fetch_order_book(exchange, pair, result_signal, running_tasks) for pair in all_pairs]
    # Collect results
    order_books = await asyncio.gather(*tasks)
    # Build the dictionary safely
    order_book_dict = {pair: book for pair, book in order_books if book is not None}
    # print('Order book : ')
    # print(order_book_dict)
    profitable_trades = []

    for triangle in triangular_pairs:
        # print('triangle arbitrage')
        # print(triangle)
        pair_a, pair_b, pair_c = triangle["pair_a"], triangle["pair_b"], triangle["pair_c"]
        order_book_a, order_book_b, order_book_c = order_book_dict.get(pair_a), order_book_dict.get(
            pair_b), order_book_dict.get(pair_c)
        if not order_book_a or not order_book_b or not order_book_c:
            continue

        min_volume_a = get_dynamic_min_volume(order_book_a, min_trade_volume_threshold)
        min_volume_b = get_dynamic_min_volume(order_book_b, min_trade_volume_threshold)
        min_volume_c = get_dynamic_min_volume(order_book_c, min_trade_volume_threshold)

        # Check against the minimum trade volume threshold
        if min_volume_a < min_trade_volume_threshold or \
                min_volume_b < min_trade_volume_threshold or \
                min_volume_c < min_trade_volume_threshold:
            print('Check against the minimum trade volume threshold : Failed')
            continue

        a_ask = order_book_a['asks'][0][0] if order_book_a['asks'] else None
        b_bid = order_book_b['bids'][0][0] if order_book_b['bids'] else None
        c_bid = order_book_c['bids'][0][0] if order_book_c['bids'] else None

        if not (a_ask and b_bid and c_bid):
            continue

        start_amount = 1.0
        amount_b = (start_amount / a_ask) * (1 - fees)
        amount_c = (amount_b * b_bid) * (1 - fees)
        end_amount = (amount_c * c_bid) * (1 - fees)
        profit = end_amount - start_amount

        if profit > 0:
            profitable_trades.append({
                "triangle": triangle,
                "profit": profit,
                "details": {
                    "start_amount": start_amount,
                    "end_amount": end_amount,
                    "a_ask": a_ask,
                    "b_bid": b_bid,
                    "c_bid": c_bid,
                    "min_volume_a": min_volume_a,
                    "min_volume_b": min_volume_b,
                    "min_volume_c": min_volume_c
                }
            })

    return profitable_trades

def get_dynamic_min_volume(order_book, min_trade_volume_threshold=0):
    """
    Dynamically determine the minimum tradable volume based on the order book.
    Args:
        order_book (dict): Order book data.
        min_trade_volume_threshold (float): Minimum volume required for a trade.
    Returns:
        float: Minimum tradable volume or 0 if insufficient liquidity.
    """
    print("get_dynamic_min_volume")
    if not order_book.get('bids') or not order_book.get('asks'):
        return 0  # No valid data in the order book

    best_ask_volume = order_book['asks'][0][1] if order_book['asks'] else float('inf')
    best_bid_volume = order_book['bids'][0][1] if order_book['bids'] else float('inf')

    # Minimum volume from both sides
    min_volume = min(best_ask_volume, best_bid_volume)

    # Ensure volume meets the threshold
    return min_volume if min_volume >= min_trade_volume_threshold else 0

async def initialize_exchange(exchange, result_signal):
    """Initialize the exchange."""
    print("initialize_exchange")
    result_signal("Initializing Exchange and fetching Market Data.......")
    await exchange.load_markets()
    
def get_exchange(exchange_id, exchange_config, result_signal):
    print("get_exchange")
    
    result_signal(f"Loading Exchange : {exchange_id}")
    exchange = getattr(ccxtpro, exchange_id)(exchange_config)
    return exchange

# Initialize SQLite Database
def init_db():
    return connect_or_create_db()



# async def execute_arbitrage_trade(exchange, trade_details, sandbox_mode, result_signal):
#     """
#     Execute trades based on a triangular arbitrage opportunity.
#     Args:
#         exchange: The exchange instance.
#         trade_details: Details of the profitable triangle.
#         sandbox_mode: Boolean to determine if trades are real or simulated.
#         result_signal: Function to emit trade results.
#     """
#     try:
#         triangle = trade_details["triangle"]
#         a_ask = trade_details["details"]["a_ask"]
#         b_bid = trade_details["details"]["b_bid"]
#         c_bid = trade_details["details"]["c_bid"]
#         start_amount = trade_details["details"]["start_amount"]

#         pair_a, pair_b, pair_c = triangle["pair_a"], triangle["pair_b"], triangle["pair_c"]

#         # Trade 1: Buy asset B using asset A (pair_a)
#         result_signal(f"Executing Trade 1: Buying {pair_a.split('/')[1]} using {pair_a.split('/')[0]}")
#         if not sandbox_mode:
#             order_a = await exchange.create_order(
#                 symbol=pair_a,
#                 type="market",
#                 side="buy",
#                 amount=start_amount
#             )
#             result_signal(f"Trade 1 executed: {order_a}")
#         else:
#             result_signal(f"Simulated Trade 1: Bought {start_amount} {pair_a.split('/')[1]} at {a_ask}")

#         # Trade 2: Sell asset B for asset C (pair_b)
#         amount_b = (start_amount / a_ask) * (1 - exchange.fees['trading']['taker'])
#         result_signal(f"Executing Trade 2: Selling {pair_b.split('/')[0]} for {pair_b.split('/')[1]}")
#         if not sandbox_mode:
#             order_b = await exchange.create_order(
#                 symbol=pair_b,
#                 type="market",
#                 side="sell",
#                 amount=amount_b
#             )
#             result_signal(f"Trade 2 executed: {order_b}")
#         else:
#             result_signal(f"Simulated Trade 2: Sold {amount_b} {pair_b.split('/')[0]} at {b_bid}")

#         # Trade 3: Sell asset C for asset A (pair_c)
#         amount_c = (amount_b * b_bid) * (1 - exchange.fees['trading']['taker'])
#         result_signal(f"Executing Trade 3: Selling {pair_c.split('/')[0]} for {pair_c.split('/')[1]}")
#         if not sandbox_mode:
#             order_c = await exchange.create_order(
#                 symbol=pair_c,
#                 type="market",
#                 side="sell",
#                 amount=amount_c
#             )
#             result_signal(f"Trade 3 executed: {order_c}")
#         else:
#             result_signal(f"Simulated Trade 3: Sold {amount_c} {pair_c.split('/')[0]} at {c_bid}")

#         # Calculate final profit
#         end_amount = (amount_c * c_bid) * (1 - exchange.fees['trading']['taker'])
#         profit = end_amount - start_amount
#         result_signal(f"Arbitrage completed! Profit: {profit:.6f} units")

#     except asyncio.CancelledError:
#         result_signal("Arbitrage task was cancelled.")
#     except Exception as e:
#         result_signal(f"Error executing arbitrage trade: {e}")
#         logging.error(f"Arbitrage trade error: {e}")

# async def execute_trades_in_batches(exchange, opportunities, sandbox_mode, result_signal, batch_size=10):
#     """
#     Execute trades in batches to handle large numbers of trades while respecting rate limits.
#     Args:
#         exchange: The exchange instance.
#         opportunities: List of profitable trades.
#         sandbox_mode: Boolean to determine if trades are real or simulated.
#         result_signal: Function to emit trade results.
#         batch_size: Number of trades to execute concurrently in each batch.
#     """
#     for i in range(0, len(opportunities), batch_size):
#         batch = opportunities[i:i + batch_size]
#         result_signal(f"Executing batch {i // batch_size + 1}: {len(batch)} trades")
#         attempts = 0
#         backoff = 2  # Initial backoff time in seconds
#         while attempts < 5:  # Maximum of 5 retry attempts
#             try:
#                 await asyncio.gather(*(execute_arbitrage_trade(exchange, trade, sandbox_mode, result_signal) for trade in batch))
#                 break
#             except Exception as e:
#                 attempts += 1
#                 result_signal(f"Rate limit or error encountered. Retrying batch {i // batch_size + 1} (attempt {attempts}) in {backoff} seconds.")
#                 logging.error(f"Batch {i // batch_size + 1} error: {e}. Retrying in {backoff} seconds.")
#                 await asyncio.sleep(backoff)
#                 backoff *= 2  # Exponential backoff

# async def calculate_and_execute_arbitrage(exchange, triangular_pairs, min_trade_volume_threshold, sandbox_mode, result_signal):
#     """
#     Calculate arbitrage opportunities and execute them if profitable.
#     Args:
#         exchange: The exchange instance.
#         triangular_pairs: List of triangular trading pairs.
#         min_trade_volume_threshold: Minimum trade volume.
#         sandbox_mode: Boolean to determine if trades are real or simulated.
#         result_signal: Function to emit trade results.
#     """
#     try:
#         start_time = datetime.now()
#         profitable_trades = await calculate_arbitrage_profit(
#             exchange, triangular_pairs, min_trade_volume_threshold, result_signal
#         )
#         result_signal(f"Arbitrage calculation completed in {datetime.now() - start_time}")

#         if profitable_trades:
#             # Sort trades by profit in descending order
#             profitable_trades.sort(key=lambda x: x["profit"], reverse=True)
#             result_signal(f"Found {len(profitable_trades)} profitable opportunities.")

#             # Execute trades in batches
#             await execute_trades_in_batches(exchange, profitable_trades, sandbox_mode, result_signal)
#         else:
#             result_signal("No profitable opportunities found.")

#     except asyncio.CancelledError:
#         result_signal("Arbitrage calculation task was cancelled.")
#     except Exception as e:
#         result_signal(f"Error calculating arbitrage opportunities: {e}")
#         logging.error(f"Arbitrage calculation error: {e}")


# Main Function
if __name__ == "__main__":
    init_db()  # Ensure the database is set up
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
