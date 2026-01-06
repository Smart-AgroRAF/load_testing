import time
import logging

class TaskBlockchain:
    """Handles the full lifecycle of processing, signing, and broadcasting blockchain transactions (Async)."""

    def __init__(self, wallet, user_id):
        self.wallet = wallet
        self.user_id = user_id

    
    def _format_result(self, request_id, task_type, endpoint, duration, status):
        """Normalize the result format."""
        return {
            "timestamp": int(time.time()),
            "user_id": self.user_id,
            "request": request_id,
            "task": task_type,
            "endpoint": endpoint, 
            "duration": duration,
            "status": status,
        }

    async def _tx_build(self, tx_obj, endpoint, request_id):
        """Builds the raw transaction (Async)."""

        start_time = time.perf_counter()
        
        # Await wallet build
        tx = await self.wallet.build_transaction(tx_obj)
        
        duration = time.perf_counter() - start_time

        logging.debug(
            f"[User-{self.user_id:03d}]"
            f" {f'[REQ-BLOCK-{request_id:03d}]':<15}"
            f" {f'[TX-BUILD]':<15}"
            f" {endpoint:<31}"
            f" {duration:<1.3f}s"
        )

        if not tx:
            logging.error(f"[User-{self.user_id:03d}] Empty transaction.")
            raise Exception("Failed to build transaction")

        result = self._format_result(
            request_id=request_id,
            task_type="TX-BUILD",
            endpoint=endpoint,
            duration=duration,
            status=""
        )

        return result, tx

    def _tx_sign(self, tx, endpoint, request_id):
        """Signs the built transaction (Sync wrapper)."""
        # Signing is CPU bound and handled by local account, no await needed mostly
        start_time = time.perf_counter()
        signed_tx = self.wallet.sign_transaction(tx)
        duration = (time.perf_counter() - start_time)
        
        logging.debug(
            f"[User-{self.user_id:03d}]"
            f" {f'[REQ-BLOCK-{request_id:03d}]':<15}"
            f" {f'[TX-SIGN]':<15}"
            f" {endpoint:<31}"
            f" {duration:<1.3f}s"
        )

        if not signed_tx:
            logging.error(f"[User-{self.user_id:03d}] Failed to sign transaction.")
            raise Exception("Failed to sign transaction")

        result = self._format_result(
            request_id=request_id,
            task_type="TX-SIGN", 
            endpoint=endpoint, 
            duration=duration, 
            status=""
        )

        return result, signed_tx

    async def _tx_send(self, signed_tx, endpoint, request_id):
        """Broadcasts the signed Ethereum transaction (Async)."""

        start_time = time.perf_counter()
        
        # Await wallet send
        tx_hash, receipt = await self.wallet.send_transaction(signed_tx, request_id)
        
        duration = time.perf_counter() - start_time

        status = "success" if receipt and receipt.status == 1 else "fail"

        logging.debug(
            f"[User-{self.user_id:03d}]"
            f" [REQ-BLOCK-{request_id:03d}]"
            f" {f'[TX-SEND]':<15}"
            f" {endpoint:<31}"
            f" {duration:<1.3f}s"
        )
        
        if not receipt:
            logging.error(f"[User-{self.user_id:03d}] No receipt returned.")
            raise Exception("Failed to get receipt")

        result = self._format_result(
            request_id=request_id,
            task_type="TX-SEND",
            endpoint=endpoint,
            duration=duration,
            status=""
        )

        return result, tx_hash, status

    
    async def execute(self, tx_obj, endpoint, request_id):
        """Executes the full blockchain pipeline (Async)."""

        results = []

        start_time = time.perf_counter()

        # Build
        result_tx_build, tx = await self._tx_build(tx_obj=tx_obj, endpoint=endpoint, request_id=request_id)
        results.append(result_tx_build)

        # Sign
        result_tx_sign, signed_tx = self._tx_sign(tx=tx, endpoint=endpoint, request_id=request_id)
        results.append(result_tx_sign)

        # Send
        result_tx_send, tx_hash, status = await self._tx_send(signed_tx, endpoint, request_id)
        results.append(result_tx_send)
        
        # TX-BLOCKCHAIN Total
        duration = (time.perf_counter() - start_time)
        
        logging.debug(
            f"[User-{self.user_id:03d}]"
            f" {f'[REQ-BLOCK-{request_id:03d}]':<15}"
            f" {f'[TX-BLOCK]':<15}"
            f" {endpoint:<31}"
            f" {duration:<1.3f}s"
            f" {status}"
        )

        results.append(self._format_result(
            request_id=request_id,
            task_type="TX-BLOCK",
            endpoint=endpoint,
            duration=duration,
            status=status
        ))

        return results, tx_hash.hex(), status
