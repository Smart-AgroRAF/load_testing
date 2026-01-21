import csv
import os
import json
import time
import random
import logging
import requests
import asyncio
import aiohttp
from typing import List, Dict, Type

# Internal imports
import log
from wallet.admin import fund_wallet, fund_wallets_batch
from users.user import User
from config import TIMEOUT_BLOCKCHAIN, AMOUNT_ETH
from wallet.config import get_w3, check_connection
from stats import Stats

class LoadTester:
    """Performs HTTP load tests simulating multiple users (Async core)."""

    def __init__(
        self, 
        host, 
        mode, 
        contract,
        duration,
        user_cls: Type[User],
        users,
        step_users=None,
        interval_users=None,
        interval_requests=None,
        
        # TCPConnector Configuration
        connector_limit: int = 100,
        connector_limit_per_host: int = 0,
        connector_keepalive_timeout: float = 15.0,
        connector_ttl_dns_cache: float = 10.0,
        connector_force_close: bool = False
    ):
        if not issubclass(user_cls, User):
            raise TypeError(f"{user_cls.__name__} must inherit from User")

        self.user_cls = user_cls
    
        # self.output_file = output_file
        self.host = host
        self.mode = mode
        self.contract = contract
        self.duration = duration

        self.interval_requests = interval_requests
        self.users = self._create_users(amount_users=users)
        self.number_users = len(self.users)
        self.step_users = step_users
        self.interval_users = interval_users

        # Connector Config
        self.connector_limit = connector_limit
        self.connector_limit_per_host = connector_limit_per_host
        self.connector_keepalive_timeout = connector_keepalive_timeout
        self.connector_ttl_dns_cache = connector_ttl_dns_cache
        self.connector_force_close = connector_force_close

        if self.mode == "api-blockchain":
            self._authorized_users()
            self._fund_users()

        self.results_tx_build: List[Dict] = []
        self.results_read_only: List[Dict] = []

    def _fund_users(self):
                
        # Collect all recipients for batch funding
        recipients = [(user.user_id, user.wallet.address) for user in self.users]
        
        # Use batch funding
        results = fund_wallets_batch(
            recipients=recipients,
            amount_eth=AMOUNT_ETH,
            gas_price_gwei=5,
            max_retries=3,
        )
        
        # Log any failures
        for user_id, success in results.items():
            if not success:
                logging.error(f"[User-{user_id:03d}] Failed to fund wallet")
        
        logging.info("Funded users:")
        logging.info("")

        # Wallet.get_balance is async now, but property address is sync.
        # We can skipping balance check here to avoid async complexity in Init
        # or use a sync call via w3 directly if needed. 
        # For now, listing addresses is enough.
        for user in self.users:
            try:
                w3 = get_w3()
                balance_wei = w3.eth.get_balance(user.wallet.address)
                balance_eth = w3.from_wei(balance_wei, "ether")
                logging.info(
                    f"\t- [User-{user.user_id:03d}] "
                    f"Wallet: {user.wallet.address[:8]}... "
                    f"Balance: {balance_eth:.4f} ETH"
                )
            except Exception as e:
                logging.error(
                    f"\t- User-{user.user_id:03d} "
                    f"Wallet: {user.wallet.address[:8]}... "
                    f"Balance: Error ({e})"
                )


    def _authorized_users(self):

        logging.info("-" * log.SIZE)
        logging.info(f"Starting authorizing {self.number_users} users for contract...")
        logging.info("")

        url = f"{self.host}/api/{self.contract}/admin/setAllowedAddressesBatch"

        addresses = [user.wallet.address for user in self.users]

        payload = {
            "addresses": addresses,
            "allow": True
        }
       
        logging.info(f"\t- URL : {url}")
        logging.info("")
        logging.info("\t- Users:")
        for user in self.users:
            logging.info(f"\t\t[User-{user.user_id:03d}] Wallet : {user.wallet.address}")

        logging.info("")
        logging.info("Sending request to authorize batch addresses...")

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT_BLOCKCHAIN
            )

            status_code = response.status_code
            result_status = "success" if 200 == status_code else "fail"

            logging.info("")
            if status_code != 200:
                logging.error(f"Authorization failed with status code {status_code}")
            else:
                logging.info("All users authorized successfully.")
            logging.info("")

        except requests.exceptions.Timeout:
            logging.error("Authorization request timed out ({timeout}s).")
        except requests.exceptions.RequestException as e:
            logging.error(f"Unexpected error during authorization: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")


        logging.info("Finish authorizing users for contract.")
        logging.info("")


    def _create_users(self, amount_users: int):
        """Init all users before start the test."""

        logging.info(f"Starting {amount_users} users...")
        logging.info("")

        users = []

        for user_id in range(1, amount_users + 1):
            users.append(self.user_cls(
                host=self.host,
                mode=self.mode,
                user_id=user_id,
                interval_requests=self.interval_requests
            ))

        logging.info("")
        logging.info(f"All {len(users)} users instantiated.")

        return users


    async def _run(self, user, user_id, duration, run_function, results_operation):
        """Runs a single type of flow (API or Blockchain) for 'duration' seconds (Async)."""
        
        logging.info(f"[User-{user_id:03d}] Starting run: {run_function.__name__}...")

        # Capture initial state
        start_api_count = user.api_requests_counter
        start_bc_count = user.blockchain_requests_counter
        start_api_success = user.api_success
        start_api_fail = user.api_fail
        start_bc_success = user.bc_success
        start_bc_fail = user.bc_fail
        start_time = time.perf_counter()

        while (time.perf_counter() - start_time) < duration:
            try:
                # Await the user function
                # Note: run_function (sequential or random) updates sequences/etc
                # If run_function is async, await it.
                if asyncio.iscoroutinefunction(run_function):
                    results = await run_function()
                else:
                    results = run_function() # Should ideally be async

                for result in results:
                    results_operation.append(result)

            except Exception as e:
                logging.error(f"[User-{user_id:03d}] Error during {run_function.__name__}: {type(e).__name__}: {e}")
                results_operation.append({
                    "timestamp": int(time.time()),
                    "user_id": user_id,
                    "request": "error",
                    "task": "error",
                    "endpoint": "unknown",
                    "duration": -1,
                    "status": f"fail ({type(e).__name__})"
                })
                # Small sleep to prevent tight loop in case of repeated immediate errors
                await asyncio.sleep(0.1)

        # Capture final state and calculate stats
        end_time = time.perf_counter()
        end_api_count = user.api_requests_counter
        end_bc_count = user.blockchain_requests_counter
        end_api_success = user.api_success
        end_api_fail = user.api_fail
        end_bc_success = user.bc_success
        end_bc_fail = user.bc_fail
        end_bc_success = user.bc_success
        end_bc_fail = user.bc_fail

        delta_api = end_api_count - start_api_count
        delta_bc = end_bc_count - start_bc_count
        
        # Calculate success/fail deltas
        delta_api_success = end_api_success - start_api_success
        delta_api_fail = end_api_fail - start_api_fail
        delta_bc_success = end_bc_success - start_bc_success
        delta_bc_fail = end_bc_fail - start_bc_fail

        total_requests = delta_api + delta_bc
        elapsed_time = end_time - start_time
        
        rps = total_requests / elapsed_time if elapsed_time > 0 else 0.0

        logging.info(f"[User-{user_id:03d}] Finished {run_function.__name__}")
        logging.info(f"\t- Duration       : {elapsed_time:.2f}s")
        logging.info(f"\t- API Reqs       : {delta_api} (Success: {delta_api_success} | Fail: {delta_api_fail})")
        logging.info(f"\t- BC Reqs        : {delta_bc} (Success: {delta_bc_success} | Fail: {delta_bc_fail})")
        logging.info(f"\t- Total          : {total_requests}")
        logging.info(f"\t- RPS            : {rps:.2f}")

        return {
            "api": delta_api,
            "bc": delta_bc,
            "total": total_requests,
            "api_success": delta_api_success,
            "api_fail": delta_api_fail,
            "bc_success": delta_bc_success,
            "bc_fail": delta_bc_fail
        }


    async def simulate_user(self, phase, user_id: int, duration: float, interval_requests: float):
        """Runs the user's sequence of Tasks for 'duration' seconds (Async)."""

        user = self.users[user_id - 1]
        
        # Initialize User Session
        connector = aiohttp.TCPConnector(
            limit=self.connector_limit, 
            limit_per_host=self.connector_limit_per_host,
            keepalive_timeout=self.connector_keepalive_timeout,
            ttl_dns_cache=self.connector_ttl_dns_cache,
            force_close=self.connector_force_close
        )
        user.session = aiohttp.ClientSession(connector=connector)

        try:
            counts = {
                "api": 0, "bc": 0, "total": 0, 
                "api_success": 0, "api_fail": 0, 
                "bc_success": 0, "bc_fail": 0
            }

            # 1. sequential API + Blockchain (API-TX_BUILD)
            if phase == "api-tx-build":
                counts = await self._run(user, user_id, duration, user.run_sequential_request, self.results_tx_build)

            # 2. random API (API-READ-ONLY)
            if phase == "api-read-only":
                counts = await self._run(user, user_id, duration, user.run_random_request, self.results_read_only)
                
            return counts
        
        finally:
            await user.session.close()
            

    def run_static_load(self, phase, output_file=None):

        """Runs a static load test (Async wrapper)."""
        
        logging.info("")
        logging.info(f"Starting static load test with {self.number_users} users for {self.duration}s...")
        logging.info("")
        
        async def main_async():
             start_time = time.perf_counter()
             tasks = [
                 self.simulate_user(phase=phase, user_id=user_id, duration=self.duration, interval_requests=self.interval_requests)                
                 for user_id in range(1, self.number_users + 1)
             ]
             results = await asyncio.gather(*tasks)
             total_time = round(time.perf_counter() - start_time, 2)
             return results, total_time

        # Execute async loop
        results_list, total_time = asyncio.run(main_async())


        global_api = 0
        global_bc = 0
        global_total = 0
        global_api_success = 0
        global_api_fail = 0
        global_bc_success = 0
        global_bc_fail = 0

        for res in results_list:
            if res:
                global_api += res["api"]
                global_bc += res["bc"]
                global_total += res["total"]
                global_api_success += res["api_success"]
                global_api_fail += res["api_fail"]
                global_bc_success += res["bc_success"]
                global_bc_fail += res["bc_fail"]

        
        global_rps = global_total / total_time if total_time > 0 else 0.0
        
        log.print_global_summary(
            "STATIC", self.number_users, total_time, 
            global_api, global_bc, global_total, global_rps,
            global_api_success, global_api_fail, global_bc_success, global_bc_fail
        )


        if phase == "api-tx-build":
            results = self.results_tx_build
        elif phase == "api-read-only":
            results = self.results_read_only
        else:
            results = []

        return {
            "users": self.number_users,
            "results": results,
            "output_file": output_file,
            "total_time": total_time,
            "global_stats": {
                "api": global_api,
                "bc": global_bc,
                "total": global_total,
                "rps": global_rps,
                "api_success": global_api_success,
                "api_fail": global_api_fail,
                "bc_success": global_bc_success,
                "bc_fail": global_bc_fail
            }
        }

    def run_ramp_up_load(self, phase, output_file=None):

        """Runs a ramp-up load test, adding users gradually (Async wrapper)."""
        
        logging.info("")
        logging.info(f"Starting ramp-up load test with up to {self.number_users} users...")
        logging.info("")
    
        
        async def main_ramp_up():
            start_time = time.perf_counter()
            tasks = []
            active_users = 0

            while active_users < self.number_users:
                # Add a new user group (step users)
                new_users = min(self.step_users, self.number_users - active_users)
                for i in range(new_users):
                    user_id = active_users + i + 1
                    # Start task
                    task = asyncio.create_task(
                        self.simulate_user(phase=phase, user_id=user_id, duration=self.duration, interval_requests=self.interval_requests)
                    )
                    tasks.append(task)

                active_users += new_users
                logging.info(f"Active users: {active_users}/{self.number_users}")

                # Wait for the time between increments
                if active_users < self.number_users:
                    await asyncio.sleep(self.interval_users)

            # Wait for all tasks to finish
            results = await asyncio.gather(*tasks)
            total_time = round(time.perf_counter() - start_time, 2)
            return results, total_time

        # Execute
        results_list, total_time = asyncio.run(main_ramp_up())


        global_api = 0
        global_bc = 0
        global_total = 0
        global_api_success = 0
        global_api_fail = 0
        global_bc_success = 0
        global_bc_fail = 0
        
        for res in results_list:
            if res:
                global_api += res["api"]
                global_bc += res["bc"]
                global_total += res["total"]
                global_api_success += res["api_success"]
                global_api_fail += res["api_fail"]
                global_bc_success += res["bc_success"]
                global_bc_fail += res["bc_fail"]


        global_rps = global_total / total_time if total_time > 0 else 0.0

        log.print_global_summary(
            "RAMP-UP", self.number_users, total_time, 
            global_api, global_bc, global_total, global_rps,
            global_api_success, global_api_fail, global_bc_success, global_bc_fail
        )
        

        if phase == "api-tx-build":
            results = self.results_tx_build
        elif phase == "api-read-only":
            results = self.results_read_only
        else:
            results = []

        return {
            "users": self.number_users,
            "results": results,
            "output_file": output_file,
            "total_time": total_time,
            "global_stats": {
                "api": global_api,
                "bc": global_bc,
                "total": global_total,
                "rps": global_rps,
                "api_success": global_api_success,
                "api_fail": global_api_fail,
                "bc_success": global_bc_success,
                "bc_fail": global_bc_fail
            }
        }
