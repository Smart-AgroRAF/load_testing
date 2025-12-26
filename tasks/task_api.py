import json
import time
import logging
import aiohttp
import asyncio

# Internal imports
from config import TIMEOUT_API

class TaskAPI:
    """Classe base para qualquer tipo de Task."""

    def __init__(self, host, user_id):
        self.host = host
        self.user_id = user_id

    async def run_request(self, session: aiohttp.ClientSession, endpoint, payload, task_type, request_id):
        """Executa uma requisição assíncrona e retorna os resultados formatados."""
        url = self.host + endpoint
        timestamp = int(time.time())

        try:
            start_time = time.perf_counter()

            async with session.post(
                url=url,
                json=payload,
                headers={"Content-Type": "application/json"},
                # timeout=aiohttp.ClientTimeout(total=TIMEOUT_API)
                timeout=TIMEOUT_API
            ) as response:
            
                duration = round(time.perf_counter() - start_time, 5)
                status_code = response.status
                status = "success" if 200 <= status_code < 300 else "fail"

                try:
                    transaction = await response.json()
                except Exception:
                    transaction = {}

                log_msg = (
                    f"[User-{self.user_id:03d}]"
                    f" {f'[REQ-API-{request_id:03d}]':<15}"
                    f" {f'[{task_type}]':<15}"
                    f" {endpoint:<31}"
                    f" {duration:<1.3f}s"
                    f" {status}"
                )

                if task_type == "API-READ-ONLY":
                    log_msg += f" Body: {transaction}"

                logging.info(log_msg)

                return {
                    "timestamp": timestamp,
                    "user_id": self.user_id,
                    "request": request_id,
                    "task": task_type,
                    "endpoint": endpoint,
                    "duration": duration,
                    "status": status,
                }, transaction

        except asyncio.TimeoutError:            
            logging.warning(f"[User-{self.user_id}] Timeout at {endpoint}")
            return {
                "timestamp": timestamp,
                "user_id": self.user_id,
                "endpoint": endpoint,
                "status_code": "timeout",
                "duration": -1,
                "result": "fail"
            }, None

        except aiohttp.ClientError as e:
            logging.error(f"[Task-User-{self.user_id}] {endpoint} exception: {e}")
            return {
                "timestamp": timestamp,
                "user_id": self.user_id,
                "endpoint": endpoint,
                "status_code": "error",
                "duration": -1,
                "result": f"fail ({e})"
            }, None
