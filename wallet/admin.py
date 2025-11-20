import json
import time
import logging
import threading
from typing import Optional

from pathlib import Path
from solcx import compile_standard, install_solc

from eth_account import Account
from web3 import Web3
from web3.exceptions import TransactionNotFound

# Internal imports
from config import PRIVATE_KEY, RPC_URL, CONTRACT_ADDRESS, ABI_PATH
from wallet.config import w3

# --- Locks e singletons ---
_admin_account: Optional[Account] = None
_admin_init_lock = threading.Lock()
_admin_tx_lock = threading.Lock()
_nonce_cache_lock = threading.Lock()
_nonce_cache: Optional[int] = None


#  Admin account initialization
def get_admin_account():
    global _admin_account
    with _admin_init_lock:
        if _admin_account is None:
            logging.info("[Admin] Initializing admin account...")
            _admin_account = Account.from_key(PRIVATE_KEY)
            logging.info(f"[Admin] Admin address: {_admin_account.address}")
        return _admin_account

def _get_chain_id():
    return w3.eth.chain_id


def _get_gas_price_wei(gwei: str = "5") -> int:
    try:
        return w3.to_wei(gwei, "gwei")
    except Exception:
        return w3.eth.gas_price


def _get_next_nonce_from_rpc(address: str) -> int:
    return w3.eth.get_transaction_count(address, "pending")


def _reserve_nonce(address: str) -> int:
    """Reserve a local nonce to avoid race conditions between threads."""
    global _nonce_cache
    with _nonce_cache_lock:
        if _nonce_cache is None:
            _nonce_cache = _get_next_nonce_from_rpc(address)
        nonce = _nonce_cache
        _nonce_cache += 1
    return nonce

def send_transaction(signed_tx, wait_receipt=True):
    """Send a signed transaction with detailed logging."""
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)        
        logging.info(f"[Admin] Transaction sent: {tx_hash.hex()}")

        if wait_receipt:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            status_str = "Success" if receipt.status == 1 else "Failed"

            logging.info(f"[Admin] Transaction received")
            logging.info(f"\tHash: {tx_hash.hex()}")
            logging.info(f"\tStatus: {status_str}")            

            return tx_hash, receipt

        return tx_hash, None

    except Exception as e:
        logging.info(f"[Admin] Transaction error: {e}")
        return None, None


#  ETH funding 
def fund_wallet(
    target: str,
    amount_eth: float = 1.0,
    gas_price_gwei: str = "5",
    wait_receipt: bool = True,
    max_retries: int = 2
) -> bool:
    """Send ETH from admin to `target`, thread-safe, with detailed logs."""
    admin = get_admin_account()
    if not Web3.is_address(target):    
        logging.info(f"[Admin] Invalid target address: {target}")
        return False

    for attempt in range(1, max_retries + 1):
        try:
            with _admin_tx_lock:
                nonce = _reserve_nonce(admin.address)
                gas_price = _get_gas_price_wei(gas_price_gwei)
                value_wei = w3.to_wei(amount_eth, "ether")

                tx = {
                    "from": admin.address,
                    "to": Web3.to_checksum_address(target),
                    "value": value_wei,
                    "gas": 21000,
                    "gasPrice": gas_price,
                    "nonce": nonce,
                    "chainId": _get_chain_id(),
                }

                logging.info(f"[Admin] Starting ETH transfer")
                logging.info(f"\tFrom: {admin.address}")
                logging.info(f"\tTo: {target}")
                logging.info(f"\tAmount: {amount_eth} ETH")
                logging.info(f"\tNonce: {nonce}")
                logging.info(f"\tGasPrice: {w3.from_wei(gas_price, 'gwei')} gwei")
                logging.info(f"\tAttempt: {attempt}/{max_retries}")
                

                signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                tx_hash, receipt = send_transaction(
                    signed_tx,
                    wait_receipt=wait_receipt,  # Always wait for confirmation by default                    
                )

            if receipt and receipt.status == 1:
                logging.info(f"[Admin] ETH transfer confirmed")                
                logging.info(f"\tFrom: {admin.address}")
                logging.info(f"\tTo: {target}")
                logging.info(f"\tHash: {tx_hash.hex()}")
                logging.info(f"\tAmount: {amount_eth} ETH")
                logging.info(f"\tBlock: {receipt.blockNumber}")
                
                return True

        except Exception as e:
            logging.info(f"[Admin] ETH transfer failed (attempt {attempt}/{max_retries}): {e}")

        time.sleep(0.5 * attempt)

    logging.info(f"[Admin] All attempts to fund {target} failed.")
    return False


