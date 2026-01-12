import os
from dotenv import load_dotenv

# Locust
# from eth_account import Account

load_dotenv()

# Locust test
RESULTS_DIR = "results"
MODES = ["api-only", "api-blockchain"]
# HOST = "http://localhost:3000"
# HOST = "http://31.97.30.104:4000"
HOST = os.getenv("API_URL", "http://localhost:3000")

TYPE = ["cartesian", "paired"]
CONTRACT = ["erc721", "erc1155", "both"]
RUN = ["static", "ramp-up", "both"]

DURATION = [10]
USERS = [10]
STEP_USERS = [1]
INTERVAL_USERS = [1]
INTERVAL_REQUEST = 1
REPEAT = 1

WARMUP_USERS = 10
WARMUP_DURATION = 10
WARMUP_STEP_USERS = 1
WARMUP_INTERVAL_USERS = 1
WARMUP_INTERVAL_REQUESTS = 1

# Wallets
# MNEMONIC = os.getenv("MNEMONIC")
# WALLETS_DIR = "wallets"
# os.makedirs(WALLETS_DIR, exist_ok=True)
# WALLETS_FILE = Path(f"{WALLETS_DIR}/wallets.json")
# Habilitar recursos HDWallet (usado em geração determinística)
# Account.enable_unaudited_hdwallet_features()

# Blockchain
BESU_RPC_URL = os.getenv("BESU_RPC_URL", "http://127.0.0.1:8545")
CHAINID = os.getenv("BESU_CHAINID")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Caminhos de artefatos e arquivos
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS_PATH", "../api/addresses/erc721-address.json")
ABI_PATH = os.getenv("ABI_PATH", "../api/artifacts/contracts/erc721.sol/TokenManager721.json")

ARGS_RUN_FILENAME = "args_run.json"
RESUME_RUN_FILENAME = "resume_run.json"
ARGS_FILENAME = "args.json"


TIMEOUT_BLOCKCHAIN = 240
TIMEOUT_API = 240

AMOUNT_ETH = 5