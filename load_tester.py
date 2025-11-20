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
from wallet.admin import fund_wallet, compile_contract, fund_wallets_batch
from users.user import User
from config import TIMEOUT_BLOCKCHAIN, AMOUNT_ETH
from wallet.config import w3

class LoadTester:
    """Performs HTTP load tests simulating multiple users."""

    def __init__(
        self, 
        output_file,
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
    
        self.output_file = output_file
        self.host = host
        self.mode = mode
        self.contract = contract
        self.duration = duration

        self.users = self._create_users(amount_users=users)
        self.number_users = len(self.users)
        self.step_users = step_users
        self.interval_users = interval_users
        self.interval_requests = interval_requests 

        if self.mode == "api-blockchain":
            self._authorized_users()
            self._fund_users()

        self.results: List[Dict] = []    

    def _fund_users(self):
        
        logging.info("-" * log.SIZE)
        logging.info("Starting fund users...")
        logging.info("")
        
        for user in self.users:
            try:
                fund_wallet(user.wallet.address, amount_eth=AMOUNT_ETH)
                balance = user.wallet.get_balance()
                logging.info(f"[User-{user.user_id:03d}] Wallet funded successfully. Balance: {balance} ETH")
            except Exception as e:
                logging.error(f"[User-{user.user_id:03d}] Failed to fund wallet {user.wallet.address}: {e}")
        
        logging.info("Finish fund users.")


        # logging.info("-" * log.SIZE)
        # logging.info("Starting fund users...")
        # logging.info("")

        # compile_contract()

        # recipients = []
        # for user in self.users:
        #     recipients.append(user.wallet.address)

    
        # fund_wallets_batch(recipients=recipients, amount_eth=AMOUNT_ETH)

        # logging.info("Recipients:")
        # for u in self.users:
        #     logging.info(f"  {u.user_id} -> {u.wallet.address}  balance={w3.eth.get_balance(u.wallet.address)}")

        # logging.info("Finish fund users.")


    def _authorized_users(self):

        logging.info("-" * log.SIZE)
        logging.info("Starting authorizing users for contract...")
        logging.info("")

        url = f"{self.host}/api/{self.contract}/admin/setAllowedAddressesBatch"

        addresses = [user.wallet.address for user in self.users]

        payload = {
            "addresses": addresses,
            "allow": True
        }

        # json_data = json.dumps(payload)
       
        logging.info(f"  - URL            : {url}")
        logging.info(f"  - Total users    : {len(addresses)}")
        logging.info(f"  - Users:")
        for user in self.users:
            logging.info(f"      [User-{user.user_id:03d}] Wallet : {user.wallet.address}")

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
            result_status = "Success" if 200 <= status_code < 300 else "Fail"
            
            logging.info(f"  HTTP Status Code : {status_code}")
            logging.info(f"  Status           : {result_status}")

            if status_code != 200:
                logging.error(f"  Authorization failed with status code {status_code}")
            else:
                logging.info("  All users authorized successfully.")

        # except subprocess.TimeoutExpired:
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

        logging.info(f"Instantiating {amount_users} users...")
        logging.info("")

        users = []

        for user_id in range(1, amount_users + 1):
            users.append(self.user_cls(
                host=self.host,
                mode=self.mode,
                user_id=user_id,
            ))

        logging.info("")
        logging.info(f"All {len(users)} users instantiated.")

        return users



    def simulate_user(self, user_id: int, duration: float, interval_requests: float):
        """Runs the user's sequence of Tasks for 'duration' seconds."""

        user = self.users[user_id - 1]

        logging.info(f"[User-{user_id:03d}] Starting Task execution...")

        start_time = time.perf_counter()
        request_count = 0

        while (time.perf_counter() - start_time) < duration:
            try:
        
                # if self.mode == "api-only":
                #     task_type = random.choices(
                #         ["read_only", "tx_build"],
                #         weights=[0.5, 0.5]
                #     )[0]

                #     if task_type == "read_only":
                #         results = user.run_tasks_read_only(interval_requests)
                #         logging.debug(f"[User-{user_id:03d}] Running READ_ONLY")
                #     elif task_type == "tx_build":
                #         results = user.run_tasks_tx_build(interval_requests)
                #         logging.debug(f"[User-{user_id:03d}] Running TX_BUILD")

                # elif self.mode == "api-blockchain":
                #     results = user.run_tasks_tx_build_sequential()

                results = user.run_random_request()

                for result in results:
                    self.results.append(result)
                request_count += 1

            except Exception as e:
                logging.error(f"[User-{user_id:03d}] Error during Task execution: {type(e).__name__}: {e}")
                self.results.append({
                    "timestamp": int(time.time()),
                    "user_id": user_id,
                    "endpoint": "unknown",
                    "status_code": "error",
                    "duration": -1,
                    "result": f"fail ({type(e).__name__})"
                })

            time.sleep(interval_requests)

        logging.info(f"[User-{user_id:03d}] Finished. Total requests: {request_count}")

    

    def run_static_load(self):

        """Runs a static load test."""
    
        logging.info(f"Starting static load test with {self.number_users} users for {self.duration}s...\n")

        start_time = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.number_users) as executor:
            futures = [
                executor.submit(self.simulate_user, user_id=user_id, duration=self.duration, interval_requests=self.interval_requests)                
                for user_id in range(1, self.number_users + 1)
            ]

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"[THREAD ERROR] -> {type(e).__name__}: {e}")

        total_time = round(time.perf_counter() - start_time, 2)

        self.save_results(self.output_file)

        total_requests = len(self.results)
        rps = total_requests / total_time if total_time > 0 else 0
        
        success = sum(1 for r in self.results if r["status"].startswith("success"))
        fails = sum(1 for r in self.results if r["status"].startswith("fail"))


        log.print_end_summary(
            total_requests=total_requests,
            success=success,
            fails=fails,
            total_time=total_time,
            rps=rps,
            output_file=self.output_file,
            mode=self.mode,
            contract=self.contract,
            run_type="static",
            users=self.number_users,
            duration=self.duration,
            interval_requests=self.interval_requests
        )


    def run_ramp_up_load(self):

        """Runs a ramp-up load test, adding users gradually."""
        
        logging.info(f"Starting ramp-up load test with up to {self.number_users} users...\n")
    
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
                        executor.submit(self.simulate_user, user_id, self.duration, self.interval_requests)
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
        
        self.save_results(self.output_file)

        total_requests = len(self.results)
        rps = total_requests / total_time if total_time > 0 else 0
        

        success = sum(1 for r in self.results if r["status"].startswith("success"))
        fails = sum(1 for r in self.results if r["status"].startswith("fail"))


        log.print_end_summary(
            total_requests=total_requests,
            success=success,
            fails=fails,
            total_time=total_time,
            rps=rps,
            output_file=self.output_file,
            mode=self.mode,
            contract=self.contract,
            run_type="ramp-up",
            users=self.number_users,
            duration=self.duration,
            interval_requests=self.interval_requests,                  
            step_users=self.step_users,
            interval_users=self.interval_users,            
        )


    def save_results(self, output_file: str):
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
            for entry in self.results
        ]

        with open(output_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(filtered_rows)
