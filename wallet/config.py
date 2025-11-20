import os
import threading
from dotenv import load_dotenv
from web3 import Web3

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# URL do nó RPC (ex: Infura, Alchemy, ou um nó local)
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")

# Inicializa a conexão com o nó Ethereum
try:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    # Verifica se a conexão foi bem-sucedida
    if not w3.is_connected():
        raise ConnectionError(f"Não foi possível conectar ao nó RPC em {RPC_URL}")
except Exception as e:
    print(f"Erro ao inicializar o Web3: {e}")
    # Em caso de falha, você pode querer ter um fallback ou simplesmente sair
    w3 = None

# Lock para garantir que o nonce seja acessado de forma thread-safe
NONCE_LOCK = threading.Lock()
