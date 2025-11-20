import os
from dotenv import load_dotenv

# Locust
# from eth_account import Account

load_dotenv()

# Locust test
RESULTS_DIR = "results"
MODES = ["api-only", "api-blockchain"]
HOST = "http://localhost:3000"
RUN_TIME = 10
USERS = 12
SPAWN_RATE = 2

# Wallets
# MNEMONIC = os.getenv("MNEMONIC")
# WALLETS_DIR = "wallets"
# os.makedirs(WALLETS_DIR, exist_ok=True)
# WALLETS_FILE = Path(f"{WALLETS_DIR}/wallets.json")
# Habilitar recursos HDWallet (usado em geração determinística)
# Account.enable_unaudited_hdwallet_features()

# Blockchain
RPC_URL = os.getenv("RPC_URL")
CHAINID = os.getenv("BESU_CHAINID")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Caminhos de artefatos e arquivos
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS_PATH", "../api/addresses/erc721-address.json")
ABI_PATH = os.getenv("ABI_PATH", "../api/artifacts/contracts/erc721.sol/TokenManager721.json")

ARGS_RUN_FILENAME = "args_run.json"
RESUME_RUN_FILENAME = "resume_run.json"
ARGS_FILENAME = "args.json"


TIMEOUT_BLOCKCHAIN = 240
TIMEOUT_API = 30

AMOUNT_ETH = 50