def get_contract(contract_address: str, abi):
    """Obtém instância de contrato."""
    return w3.eth.contract(address=contract_address, abi=abi)

def load_contract():
    """Carrega o contrato e o ABI."""
    try:
        with open(CONTRACT_ADDRESS) as f:
            address_data = json.load(f)
            contract_address = address_data["contractAddress"]

        with open(ABI_PATH) as f:
            artifact = json.load(f)
            abi = artifact["abi"]

        contract = get_contract(contract_address=contract_address, abi=abi)
        return contract

    except Exception as e:
        raise RuntimeError(f"Erro ao carregar contrato: {e}")

def authorize_wallet(contract, wallet_address):
    """Autoriza uma carteira no contrato."""

    try:
        gas_price_gwei = "5"

        admin_account = get_admin_account()
        nonce = _reserve_nonce(admin_account.address)
        gas_price = _get_gas_price_wei(gas_price_gwei)
        value_wei = w3.to_wei(0.0, "ether")


        tx = contract.functions.setAllowedAddress(wallet_address, True).build_transaction({
            "from": admin_account.address,
            "value": value_wei,
            "gas": 300000,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": _get_chain_id()
        })

        # signed = sign_transaction(admin_account, tx)
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

        tx_hash, receipt = send_transaction(signed_tx)
        print(f"{wallet_address} autorizada ({tx_hash.hex()})")
    except Exception as e:
        print(f"Erro ao autorizar {wallet_address}: {e}")


# --- Utilitários ---
# def reset_nonce_cache():
#     global _nonce_cache
#     with _nonce_cache_lock:
#         _nonce_cache = None
#         logging.info("[Admin] Nonce cache reset.")




ABI_PATH = Path("./wallet/BatchTransferETH.abi.json")
BIN_PATH = Path("./wallet/BatchTransferETH.bin")
ADDR_PATH = Path("./wallet/deployed_batch_contract.json")

def load_contract_info():
    """Retorna ABI, BIN e endereço salvo (se existir)."""
    with open(ABI_PATH) as f:
        abi = json.load(f)

    with open(BIN_PATH) as f:
        bytecode = f.read().strip()

    address = None
    if ADDR_PATH.exists():
        with open(ADDR_PATH) as f:
            address = json.load(f).get("address")

    return abi, bytecode, address


def save_contract_address(address: str):
    with open(ADDR_PATH, "w") as f:
        json.dump({"address": address}, f, indent=4)
    print(f"[INFO] Contrato salvo em {ADDR_PATH}: {address}")


