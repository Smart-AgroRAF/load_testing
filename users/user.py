import json
import time
import random
import logging
import asyncio
import aiohttp
import uuid
from functools import partial

# Internal imports
import campaigns 
from wallet.wallet import Wallet
from tasks.task_api import TaskAPI
from tasks.task_blockchain import TaskBlockchain
from config import TIMEOUT_API

class User:
    """Simulates a user performing API or blockchain operations (Async)."""

    def __init__(self, host, mode, contract, user_id, interval_requests, campaign_names: list):

        self.host = host
        self.mode = mode
        self.contract = contract
        self.user_id = user_id
        self.interval_requests = interval_requests
        
        # self.requests_counter = 0 
        self.api_requests_counter = 0 
        self.blockchain_requests_counter = 0 

        self.api_success = 0
        self.api_fail = 0
        self.bc_success = 0
        self.bc_fail = 0

        self.api_errors = 0
        self.blockchain_errors = 0

        self.wallet = Wallet(self.user_id)
        self.campaign_names = campaign_names

        self.sequence_step = 0
        self.last_token_id = None
        self.batch_id = f"LOTE-{uuid.uuid4()}"

        # Session will be initialized in run_... methods or passed in
        self.session = None

        # READ-ONLY campaigns
        self.available_campaigns_read_only = self._build_user_campaigns_read_only()

        # TX-BUILD SEQUENTIAL campaigns
        self.available_campaigns_tx_build = self._build_user_campaigns_sequential_tx_build()

        logging.info(f"\t[User-{self.user_id:03d}] Wallet : {self.wallet.address}")

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
                    address=self.wallet.address,
                    batch_id=self.batch_id
                )

        return campaigns_dict
 

    def _build_user_campaigns_sequential_tx_build(self):
        """Constrói a sequência de métodos para as campanhas TX-BUILD."""
        campaigns_dict = {}
        # Usaremos esta lista para armazenar a sequência de funções
        self.tx_build_sequence = []

        for task_type in self.campaign_names:
            if task_type == "API-TX-BUILD":
                # A função build_campaign_sequential retorna a lista de requisições
                campaign_requests = campaigns.build_campaign_sequential(
                    contract=self.contract,
                    address=self.wallet.address,
                    batch_id=self.batch_id,
                    n_split_batch_tx=random.choice(range(1, 5)),
                    n_add_status_tx=random.choice(range(1, 5))
                )

                # Passo 1: Mint (adiciona a função _step_mint à sequência)
                mint_endpoint, mint_payload = campaign_requests[0]
                self.tx_build_sequence.append(partial(self._step_mint, mint_endpoint, mint_payload))

                # Passo 2: Get Token (adiciona a função _step_get_token)
                self.tx_build_sequence.append(self._step_get_token)

                # Passos seguintes: Transações que dependem do token_id
                for endpoint, payload in campaign_requests[1:]:
                    self.tx_build_sequence.append(partial(self._step_tx, endpoint, payload))
        
        return campaigns_dict


    async def _step_mint(self, endpoint, payload):
           """Passo 1: Executa o mintRootBatchTx (Async)."""
           measured_results, _, status = await self._measure_api_block(
               endpoint=endpoint,
               payload=payload,
               task_type="API-TX-BUILD"
           )
           if status == "reverted":
               # Se a transação for revertida, reiniciamos a sequência para este usuário
               self.sequence_step = 0
           return measured_results
   
    async def _step_get_token(self):
        """Passo 2: Executa o getUsersBatches e armazena o token ID (Async)."""
        try:
            contract = self.contract.lower().replace("-", "")
            endpoint = f"/api/{contract}/getUsersBatches"
            url = self.host + endpoint
            
            # Use aiohttp
            async with self.session.post(
                url=url,
                json={"userAddress": [self.wallet.address]},
                headers={"Content-Type": "application/json"},
                # timeout=aiohttp.ClientTimeout(total=TIMEOUT_API)
                timeout=TIMEOUT_API
            ) as response:
            
                if response.status != 200:
                    raise Exception(f"HTTP Error {response.status}")

                body = await response.json()

            if (
                not body or "results" not in body or len(body["results"]) == 0 or
                "tokenIds" not in body["results"][0] or len(body["results"][0]["tokenIds"]) == 0
            ):
                if self.mode == "api-only":
                    # In api-only mode, we don't mint on chain, so we won't find tokens.
                    # We simulate a token ID to allow the process to continue.
                    token_id = random.randint(1000, 1000000)
                    logging.debug(f"[User-{self.user_id:03d}] [GET-TOKEN] api-only mode: Simulating TokenId: {token_id}")
                else: 
                    logging.debug(f"[User-{self.user_id:03d}] [GET-TOKEN] Failed to find tokenIds. Body: {body}")
                    raise ValueError(f"No tokenIds found for this user. Contract: {self.contract}")
            else:
                token_id = body["results"][0]["tokenIds"][-1]
            self.last_token_id = token_id # Armazena o token no estado do usuário

            logging.debug(
                f"[User-{self.user_id:03d}]"
                f" {f'[GET-TOKEN]':<15}"
                f" {endpoint:31}"
                f" TokenId: {token_id}"
                # f" Body: {body}"
            )
            
            return [] # Este passo não gera resultados medidos
        except Exception as e:
            logging.error(f"[User-{self.user_id:03d}] Erro em _step_get_token: {e}", exc_info=True)
            self.sequence_step = 0 # Reinicia em caso de erro
            # Retorna um erro formatado como os outros resultados
            return [{"timestamp": int(time.time()), "user_id": self.user_id, "endpoint": "get_token_error", "status_code": "error", "duration": -1, "status": f"fail ({type(e).__name__})"}]
 
    async def _step_tx(self, endpoint, payload):
        """Passos seguintes: Executa uma transação genérica que precisa de um token ID (Async)."""
        if self.last_token_id is None:
            # Se não temos um token, não podemos continuar. Reiniciamos a sequência.
            logging.warning(f"[User-{self.user_id:03d}] Pulando passo de TX pois o token ID não foi definido.")
            self.sequence_step = 0
            return []

        updated_payload = self._replace_token_id(payload, self.last_token_id)

        measured_results, _, status = await self._measure_api_block(
            endpoint=endpoint,
            payload=updated_payload,
            task_type="API-TX-BUILD"
        )

        if status == "reverted":
            self.sequence_step = 0 # Reinicia em caso de erro

        return measured_results


    async def _api_request(self, endpoint, payload, task_type):
        """Executes one API request and increments request counter (Async)."""
        self.api_requests_counter += 1
        
        result, transaction = await self.task_api.run_request(
            session=self.session,
            endpoint=endpoint,
            payload=payload,
            task_type=task_type,
            request_id=self.api_requests_counter
        )

        if result and ((isinstance(result, dict) and result.get("status") == "success") or (isinstance(result, tuple) and result[0].get("status") == "success")):
             self.api_success += 1
        else:
             self.api_fail += 1

        if self.interval_requests:
            await asyncio.sleep(self.interval_requests)
        
        return result, transaction


    async def _blockchain_execute(self, tx_obj, endpoint):
        """Executes a blockchain transaction if mode == api-blockchain (Async)."""
        if self.mode != "api-blockchain":
            return [], None, None

        self.blockchain_requests_counter += 1

        # Await execution
        result, tx_hash, status = await self.task_blockchain.execute(
            tx_obj=tx_obj,
            endpoint=endpoint,
            request_id=self.blockchain_requests_counter
        )

        if status == "success":
            self.bc_success += 1
        else:
            self.bc_fail += 1
            
        return result, tx_hash, status


    # RANDOM MODE (READ-ONLY)
    async def run_random_request(self):
        """Executes a random READ-ONLY request (Async)."""
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

            api_result, _ = await self._api_request(endpoint, payload, "API-READ-ONLY")
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



    async def _measure_api_block(self, endpoint, payload, task_type):
        """
        Executes API + blockchain and appends a synthetic [API-BLOCK] result (Async).

        Returns:
            (results_list, tx_body, blockchain_status)
        """

        start_time = time.perf_counter()

        # API - returns (result_dict, tx_body_json)
        # Note: _api_request returns (result, transaction)
        api_result, tx_body = await self._api_request(
            endpoint=endpoint,
            payload=payload,
            task_type=task_type
        )

        # BLOCKCHAIN
        bc_results, _, status = await self._blockchain_execute(tx_body, endpoint)

        duration = time.perf_counter() - start_time

        if self.interval_requests:
            await asyncio.sleep(self.interval_requests)

        logging.debug(
            f"[User-{self.user_id:03d}]"
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
            "task": "FULL",
            "endpoint": endpoint,
            "duration": duration,
            "status": status
        }
        
        # Build final result list
        results_combined = [api_result]
        results_combined.extend(bc_results)
        results_combined.append(api_block_result)

        return results_combined, tx_body, status

    async def run_sequential_request(self):
        """
        Executa UM passo do fluxo sequencial de TX (Async).
        """
        try:
            if not self.tx_build_sequence:
                raise RuntimeError("Nenhuma sequência de TX-BUILD disponível para este usuário.")

            # Pega a função correspondente ao passo atual
            step_function = self.tx_build_sequence[self.sequence_step]

            # Executa o passo (await)
            # Como usamos partial, se a função original for async, o partial retorna uma coroutine quando chamado?
            # Não, partial apenas fixa argumentos. Se a função for async, ela retorna coroutine.
            
            if asyncio.iscoroutinefunction(step_function) or (isinstance(step_function, partial) and asyncio.iscoroutinefunction(step_function.func)):
                 results = await step_function()
            else:
                 # Fallback synchronous? Need to ensure all steps are async
                 results = step_function()


            self.sequence_step = (self.sequence_step + 1) % len(self.tx_build_sequence)

            return results

        except Exception as e:
            logging.error(
                f"[User-{self.user_id:03d}] Erro em run_sequential_request (passo {self.sequence_step}): {e}",
                exc_info=True
            )
            self.sequence_step = 0
            return [{
                "timestamp": int(time.time()),
                "user_id": self.user_id,
                "endpoint": "sequential_request_error",
                "status_code": "error",
                "duration": -1,
                "status": f"fail ({type(e).__name__})"
            }]
