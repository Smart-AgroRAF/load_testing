import time
import logging

class TaskBlockchain:
    """Processa a transação retornada pela API e envia na blockchain."""

    def __init__(self, wallet, user_id):
        self.wallet = wallet
        self.user_id = user_id

    
    def _format_result(self, request_id, task_type, endpoint, duration, status):
        """Retorna o mesmo formato da classe Task."""
        return {
            "timestamp": int(time.time()),
            "user_id": self.user_id,
            "request": request_id,
            "task": task_type,
            "endpoint": endpoint, 
            "duration": duration,
            "status": status,
        }


    def execute(self, tx_obj, endpoint, request_id):
        """Constrói, assina e envia a transação."""

        results = []

        # Build transaction (calculate - gas, gasPrice, nonce and chainId) 
        start_time_build = time.perf_counter()
        tx = self.wallet.build_transaction(tx_obj)
        # total_time_tx_build = self.fire_metrics(endpoint, "TX_BUILD", start_time_build, tx)
        total_time_build = (time.perf_counter() - start_time_build)
        logging.info(
            f"[User-{self.user_id:03d}]"
            f"  [Req-{request_id:03d}]"
            f"  [TX-BUILD]"
            f"  {total_time_build:.3f}s"
        )
        if not tx:
            logging.warning(f"[User-{user_id:03d}] [Req-{request_id:03d}] [TX-BUILD] Empty transaction.")
            raise Exception("Failed to build transaction")


        results.append(self._format_result(
            request_id=request_id,
            task_type="TX-BUILD", 
            endpoint=endpoint, 
            duration=total_time_build, 
            status="success"
        ))


        # Sign transaction
        start_time_sign = time.perf_counter()
        signed_tx = self.wallet.sign_transaction(tx)
        total_time_sign = (time.perf_counter() - start_time_sign)
        # logging.info(f"[User-{self.user_id:03d}][TX-SIGN] Transaction signed in {total_time_tx_sign:.2f} ms")
        logging.info(
            f"[User-{self.user_id:03d}]"
            f"  [Req-{request_id:03d}]"
            f"  [TX-SIGN]"
            f"  {total_time_sign:.3f}s"
        )
        if not signed_tx:
            logging.error(f"[User-{user_id:03d}] [Req-{request_id:03d}] [TX_SEND] Failed to sign transaction.")
            raise Exception("Failed to sign transaction")


        results.append(self._format_result(
            request_id=request_id,
            task_type="TX-SIGN", 
            endpoint=endpoint, 
            duration=total_time_sign, 
            status="success"
        ))


        # Send transaction
        start_time_send = time.perf_counter()
        tx_hash, receipt = self.wallet.send_transaction(signed_tx, request_id)
        total_time_send = (time.perf_counter() - start_time_send)
        logging.info(
            f"[User-{self.user_id:03d}]"
            f"  [Req-{request_id:03d}]"
            f"  [TX-SEND]"
            f"  {total_time_send:.3f}s"
        )
        if not receipt:
            logging.error(
                f"[User-{self.user_id:03d}]"
                f"  [Req-{request_id:03d}]" 
                f"  [TX_SEND] No receipt returned."
            )
            raise Exception("Failed to get receipt")

        status = "success" if receipt.status == 1 else "fail"
        

        logging.info(
            f"[User-{self.user_id:03d}]"
            f"  [Req-{request_id:03d}]"
            f"  [TX_SEND]" 
            f"  {status}"
            f"  {tx_hash.hex()}"
        )

        results.append(self._format_result(
            request_id=request_id,
            task_type="TX-SEND", 
            endpoint=endpoint, 
            duration=total_time_send, 
            status=status
        ))

        return results, tx_hash.hex(), receipt.status
