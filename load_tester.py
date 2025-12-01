import csv
import json
import time
import random
import logging
import requests
import concurrent.futures
from typing import List, Dict, Type

# Internal imports
import log
from wallet.admin import fund_wallet
from users.user import User
from config import TIMEOUT_BLOCKCHAIN, AMOUNT_ETH
from wallet.config import w3

class LoadTester:
    """Performs HTTP load tests simulating multiple users."""

    def __init__(
        self, 
        # output_file,
        host, 
        mode, 
        contract,
        duration,
        user_cls: Type[User],
        users,
        step_users=None,
        interval_users=None,
        interval_requests=None,
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

        if self.mode == "api-blockchain":
            self._authorized_users()
            self._fund_users()

        self.results_tx_build: List[Dict] = []
        self.results_read_only: List[Dict] = []

    def _fund_users(self):
        
        logging.info("-" * log.SIZE)
        logging.info("Starting fund users...")
        logging.info("")
        
        for user in self.users:
            try:
                fund_wallet(
                    user_id=user.user_id,
                    target=user.wallet.address,
                    amount_eth=AMOUNT_ETH,
                    gas_price_gwei=5,
                    wait_receipt=True,
                    max_retries=3,
                )
            except Exception as e:
                logging.error(f"[User-{user.user_id:03d}] Failed to fund wallet {user.wallet.address}: {e}")
        

        logging.info("Funded users")

        for user in self.users:
            balance = user.wallet.get_balance()
            logging.info(f"\t[User-{user.user_id:03d}] Wallet {user.wallet.address} balance: {balance} ETH")

        logging.info("Finish fund users.")

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
       
        logging.info(f"\tURL           : {url}")
        logging.info(f"\tUsers allowed : {len(addresses)}")
        logging.info("")
        for user in self.users:
            logging.info(f"\t[User-{user.user_id:03d}] wallet : {user.wallet.address}")

        logging.info("")
        logging.info("  Sending request to authorize batch addresses...")
        logging.info("")

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT_BLOCKCHAIN
            )

            status_code = response.status_code
            result_status = "success" if 200 <= status_code < 300 else "fail"
            
            logging.info(f"\tHTTP Status Code : {status_code}")
            logging.info(f"\tStatus           : {result_status}")

            if status_code != 200:
                logging.error(f"Authorization failed with status code {status_code}")
            else:
                logging.info("All users authorized successfully.")

        except requests.exceptions.Timeout:
            logging.error("Authorization request timed out ({timeout}s).")
        except requests.exceptions.RequestException as e:
            logging.error(f"Unexpected error during authorization: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")


        logging.info("")
        logging.info("Finish authorizing users for contract.")


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


    def _run(self, user, user_id, duration, run_function, results_operation):
        """Runs a single type of flow (API or Blockchain) for 'duration' seconds."""
        
        logging.info(f"[User-{user_id:03d}] Starting run: {run_function.__name__}")

        start_time = time.perf_counter()
        # request_count = 0

        while (time.perf_counter() - start_time) < duration:
            try:
                results = run_function()

                for result in results:
                    results_operation.append(result)

                # request_count += len(results)

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


        # logging.info(f"[User-{user_id:03d}] Finished {run_function.__name__}. Total tasks: {0}")
        logging.info(f"[User-{user_id:03d}] Finished {run_function.__name__}.")


    def simulate_user(self, phase, user_id: int, duration: float, interval_requests: float):
        """Runs the user's sequence of Tasks for 'duration' seconds."""

        user = self.users[user_id - 1]

        # 1. sequential API + Blockchain (API-TX_BUILD)
        if phase == "api-tx-build":
            self._run(user, user_id, duration, user.run_sequential_request, self.results_tx_build)

        # 2. random API (API-READ-ONLY)
        if phase == "api-read-only":
            self._run(user, user_id, duration, user.run_random_request, self.results_read_only)
            

    def run_static_load(self, phase, output_file=None):

        """Runs a static load test."""
    
        logging.info(f"Starting static load test with {self.number_users} users for {self.duration}s...")
        logging.info("")

        start_time = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.number_users) as executor:
            futures = [
                executor.submit(self.simulate_user, phase=phase, user_id=user_id, duration=self.duration, interval_requests=self.interval_requests)                
                for user_id in range(1, self.number_users + 1)
            ]

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"[THREAD ERROR] -> {type(e).__name__}: {e}")

        total_time = round(time.perf_counter() - start_time, 2)

        if phase == "api-tx-build":
            results = self.results_tx_build
        elif phase == "api-read-only":
            results = self.results_read_only
        else:
            results = []

        if output_file: 
            self.save_results(results=results, output_file=output_file)

        
        # total_tasks = len(results)

        # total_requests = len(results)
        
        # for result in results:
        #     print(result["task"])

        # rps = total_requests / total_time if total_time > 0 else 0
        
        # success = sum(1 for r in results if r["status"] == "success")
        # fails = sum(1 for r in results if r["status"] == "fail")


        # log.print_end_summary(
        #     total_requests=total_requests,
        #     total_tasks=total_tasks,
        #     success=success,
        #     fails=fails,
        #     total_time=total_time,
        #     rps=rps,
        #     output_file=output_file,
        #     mode=self.mode,
        #     contract=self.contract,
        #     run_type="static",
        #     users=self.number_users,
        #     duration=self.duration,
        #     interval_requests=self.interval_requests
        # )

        return total_time

    def run_ramp_up_load(self, phase, output_file=None):

        """Runs a ramp-up load test, adding users gradually."""
        
        logging.info(f"Starting ramp-up load test with up to {self.number_users} users...")
        logging.info("")
    
        start_time = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.number_users) as executor:
            futures = []
            active_users = 0

            while active_users < self.number_users:
                # Add a new user group (step users)
                new_users = min(self.step_users, self.number_users - active_users)
                for i in range(new_users):
                    user_id = active_users + i + 1
                    futures.append(
                        executor.submit(self.simulate_user, phase=phase, user_id=user_id, duration=self.duration, interval_requests=self.interval_requests)
                    )

                active_users += new_users
                logging.info(f"Active users: {active_users}/{self.number_users}")

                # Wait for the time between increments
                if active_users < self.number_users:
                    time.sleep(self.interval_users)

            # Wait for all threads to finish
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:                
                    logging.error(f"[THREAD ERROR] -> {type(e).__name__}: {e}")

        total_time = round(time.perf_counter() - start_time, 2)
        

        if phase == "api-tx-build":
            results = self.results_tx_build
        elif phase == "api-read-only":
            results = self.results_read_only
        else:
            results = []

        if output_file:
            self.save_results(results=results, output_file=output_file)


        return total_time
        # total_requests = len(results)
        # rps = total_requests / total_time if total_time > 0 else 0
        
        # success = sum(1 for r in results if r["status"] == "success")
        # fails = sum(1 for r in results if r["status"] == "fail")

        # log.print_end_summary(
        #     total_requests=total_requests,
        #     total_tasks=total_tasks,
        #     success=success,
        #     fails=fails,
        #     total_time=total_time,
        #     rps=rps,
        #     output_file=output_file,
        #     mode=self.mode,
        #     contract=self.contract,
        #     run_type="ramp-up",
        #     users=self.number_users,
        #     duration=self.duration,
        #     interval_requests=self.interval_requests,                  
        #     step_users=self.step_users,
        #     interval_users=self.interval_users,            
        # )


    def save_results(self, results, output_file: str):
        fieldnames = [
            "timestamp",
            "user_id",
            "request",
            "task",
            "endpoint",
            "duration",
            "status",
        ]

        filtered_rows = [
            {field: entry.get(field) for field in fieldnames}
            for entry in results
        ]

        with open(output_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(filtered_rows)
