import asyncio
import ccxt.pro as ccxtpro
from typing import List, Dict, Tuple, Set
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class TriangularArbitragePathFinder:
    def __init__(
        self,
        exchange_id: str,
        starting_coin: str,
        starting_balance: float,
        whitelist: List[str],
        api_key: str = None,
        api_secret: str = None,
        additional_params: dict = None
    ):
        """
        Initialize the path finder with exchange credentials and parameters.
        
        :param exchange_id: CCXT exchange id (e.g., 'binance')
        :param starting_coin: The coin you want to start with (e.g., 'BTC')
        :param starting_balance: Your available balance for the first trade
        :param whitelist: List of coins that must appear in the path
        :param api_key: Exchange API key (optional, can be loaded from env)
        :param api_secret: Exchange API secret (optional, can be loaded from env)
        :param additional_params: Additional exchange parameters like password, etc.
        """
        self.exchange_id = exchange_id
        self.starting_coin = starting_coin.upper()
        self.starting_balance = starting_balance
        self.whitelist = set(coin.upper() for coin in whitelist)
        
        # Configure API credentials
        config = {
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # Focus on spot markets
            }
        }
        
        # Use provided credentials or fall back to environment variables
        self.api_key = api_key or os.getenv(f"{exchange_id.upper()}_API_KEY")
        self.api_secret = api_secret or os.getenv(f"{exchange_id.upper()}_API_SECRET")
        
        if self.api_key:
            config['apiKey'] = self.api_key
        if self.api_secret:
            config['secret'] = self.api_secret
        
        # Add any additional parameters
        if additional_params:
            config.update(additional_params)
        
        # Initialize the exchange
        self.exchange = getattr(ccxtpro, exchange_id)(config)
        self.markets = None
        self.symbols = None
        self.graph = None
    
    async def initialize(self):
        """Load markets and build the exchange graph"""
        try:
            print(f"Connecting to {self.exchange_id}...")
            await self.exchange.load_markets()
            self.markets = self.exchange.markets
            self.symbols = self.exchange.symbols
            print(f"Successfully connected to {self.exchange_id}")
            self._build_exchange_graph()
        except Exception as e:
            print(f"Failed to initialize exchange: {str(e)}")
            raise
    
    def _build_exchange_graph(self):
        """Build a graph representation of the exchange markets"""
        self.graph = {}
        
        for symbol in self.symbols:
            try:
                base, quote = symbol.split('/')
                
                # Skip markets that aren't active
                if not self.markets[symbol].get('active', True):
                    continue
                
                # Add edge from base to quote
                if base not in self.graph:
                    self.graph[base] = set()
                self.graph[base].add(quote)
                
                # Add edge from quote to base (for inverse trading pair)
                if quote not in self.graph:
                    self.graph[quote] = set()
                self.graph[quote].add(base)
            except:
                # Skip symbols that don't split into two parts
                continue
    
    def _contains_whitelisted_coin(self, path: List[str]) -> bool:
        """Check if path contains at least one whitelisted coin"""
        return any(coin in self.whitelist for coin in path)
    
    async def find_triangular_paths(self) -> List[List[str]]:
        """
        Find all possible triangular paths starting with the starting_coin
        that contain at least one whitelisted coin.
        
        :return: List of paths (each path is a list of 3-4 coins)
        """
        if not self.graph:
            raise RuntimeError("Exchange graph not initialized. Call initialize() first.")
        
        paths = []
        first_level = self.graph.get(self.starting_coin, set())
        
        for intermediate_coin in first_level:
            second_level = self.graph.get(intermediate_coin, set())
            
            for final_coin in second_level:
                if final_coin in self.graph and self.starting_coin in self.graph[final_coin]:
                    path = [self.starting_coin, intermediate_coin, final_coin, self.starting_coin]
                    if self._contains_whitelisted_coin(path):
                        paths.append(path)
        
        return paths
    
    async def check_path_liquidity(self, path: List[str]) -> Tuple[float, float]:
        """
        Check liquidity for a specific path and calculate potential profit
        
        :param path: The trading path to check
        :return: Tuple of (final_quantity, profit)
        """
        try:
            # A → B
            symbol1 = f"{path[0]}/{path[1]}"
            order_book1 = await self.exchange.watch_order_book(symbol1)
            bid_price1 = order_book1['bids'][0][0] if order_book1['bids'] else 0
            
            if bid_price1 == 0:
                return (0, 0)
            
            # B → C
            symbol2 = f"{path[1]}/{path[2]}"
            order_book2 = await self.exchange.watch_order_book(symbol2)
            bid_price2 = order_book2['bids'][0][0] if order_book2['bids'] else 0
            
            if bid_price2 == 0:
                return (0, 0)
            
            # C → A
            symbol3 = f"{path[2]}/{path[3]}"
            order_book3 = await self.exchange.watch_order_book(symbol3)
            bid_price3 = order_book3['bids'][0][0] if order_book3['bids'] else 0
            
            if bid_price3 == 0:
                return (0, 0)
            
            # Calculate quantities
            qty1 = self.starting_balance
            qty2 = qty1 * bid_price1
            qty3 = qty2 * bid_price2
            final_qty = qty3 * bid_price3
            profit = final_qty - self.starting_balance
            
            return (final_qty, profit)
            
        except Exception as e:
            print(f"Error checking liquidity for path {path}: {str(e)}")
            return (0, 0)
    
    async def filter_paths_by_liquidity(self, paths: List[List[str]]) -> List[Tuple[List[str], float, float]]:
        """
        Filter paths by checking if they have sufficient liquidity based on starting balance
        
        :param paths: List of potential paths
        :return: List of tuples (path, final_quantity, profit) with viable paths
        """
        viable_paths = []
        
        for path in paths:
            final_qty, profit = await self.check_path_liquidity(path)
            if profit > 0:
                viable_paths.append((path, final_qty, profit))
        
        # Sort by profit descending
        viable_paths.sort(key=lambda x: x[2], reverse=True)
        return viable_paths
    
    async def close(self):
        """Close the exchange connection"""
        await self.exchange.close()

