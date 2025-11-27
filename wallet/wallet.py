import time
import logging
import threading
from typing import Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.exceptions import Web3RPCError

# Internal imports
from wallet.config import w3

# _nonce_cache_lock = threading.Lock()
# _nonce_cache: Optional[int] = None

def _get_chain_id():
    return w3.eth.chain_id


def _get_gas_price_wei(gwei: str = "5") -> int:
    try:
        return w3.to_wei(gwei, "gwei")
    except Exception:
        return w3.eth.gas_price


# def _get_next_nonce_from_rpc(address: str) -> int:
#     return w3.eth.get_transaction_count(address, "pending")


# def _reserve_nonce(address: str) -> int:
#     """Reserve a local nonce to avoid race conditions between threads."""
#     global _nonce_cache
#     with _nonce_cache_lock:
#         if _nonce_cache is None:
#             _nonce_cache = _get_next_nonce_from_rpc(address)
#         nonce = _nonce_cache
#         _nonce_cache += 1
#     return nonce

# _nonce_cache_lock = threading.Lock()
# _nonce_cache: dict[str, int] = {}  # nonce por endereço



_NONCE_LOCKS: dict[str, threading.Lock] = {}

def get_next_nonce(wallet_address):
    """Thread-safe nonce getter (per wallet address)."""
    lock = _NONCE_LOCKS.setdefault(wallet_address, threading.Lock())
    with lock:
        nonce = w3.eth.get_transaction_count(wallet_address, "pending")
        logging.debug(f"[wallet:{wallet_address}] Current nonce: {nonce}")
        return nonce

class Wallet:
    """Represents an Ethereum wallet associated with a user."""

    def __init__(self, user_id, private_key: str | None = None):
        """
        Creates a new wallet.
        If no private key is provided, a new local account is generated.
        """
        self.user_id = user_id
        self.account: LocalAccount = (
            Account.create() if private_key is None else Account.from_key(private_key)
        )
        self.address = self.account.address

        self._nonce_lock = threading.Lock()
        self._next_nonce: Optional[int] = None


    def get_balance(self) -> float:
        """Return the wallet balance in ETH."""
        try:
            balance_wei = w3.eth.get_balance(self.address)
            balance_eth = w3.from_wei(balance_wei, "ether")
            
            logging.debug(
                f"[User-{self.user_id:03d}]"
                f" [wallet:{self.address}]"
                f" Balance retrieved: {balance_eth} ETH"
            )
            return balance_eth
        except Exception as e:
            logging.error(
                f"[User-{self.user_id:03d}]"
                f" [wallet:{self.address}]"
                f" Failed to get balance: {e}"
            )
            return 0.0
        
    def sign_transaction(self, tx: dict):
        """Sign a transaction."""
        try:
            signed_tx = self.account.sign_transaction(tx)
            logging.debug(f"[User-{self.user_id:03d}] [wallet:{self.address}] Transaction signed successfully")
            return signed_tx
        except Exception as e:
            logging.error(f"[User-{self.user_id:03d}] [wallet:{self.address}] Failed to sign transaction: {e}")
            return None


    def send_transaction(self, signed_tx, request_id, wait_receipt: bool = True):
        """Send a signed transaction to the network"""
        for attempt in range(3):
            try:
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                # logging.info(
                #     f"[User-{self.user_id:03d}]"
                #     f" [Req-{request_id:03d}]"
                #     f" [wallet:{self.address}]"
                #     f" Transaction sent: {tx_hash.hex()}"
                # )

                if wait_receipt:
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    status_str = "Success" if receipt.status == 1 else "Failed"
                    # logging.info(f"[User-{self.user_id:03d}] [Req-{request_id:03d}] [wallet:{self.address}] Receipt status: {status_str}")
                    # logging.info(
                    #     f"[User-{self.user_id:03d}]"
                    #     f" [Req-{request_id:03d}]"
                    #     # f"  [wallet:{self.address}]"
                    #     f"  Receipt status: {status_str}"
                    # )
                    


                    if receipt.status == 0:
                        tx = w3.eth.get_transaction(tx_hash)
                        try:
                            w3.eth.call({
                                "to": tx["to"],
                                "from": tx["from"],
                                "data": tx["input"],
                                "value": tx["value"],
                            }, receipt.blockNumber - 1)
                        except Exception as e:
                            logging.error(
                                f"[User-{self.user_id:03d}]" 
                                f"  [Req-{request_id:03d}]"
                                f"  [wallet:{self.address}]"
                                f"  Revert reason: {e}"
                            )
                    
                    
                    return tx_hash, receipt

                return tx_hash, None

            except Exception as e:
                logging.warning(
                    f"[User-{self.user_id:03d}]"
                    f" [Req-{request_id:03d}]" 
                    f" [wallet:{self.address}]"
                    f" Retry {attempt+1}/3 send failed: {e}"
                )

                time.sleep(1)

        logging.error(
            f"[User-{self.user_id:03d}]"
            f"  [Req-{request_id:03d}]"
            f"  [wallet:{self.address}]"
            f"  Transaction failed after retries"
        )
        return None, None


    def build_transaction(self, tx_obj: dict) -> dict:
        """Build a transaction ready for signing (safe version)."""
        try:
            gas_price_gwei = "50"

            # Get proper nonce and gas price (ensure they're integers)
            # nonce = int(_reserve_nonce(self.address))

            nonce = get_next_nonce(self.address)
            gas_price = int(_get_gas_price_wei(gas_price_gwei))
            value_wei = int(w3.to_wei(0.0, "ether"))
            chain_id = int(_get_chain_id())

            tx = {
                "from": tx_obj["from"],
                "to": tx_obj["to"],
                "data": tx_obj.get("data", "0x"),
                "value": value_wei,
                "gas": 1_000_000,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": chain_id,
            }

            logging.debug(
                f"[User-{self.user_id:03d}] [wallet:{self.address}] Transaction built | nonce={nonce} | gasPrice={gas_price} | chainId={chain_id}"
            )
            return tx

        except Exception as e:
            logging.error(f"[User-{self.user_id:03d}] [wallet:{self.address}] Failed to build transaction: {e}")
            return None
