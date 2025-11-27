import time
import logging

class TaskBlockchain:
    """Handles the full lifecycle of processing, signing, and broadcasting blockchain transactions."""

    def __init__(self, wallet, user_id):
        self.wallet = wallet
        self.user_id = user_id

    
    def _format_result(self, request_id, task_type, endpoint, duration, status):
        """
        Normalize the result format.

        Args:
            request_id (int): Sequential request number for the user.
            task_type (str): Stage name (TX-BUILD, TX-SIGN, TX-SEND, TX-BLOCK).
            endpoint (str): HTTP endpoint associated with this transaction.
            duration (float): Duration of the step in seconds.
            status (str): "success", "fail" or "" when not applicable.

        Returns:
            dict: Structured result entry.
        """

        return {
            "timestamp": int(time.time()),
            "user_id": self.user_id,
            "request": request_id,
            "task": task_type,
            "endpoint": endpoint, 
            "duration": duration,
            "status": status,
        }

    def _tx_build(self, tx_obj, endpoint, request_id):
        """
        Builds the raw transaction by computing gas, gasPrice, nonce, and chainId.

        Args:
            tx_obj (dict): Transaction fields returned by API-BUILD.
            endpoint (str): API endpoint that produced this transaction.
            request_id (int): Sequential request ID for logging.

        Returns:
            tuple: (result_entry, built_transaction)

        Raises:
            Exception: If the transaction could not be constructed.
        """

        start_time = time.perf_counter()
        tx = self.wallet.build_transaction(tx_obj)
        duration = time.perf_counter() - start_time

        logging.info(
            f"[User-{self.user_id:03d}]"
            # f" [REQ-BLOCK-{request_id:03d}]"
            f" {f'[REQ-BLOCK-{request_id:03d}]':<15}"
            f" {f'[TX-BUILD]':<15}"
            f" {endpoint:<31}"
            f" {duration:<1.3f}s"
        )

        if not tx:
            logging.error(
                f"[User-{self.user_id:03d}]"
                # f" [REQ-BLOCK-{request_id:03d}]"
                f" {f'[REQ-BLOCK-{request_id:03d}]':<15}"
                f" {f'[TX-BUILD]':<15}"
                f"Empty transaction."
            )
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
        """
        Signs the built transaction using the user's wallet.

        Args:
            tx (dict): Built Ethereum transaction fields.
            endpoint (str): API endpoint associated with this call.
            request_id (int): Sequential request ID.

        Returns:
            tuple: (result_entry, signed_transaction)

        Raises:
            Exception: If signing fails.
        """

        start_time = time.perf_counter()
        signed_tx = self.wallet.sign_transaction(tx)
        duration = (time.perf_counter() - start_time)
        logging.info(
            f"[User-{self.user_id:03d}]"
            # f" [REQ-BLOCK-{request_id:03d}]"
            f" {f'[REQ-BLOCK-{request_id:03d}]':<15}"
            f" {f'[TX-SIGN]':<15}"
            f" {endpoint:<31}"
            f" {duration:<1.3f}s"
        )

        if not signed_tx:
            logging.error(
                f"[User-{user_id:03d}]"
                # f" [REQ-BLOCK-{request_id:03d}]"
                f" {f'[REQ-BLOCK-{request_id:03d}]':<15}"
                f" {f'[TX-SIGN]':<15}"
                "Failed to sign transaction."
                )
            raise Exception("Failed to sign transaction")

        result = self._format_result(
            request_id=request_id,
            task_type="TX-SIGN", 
            endpoint=endpoint, 
            duration=duration, 
            status=""
        )

        return result, signed_tx

    def _tx_send(self, signed_tx, endpoint, request_id):
        """
        Broadcasts the signed Ethereum transaction to the network.

        Args:
            signed_tx (bytes): Signed raw transaction.
            endpoint (str): API endpoint that originated this call.
            request_id (int): Sequential request ID.

        Returns:
            tuple: (result_entry, tx_hash, tx_status_str)

        Raises:
            Exception: If no receipt is returned.
        """

        start_time = time.perf_counter()
        tx_hash, receipt = self.wallet.send_transaction(signed_tx, request_id)
        duration = time.perf_counter() - start_time

        status = "success" if receipt and receipt.status == 1 else "fail"

        logging.info(
            f"[User-{self.user_id:03d}]"
            f" [REQ-BLOCK-{request_id:03d}]"
            f" {f'[TX-SEND]':<15}"
            f" {endpoint:<31}"
            f" {duration:<1.3f}s"
        )
        
        if not receipt:
            logging.error(
                f"[User-{self.user_id:03d}]"
                # f" [REQ-BLOCK-{request_id:03d}]"
                f" {f'[REQ-BLOCK-{request_id:03d}]':<15}"
                f" {f'[TX-SEND]':<15}"
                f" No receipt returned."
            )
            raise Exception("Failed to get receipt")

        result = self._format_result(
            request_id=request_id,
            task_type="TX-SEND",
            endpoint=endpoint,
            duration=duration,
            status=""
        )

        return result, tx_hash, status

    
    def execute(self, tx_obj, endpoint, request_id):
        """
        Executes the full blockchain pipeline for one transaction:

            TX-BLOCK = TX-BUILD + TX-SIGN + TX-SEND

        Args:
            tx_obj (dict): Transaction data returned by the API.
            endpoint (str): API endpoint associated with this request.
            request_id (int): Internal sequential request number.

        Returns:
            tuple:
                - list[dict]: List of per-stage result entries.
                - str: Hexadecimal transaction hash.
                - str: Final status ("success" / "fail").
        """

        results = []

        start_time = time.perf_counter()

        # Build transaction (calculate - gas, gasPrice, nonce and chainId)
        result_tx_build, tx = self._tx_build(tx_obj=tx_obj, endpoint=endpoint, request_id=request_id)
        results.append(result_tx_build)

        # Sign transaction
        result_tx_sign, signed_tx = self._tx_sign(tx=tx, endpoint=endpoint, request_id=request_id)
        results.append(result_tx_sign)

        # Send transaction
        result_tx_send, tx_hash, status = self._tx_send(signed_tx, endpoint, request_id)
        results.append(result_tx_send)
        
        
        # TX-BLOCKCHAIN
        duration = (time.perf_counter() - start_time)
        
        logging.info(
            f"[User-{self.user_id:03d}]"
            # f" [REQ-BLOCK-{request_id:03d}]"
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
