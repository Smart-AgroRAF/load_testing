import json
import time
import random
import logging
import requests

# Internal imports
import campaigns 
from wallet.wallet import Wallet
from tasks.task_api import TaskAPI
from tasks.task_blockchain import TaskBlockchain
from config import TIMEOUT_API

class User:
    """Simulates a user performing API or blockchain operations."""

    def __init__(self, host, mode, contract, user_id, interval_requests, campaign_names: list):

        self.host = host
        self.mode = mode
        self.contract = contract
        self.user_id = user_id
        self.interval_requests = interval_requests
        
        # self.requests_counter = 0 
        self.api_requests_counter = 0 
        self.blockchain_requests_counter = 0 

        self.api_errors = 0
        self.blockchain_errors = 0

        self.wallet = Wallet(self.user_id)
        self.campaign_names = campaign_names

        # READ-ONLY campaigns
        self.available_campaigns_read_only = self._build_user_campaigns_read_only()

        # TX-BUILD SEQUENTIAL campaigns
        self.available_campaigns_tx_build = self._build_user_campaigns_sequential_tx_build()

        logging.info(f"\t[User-{self.user_id:03d}] wallet : {self.wallet.address}")

        self.task_api = TaskAPI(host, user_id)
        self.task_blockchain = TaskBlockchain(self.wallet, user_id)


    # CAMPAIGN BUILDERS
    def _build_user_campaigns_read_only(self):
        """Builds READ-ONLY campaigns."""
        campaigns_dict = {}

        for task_type in self.campaign_names:
            if task_type == "API-READ-ONLY":
                campaigns_dict[(self.contract, task_type)] = campaigns.build_campaign(
                    contract=self.contract,
                    task_type="API-READ-ONLY",
                    address=self.wallet.address
                )

        return campaigns_dict
 

    def _build_user_campaigns_sequential_tx_build(self):
        """Builds TX-BUILD sequential campaigns."""
        campaigns_dict = {}

        for task_type in self.campaign_names:
            if task_type == "API-TX-BUILD":
                campaigns_dict[(self.contract, task_type)] = campaigns.build_campaign_sequential(
                    contract=self.contract,
                    address=self.wallet.address,
                    n_split_batch_tx=random.choice(range(1, 5)),
                    # n_set_product_is_active_tx=random.choice(range(1, 5)),
                    n_add_status_tx=random.choice(range(1, 5))
                )

        return campaigns_dict

    def _api_request(self, endpoint, payload, task_type):
        """Executes one API request and increments request counter."""
        self.api_requests_counter += 1
        # self.requests_counter += 1

        result = self.task_api.run_request(
            endpoint=endpoint,
            payload=payload,
            task_type=task_type,
            request_id=self.api_requests_counter
            # request_id=self.requests_counter
        )

        if self.interval_requests:
            time.sleep(self.interval_requests)
        
        return result



    def _blockchain_execute(self, tx_obj, endpoint):
        """Executes a blockchain transaction if mode == api-blockchain."""
        if self.mode != "api-blockchain":
            return [], None, None

        self.blockchain_requests_counter += 1
        # self.requests_counter += 1

        return self.task_blockchain.execute(
            tx_obj=tx_obj,
            endpoint=endpoint,
            request_id=self.blockchain_requests_counter
            # request_id=self.requests_counter
        )


    # RANDOM MODE (READ-ONLY)
    def run_random_request(self):
        """Executes a random READ-ONLY request."""
        results = []

        try:
            if not self.available_campaigns_read_only:
                raise RuntimeError("No READ-ONLY campaigns available.")

            # Select a random contract campaign
            (contract, _), campaign = random.choice(
                list(self.available_campaigns_read_only.items())
            )

            # Select a random endpoint
            endpoint, payload = random.choice(campaign)

            api_result, _ = self._api_request(endpoint, payload, "API-READ-ONLY")
            results.append(api_result)

            return results

        except Exception as e:
            logging.error(
                f"[User-{self.user_id:03d}] Error in run_random_request: {e}",
                exc_info=True
            )
            return [{
                "timestamp": int(time.time()),
                "user_id": self.user_id,
                "endpoint": "random_request_error",
                "status_code": "error",
                "duration": -1,
                "result": f"fail ({type(e).__name__})"
            }]


    
    def _replace_token_id(self, obj, token_id):
        """Recursively replaces <TOKEN_ID> in a JSON object."""
        if isinstance(obj, dict):
            return {k: self._replace_token_id(v, token_id) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_token_id(v, token_id) for v in obj]
        elif isinstance(obj, str):
            return obj.replace("<TOKEN_ID>", str(token_id))
        return obj



    def _measure_api_block(self, endpoint, payload, task_type):
        """
        Executes API + blockchain and appends a synthetic [API-BLOCK] result.

        Returns:
            (results_list, tx_body, blockchain_status)
        """

        start_time = time.perf_counter()

        # API
        api_result, tx_body = self._api_request(
            endpoint=endpoint,
            payload=payload,
            task_type=task_type
        )

        # BLOCKCHAIN
        bc_results, _, status = self._blockchain_execute(tx_body, endpoint)

        duration = time.perf_counter() - start_time

        if self.interval_requests:
            time.sleep(self.interval_requests)

        logging.info(
            f"[User-{self.user_id:03d}]"
            # f" [Req-{self.requests_counter:03d}]"
            # f" [REQ-FULL-{self.blockchain_requests_counter:03d}]"
            f" {f'[REQ-BLOCK-{self.blockchain_requests_counter:03d}]':<15}"
            f" {f'[FULL]':<15}"
            f" {endpoint:<31}"
            f" {duration:<1.3f}s"
        )
        
        # Synthetic API-BLOCK entry
        api_block_result = {
            "timestamp": int(time.time()),
            "user_id": self.user_id,
            "request": self.blockchain_requests_counter,
            # "request": self.requests_counter,
            "task": "FULL",
            "endpoint": endpoint,
            "duration": duration,
            "status": ""
        }
        
        # Build final result list
        results_combined = [api_result]
        results_combined.extend(bc_results)
        results_combined.append(api_block_result)

        return results_combined, tx_body, status



    def run_sequential_request(self):
        """
        Sequential TX workflow (must preserve strict order):
        mintRootBatchTx -> getUsersBatches -> splitBatchTx -> setProductIsActiveTx -> addStatusTx
        """
        results = []

        try:
            # Load sequential campaign
            key = None
            campaign_requests = None

            for k in self.available_campaigns_tx_build.keys():
                key = k
                campaign_requests = self.available_campaigns_tx_build[k]
                break

            if not campaign_requests:
                raise RuntimeError("No TX-BUILD campaigns available.")

            
            # STEP 1. mintRootBatchTx (MEASURED)
            mint_endpoint, mint_payload = campaign_requests[0]

            measured_results, mint_body, status = self._measure_api_block(
                endpoint=mint_endpoint,
                payload=mint_payload,
                task_type="API-TX-BUILD"
            )
            results.extend(measured_results)

            if status == "reverted":
                return results

            
            # STEP 2.  getUsersBatches (NOT MEASURED)
            contract = self.contract.lower().replace("-", "")
            endpoint = f"/api/{contract}/getUsersBatches"
            url = self.host + endpoint
            response = requests.post(
                url=url,
                json={"userAddress": [self.wallet.address]},
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT_API
            )
            
            body = response.json()

            if (
                not body or "results" not in body or len(body["results"]) == 0 or
                "tokenIds" not in body["results"][0] or len(body["results"][0]["tokenIds"]) == 0
            ):
                raise ValueError("No tokenIds found for this user.")

            token_id = body["results"][0]["tokenIds"][-1]

            logging.info(
                f"{f'[User-{self.user_id:03d}]'}"
                f" {f'[GET-TOKEN]':<15}"
                f" {endpoint:31}"
                f" TokenId: {token_id}"
            )

            
            # STEP 3, 4, 5. n * splitBatchTx -> n * setProductIsActiveTx -> n * addStatusTx (MEASURED)
            for endpoint, payload in campaign_requests[1:]:
                updated_payload = self._replace_token_id(payload, token_id)

                measured_results, tx_body, status = self._measure_api_block(
                    endpoint=endpoint,
                    payload=updated_payload,
                    task_type="API-TX-BUILD"
                )

                results.extend(measured_results)

                if status == "reverted":
                    break

            return results

        except Exception as e:
            logging.error(
                f"[User-{self.user_id:03d}] Error in run_sequential_request: {e}",
                exc_info=True
            )
            return [{
                "timestamp": int(time.time()),
                "user_id": self.user_id,
                "endpoint": "sequential_request_error",
                "status_code": "error",
                "duration": -1,
                "status": f"fail ({type(e).__name__})"
            }]
