import os
import threading
from web3 import Web3

from config import BESU_RPC_URL

# Inicializa a conexão com o nó Ethereum
try:
    w3 = Web3(Web3.HTTPProvider(BESU_RPC_URL))
    # Verifica se a conexão foi bem-sucedida
    if not w3.is_connected():
        raise ConnectionError(f"Não foi possível conectar ao nó RPC em {BESU_RPC_URL}")
except Exception as e:
    print(f"Erro ao inicializar o Web3: {e}")
    # Em caso de falha, você pode querer ter um fallback ou simplesmente sair
    w3 = None

# Lock para garantir que o nonce seja acessado de forma thread-safe
# Lock para garantir que o nonce seja acessado de forma thread-safe
NONCE_LOCK = threading.Lock()

# Async Web3 Provider
try:
    from web3 import AsyncWeb3, AsyncHTTPProvider
    async_w3 = AsyncWeb3(AsyncHTTPProvider(BESU_RPC_URL))
except Exception as e:
    print(f"Erro ao inicializar AsyncWeb3: {e}")
    async_w3 = None
