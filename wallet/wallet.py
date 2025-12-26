import time
import logging
import asyncio
from typing import Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount

# Internal imports
from wallet.config import async_w3

class Wallet:
    """Represents an Ethereum wallet associated with a user (Async)."""

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

    async def get_balance(self) -> float:
        """Return the wallet balance in ETH."""
        try:
            balance_wei = await async_w3.eth.get_balance(self.address)
            balance_eth = float(async_w3.from_wei(balance_wei, "ether"))
            
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
        """Sign a transaction (CPU bound, fast enough to keep sync)."""
        try:
            signed_tx = self.account.sign_transaction(tx)
            logging.debug(f"[User-{self.user_id:03d}] [wallet:{self.address}] Transaction signed successfully")
            return signed_tx
        except Exception as e:
            logging.error(f"[User-{self.user_id:03d}] [wallet:{self.address}] Failed to sign transaction: {e}")
            return None


    async def send_transaction(self, signed_tx, request_id, wait_receipt: bool = True):
        """Send a signed transaction to the network (Async)."""
        for attempt in range(3):
            try:
                # Send raw transaction
                tx_hash_bytes = await async_w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                tx_hash = tx_hash_bytes # hex() is called later usually

                if wait_receipt:
                    # Wait for receipt
                    receipt = await async_w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    status_str = "Success" if receipt.status == 1 else "Failed"
                    
                    if receipt.status == 0:
                        # Try to get revert reason (call trace)
                        try:
                            tx = await async_w3.eth.get_transaction(tx_hash)
                            await async_w3.eth.call({
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

                await asyncio.sleep(1)

        logging.error(
            f"[User-{self.user_id:03d}]"
            f"  [Req-{request_id:03d}]"
            f"  [wallet:{self.address}]"
            f"  Transaction failed after retries"
        )
        return None, None


    async def build_transaction(self, tx_obj: dict) -> dict:
        """Build a transaction ready for signing (Async)."""
        try:
            gas_price_gwei = "50"

            # Async calls
            nonce = await async_w3.eth.get_transaction_count(self.address)
            
            # Helper for gas price
            try:
                gas_price = await async_w3.eth.gas_price
                # Override if we want fixed
                # gas_price = int(async_w3.to_wei(gas_price_gwei, "gwei"))
            except:
                gas_price = await async_w3.eth.gas_price

            value_wei = int(async_w3.to_wei(0.0, "ether"))
            chain_id = await async_w3.eth.chain_id

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