async def main():
    # Example configuration - you can load these from environment variables
    config = {
        'exchange_id': 'binance',
        'starting_coin': 'BTC',
        'starting_balance': 0.01,  # 0.01 BTC
        'whitelist': ['ETH', 'BNB', 'SOL', 'ADA', 'DOT'],
        'api_key': os.getenv('BINANCE_API_KEY'),  # Load from .env file
        'api_secret': os.getenv('BINANCE_API_SECRET'),  # Load from .env file
        'additional_params': {
            # 'password': 'your_password_if_required',
            # 'uid': 'your_user_id_if_required',
        }
    }
    
    path_finder = TriangularArbitragePathFinder(**config)
    
    try:
        await path_finder.initialize()
        print(f"Loaded {len(path_finder.symbols)} markets from {path_finder.exchange_id}")
        print(f"Whitelisted coins: {', '.join(path_finder.whitelist)}")
        
        all_paths = await path_finder.find_triangular_paths()
        print(f"\nFound {len(all_paths)} potential triangular paths containing whitelisted coins")
        
        viable_paths = await path_finder.filter_paths_by_liquidity(all_paths)
        print(f"\nFound {len(viable_paths)} viable paths with sufficient liquidity:")
        
        for i, (path, final_qty, profit) in enumerate(viable_paths, 1):
            highlighted_path = [
                f"*{coin}*" if coin in path_finder.whitelist else coin 
                for coin in path
            ]
            print(f"\nPath {i}: {' → '.join(highlighted_path)}")
            print(f"Starting amount: {path_finder.starting_balance:.8f} {path_finder.starting_coin}")
            print(f"Final amount:    {final_qty:.8f} {path_finder.starting_coin}")
            print(f"Estimated profit: {profit:.8f} {path_finder.starting_coin} "
                  f"(+{profit/path_finder.starting_balance*100:.2f}%)")
    
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
    finally:
        await path_finder.close()

if __name__ == '__main__':
    asyncio.run(main())