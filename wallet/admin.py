import json
import time
import logging
import threading
from typing import Optional

from eth_account import Account
from web3 import Web3

# Internal imports
from config import PRIVATE_KEY, CONTRACT_ADDRESS, ABI_PATH
from wallet.config import get_w3
from log import SIZE

# --- Locks e singletons ---
_admin_account: Optional[Account] = None
_admin_init_lock = threading.Lock()
_admin_tx_lock = threading.Lock()


# ---------------------------
# Admin account initialization
# ---------------------------
def get_admin_account():
    global _admin_account
    with _admin_init_lock:
        if _admin_account is None:
            _admin_account = Account.from_key(PRIVATE_KEY)
            logging.info("Initializing admin account")
            logging.info("")
            logging.info(f"\t- Admin address: {_admin_account.address}")
            logging.info("")
        return _admin_account


def _get_chain_id():
    return get_w3().eth.chain_id


def _get_gas_price_wei(gwei: int) -> int:
    try:
        return get_w3().to_wei(gwei, "gwei")
    except Exception:
        return get_w3().eth.gas_price


def _get_nonce_rpc(address: str) -> int:
    """Sempre pegar nonce REAL do RPC (pending)."""
    return get_w3().eth.get_transaction_count(address, "pending")


# -------------------------------------
# Send transaction (unchanged)
# -------------------------------------
def send_transaction(
    signed_tx,
    user_id,
    admin_address,
    target,
    amount_eth,
    attempt,
    max_retries,
    wait_receipt=True
):
    try:
        w3 = get_w3()
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # logging.info(f"Transaction sent")
        # logging.info(f"\tHash    : {tx_hash.hex()}")
        # logging.info(f"\tUser    : {user_id:03d}")
        # logging.info(f"\tTo      : {target}")
        # logging.info(f"\tAmount  : {amount_eth} ETH")
        # logging.info(f"\tAttempt : {attempt}/{max_retries}")
        # logging.debug(
        #     f"{'Transaction sent':<21} "
        #     f"User-{user_id:03d} "
        #     f"Wallet: {target[:8]}... "
        #     f"{str(amount_eth)} ETH "
        #     f"Hash: {tx_hash.hex()[:8]}... "
        #     f"{attempt}/{max_retries}"
        # )

        if wait_receipt:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
            status = "success" if receipt.status == 1 else "failed"

            # logging.info(f"Transaction confirmed")
            # logging.info(f"\tHash    : {tx_hash.hex()}")
            # logging.info(f"\tUser    : {user_id:03d}")
            # logging.info(f"\tStatus  : {status.capitalize()}")
            logging.info(
                f"Send "
                f"User-{user_id:03d} " 
                f"Wallet: {target[:8]}... "
                f"{str(amount_eth)} ETH "
                f"Hash: {tx_hash.hex()[:8]}... "
                f"{attempt}/{max_retries} "
                f"{status.capitalize()}"
            )

            return tx_hash, receipt

        return tx_hash, None

    except Exception as e:
        logging.info(f"Transaction error: {e}")
        return None, None


# -------------------------------------
# FUND WALLET - FIXED VERSION
# -------------------------------------
def fund_wallet(
    user_id,
    target: str,
    amount_eth: float = 1.0,
    gas_price_gwei: int = 5,
    wait_receipt: bool = True,
    max_retries: int = 2
) -> bool:

    admin = get_admin_account()

    if not Web3.is_address(target):
        logging.info(f"Invalid target address: {target}")
        return False

    for attempt in range(1, max_retries + 1):

        try:
            with _admin_tx_lock:

                # nonce real
                nonce = _get_nonce_rpc(admin.address)

                gas_price = _get_gas_price_wei(gas_price_gwei)
                gas_limit = 21000
                w3 = get_w3()
                value_wei = w3.to_wei(amount_eth, "ether")

                # check balance before
                balance = w3.eth.get_balance(admin.address)
                total_cost = value_wei + gas_limit * gas_price

                if balance < total_cost:
                    logging.error(
                        f"Saldo insuficiente: balance={w3.from_wei(balance,'ether')} "
                        f"< required={w3.from_wei(total_cost,'ether')} ETH "
                        f"(user={user_id}, target={target})"
                    )
                    return False

                tx = {
                    "from": admin.address,
                    "to": Web3.to_checksum_address(target),
                    "value": value_wei,
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                    "nonce": nonce,
                    "chainId": _get_chain_id(),
                }

                signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)

                tx_hash, receipt = send_transaction(
                    signed_tx=signed_tx,
                    user_id=user_id,
                    admin_address=admin.address,
                    target=target,
                    amount_eth=amount_eth,
                    attempt=attempt,
                    max_retries=max_retries,
                    wait_receipt=wait_receipt
                )

            if receipt and receipt.status == 1:
                return True

        except Exception as e:
            logging.info(f"ETH transfer error: {e}")

        time.sleep(0.5 * attempt)

    logging.info(f"ETH transfer failed target: {target}")
    return False


