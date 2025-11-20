import json
import time
import random
import logging
import requests

# Internal imports
from config import TIMEOUT_API

class Task:
    """Classe base para qualquer tipo de Task."""

    def __init__(self, host, user_id):
        self.host = host
        self.user_id = user_id

    def run_request(self, endpoint, payload, task_type, request_id):
        """Executa uma requisição curl e retorna os resultados formatados."""
        url = self.host + endpoint
        timestamp = int(time.time())

        try:
            start_time = time.perf_counter()

            response = requests.post(
                url=url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT_API
            )

            duration = round(time.perf_counter() - start_time, 5)
            status_code = response.status_code
            status = "success" if 200 <= status_code < 300 else "fail"

            try:
                transaction = response.json()
            except json.JSONDecodeError:
                transaction = {}

            logging.info(
                f"[User-{self.user_id:03d}]"
                f"  [Req-{request_id:03d}]"
                f"  {f'[{task_type}]':<12}"                
                f"  {endpoint:<34}"
                f"  {status_code}"
                f"  {duration:.3f}s"
                f"  {status}"
            )

            return {
                "timestamp": timestamp,
                "user_id": self.user_id,
                "request": request_id,
                "task": task_type,
                "endpoint": endpoint,
                "duration": duration,
                "status": status,
            }, transaction

        except requests.exceptions.Timeout:            
            logging.warning(f"[User-{self.user_id}] Timeout at {endpoint}")
            return {
                "timestamp": timestamp,
                "user_id": self.user_id,
                "endpoint": endpoint,
                "status_code": "timeout",
                "duration": -1,
                "result": "fail"
            }, None

        # except Exception as e:
        except requests.exceptions.RequestException as e:
            logging.error(f"[Task-User-{self.user_id}] {endpoint} exception: {e}")
            return {
                "timestamp": timestamp,
                "user_id": self.user_id,
                "endpoint": endpoint,
                "status_code": "error",
                "duration": -1,
                "result": f"fail ({e})"
            }, None