def get_or_deploy_contract(deployer_account):
    abi, bytecode, existing_address = load_contract_info()

    # SE O CONTRATO EXISTE: retorna
    if existing_address:
        print(f"[INFO] Contrato já implantado em {existing_address}, carregando.")
        return w3.eth.contract(address=existing_address, abi=abi)

    print("[INFO] Implantando contrato BatchTransferETH...")

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # --- BUILD TRANSACTION ---
    nonce = w3.eth.get_transaction_count(deployer_account.address, "pending")

    tx = contract.constructor().build_transaction({
        "from": deployer_account.address,
        "gas": 5_000_000,
        "gasPrice": w3.eth.gas_price,
        "nonce": nonce,
        "chainId": w3.eth.chain_id
    })

    # --- SIGN ---
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=deployer_account.key)

    # --- SEND RAW ---
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print(f"[INFO] Deploy enviado: {tx_hash.hex()}")

    # --- WAIT RECEIPT ---
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    contract_address = receipt.contractAddress
    # print("Contract balance:", w3.eth.get_balance(contract_address))

    contract_balance = w3.eth.get_balance(contract_address)
    logging.info(f"[DEBUG] Contract balance AFTER tx: {contract_balance}")
    save_contract_address(contract_address)

    print(f"[SUCCESS] Contrato implantado em: {contract_address}")

    return w3.eth.contract(address=contract_address, abi=abi)



# def fund_wallets_batch(recipients: list, value):
#     """Envia ETH para várias carteiras usando o contrato BatchTransferETH."""

    
#     admin = get_admin_account()

#     # deployer = w3.eth.account.from_key(deployer_priv_key)
#     # w3.eth.default_account = deployer.address

#     # 1️⃣ Garante que o contrato existe antes (deploy ou load)
#     contract = get_or_deploy_contract(admin)

#     # 2️⃣ Calcula total enviado
#     # total_value = sum(amounts)

#     amount = w3.to_wei(value, "ether")

#     # 3️⃣ Chama o batchSendETH
#     tx = contract.functions.batchSendETH(recipients, amount).build_transaction({
#         "from": admin.address,
#         "value": amount * len(recipients),
#         "nonce": w3.eth.get_transaction_count(admin.address),
#         "gas": 500000,
#         "gasPrice": w3.eth.gas_price
#     })

#     signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
#     tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

#     receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
#     print(f"[SUCCESS] Batch enviado. Hash: {receipt.transactionHash.hex()}")

#     return receipt


def fund_wallets_batch(recipients: list, amount_eth: float):
    """
    Envia o mesmo valor ETH para todos os endereços usando o contrato.
    """
    admin = get_admin_account()
    contract = get_or_deploy_contract(admin)

    # logging.info("Admin balance:", w3.eth.get_balance(admin.address))


    amount = w3.to_wei(amount_eth, "ether")

    # CRIA ARRAY DE AMOUNT PARA CADA RECEBEDOR
    amounts = [amount] * len(recipients)

    nonce = _reserve_nonce(admin.address)

    tx = contract.functions.batchSendETH(
        recipients,
        amounts            # <-- AGORA SIM: uint256[]
    ).build_transaction({
        "from": admin.address,
        "value": amount * len(recipients),
        "gas": 500000,
        "gasPrice": w3.eth.gas_price,
        "nonce": nonce,
        "chainId": w3.eth.chain_id
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash, receipt = send_transaction(signed)

    if receipt and receipt.status == 1:
        logging.info(f"[SUCCESS] Batch funding sent! {tx_hash.hex()}")

    return receipt




def compile_contract():
    CONTRACT_PATH = Path("./wallet/BatchTransferETH.sol")

    with open(CONTRACT_PATH, "r") as f:
        source = f.read()

    install_solc("0.8.20")

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {"BatchTransferETH.sol": {"content": source}},
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "evm.bytecode.object"]}
                }
            },
        },
        solc_version="0.8.20",
    )

    abi = compiled["contracts"]["BatchTransferETH.sol"]["BatchTransferETH"]["abi"]
    bytecode = compiled["contracts"]["BatchTransferETH.sol"]["BatchTransferETH"]["evm"]["bytecode"]["object"]

    # ⬇️ SALVA DO JEITO CORRETO
    ABI_PATH.write_text(json.dumps(abi, indent=4))
    BIN_PATH.write_text(bytecode)

    print(f"[INFO] ABI salva em {ABI_PATH}")
    print(f"[INFO] Bytecode salvo em {BIN_PATH}")

    return abi, bytecode