# -------------------------------------
# FUND WALLETS BATCH - NEW
# -------------------------------------
def fund_wallets_batch(
    recipients: list,  # List of (user_id, address) tuples
    amount_eth: float = 1.0,
    gas_price_gwei: int = 5,
    max_retries: int = 2
) -> dict:
    """
    Fund multiple wallets in batch by sending all transactions asynchronously,
    then waiting for all receipts in parallel.
    
    Returns:
        dict: {user_id: success_bool}
    """
    admin = get_admin_account()
    results = {}
    
    if not recipients:
        return results
    
        
    logging.info("-" * SIZE)
    logging.info(f"Starting batch funding for {len(recipients)} users...")
    logging.info("")
    
    for attempt in range(1, max_retries + 1):
        pending_txs = []  # List of (user_id, tx_hash)
        
        try:
            with _admin_tx_lock:
                # Get starting nonce
                base_nonce = _get_nonce_rpc(admin.address)
                
                gas_price = _get_gas_price_wei(gas_price_gwei)
                gas_limit = 21000
                w3 = get_w3()
                value_wei = w3.to_wei(amount_eth, "ether")
                
                # Check admin balance
                balance = w3.eth.get_balance(admin.address)
                total_cost = len(recipients) * (value_wei + gas_limit * gas_price)
                
                if balance < total_cost:
                    logging.error(
                        f"Insufficient balance for batch: "
                        f"balance={w3.from_wei(balance,'ether')} < "
                        f"required={w3.from_wei(total_cost,'ether')} ETH"
                    )
                    return {user_id: False for user_id, _ in recipients}
                
                # Build and send all transactions
                for idx, (user_id, target) in enumerate(recipients):
                    if not Web3.is_address(target):
                        logging.warning(f"Invalid address for user {user_id}: {target}")
                        results[user_id] = False
                        continue
                    
                    tx = {
                        "from": admin.address,
                        "to": Web3.to_checksum_address(target),
                        "value": value_wei,
                        "gas": gas_limit,
                        "gasPrice": gas_price,
                        "nonce": base_nonce + idx,
                        "chainId": _get_chain_id(),
                    }
                    
                    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                    
                    try:
                        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                        pending_txs.append((user_id, tx_hash, target))
                        logging.info(
                            f"\t- Sent batch tx {idx+1}/{len(recipients)} "
                            f"User-{user_id:03d} {target[:8]}... "
                            f"Hash: {tx_hash.hex()[:8]}..."
                        )
                    except Exception as e:
                        logging.error(f"Failed to send tx for user {user_id}: {e}")
                        results[user_id] = False
            
            # Wait for all receipts in parallel
            logging.info("")
            logging.info(f"Waiting for {len(pending_txs)} transaction confirmations...")
            logging.info("")
            
            for user_id, tx_hash, target in pending_txs:
                try:
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
                    success = receipt.status == 1
                    results[user_id] = success
                    
                    status = "success" if success else "failed"

                    logging.info(
                        f"\t- Batch confirmed "
                        f"User-{user_id:03d} {target[:8]}... "
                        f"{amount_eth} ETH "
                        f"Hash: {tx_hash.hex()[:8]}... "
                        f"{status.capitalize()}"
                    )
                except Exception as e:
                    logging.error(f"Failed to get receipt for user {user_id}: {e}")
                    results[user_id] = False
            
            # Check if all succeeded
            if all(results.get(uid, False) for uid, _ in recipients if uid in results):
                logging.info("")
                logging.info(f"Batch funding completed successfully!")
                logging.info("")
                return results
            
        except Exception as e:
            logging.error(f"Batch funding error (attempt {attempt}/{max_retries}): {e}")
        
        if attempt < max_retries:
            time.sleep(1.0 * attempt)
    
    # Mark any remaining users as failed
    for user_id, _ in recipients:
        if user_id not in results:
            results[user_id] = False
    
    logging.warning(f"Batch funding completed with some failures")
    return results



# -------------------------------------
# Contract loading
# -------------------------------------
def get_contract(contract_address: str, abi):
    return get_w3().eth.contract(address=contract_address, abi=abi)


def load_contract():
    try:
        with open(CONTRACT_ADDRESS) as f:
            address_data = json.load(f)
            contract_address = address_data["contractAddress"]

        with open(ABI_PATH) as f:
            artifact = json.load(f)
            abi = artifact["abi"]

        return get_contract(contract_address, abi)
    except Exception as e:
        raise RuntimeError(f"Erro ao carregar contrato: {e}")


# -------------------------------------
# Authorize wallet (also fixed)
# -------------------------------------
def authorize_wallet(contract, wallet_address):
    try:
        gas_price = _get_gas_price_wei(5)
        admin_account = get_admin_account()

        with _admin_tx_lock:
            nonce = _get_nonce_rpc(admin_account.address)
            w3 = get_w3()
            
            tx = contract.functions.setAllowedAddress(wallet_address, True).build_transaction({
                "from": admin_account.address,
                "value": 0,
                "gas": 300000,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": _get_chain_id()
            })

            signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

            tx_hash, receipt = send_transaction(
                signed_tx,
                user_id=0,
                admin_address=admin_account.address,
                target=wallet_address,
                amount_eth=0,
                attempt=1,
                max_retries=1,
                wait_receipt=True
            )

        print(f"{wallet_address} autorizada ({tx_hash.hex()})")

    except Exception as e:
        print(f"Erro ao autorizar {wallet_address}: {e}")
