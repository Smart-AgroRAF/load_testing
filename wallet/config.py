import os
import threading
from web3 import Web3

from config import BESU_RPC_URL

_w3 = None
_async_w3 = None
_w3_lock = threading.Lock()
_async_w3_lock = threading.Lock()

def get_w3():
    """Returns the synchronous Web3 instance, initializing it if necessary."""
    global _w3
    with _w3_lock:
        if _w3 is None:
            try:
                _w3 = Web3(Web3.HTTPProvider(BESU_RPC_URL))
            except Exception as e:
                print(f"Erro ao inicializar o Web3: {e}")
                _w3 = None
    return _w3

def get_async_w3():
    """Returns the asynchronous Web3 instance, initializing it if necessary."""
    global _async_w3
    with _async_w3_lock:
        if _async_w3 is None:
            try:
                from web3 import AsyncWeb3, AsyncHTTPProvider
                _async_w3 = AsyncWeb3(AsyncHTTPProvider(BESU_RPC_URL))
            except Exception as e:
                print(f"Erro ao inicializar AsyncWeb3: {e}")
                _async_w3 = None
    return _async_w3

def check_connection():
    """Verifica se a conexão com o nó Ethereum foi bem-sucedida."""
    # Verifica w3 sync
    w3_instance = get_w3()
    if w3_instance is None:
         raise ConnectionError("Web3 object is None. Initialization failed.")
    
    if not w3_instance.is_connected():
        raise ConnectionError(f"Não foi possível conectar ao nó RPC em {BESU_RPC_URL}")

    # Verifica w3 async
    async_w3_instance = get_async_w3()
    if async_w3_instance is None:
         print("Warning: AsyncWeb3 object is None.") 

# Lock para garantir que o nonce seja acessado de forma thread-safe
NONCE_LOCK = threading.Lock()
