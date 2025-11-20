import json
import time
import random
import subprocess
import logging

# Internal imports
import campaigns 
from wallet.wallet import Wallet
from tasks.task import Task
from tasks.task_blockchain import TaskBlockchain

class User:
    """Simula um usuário que faz uma requisição HTTP usando curl."""

    def __init__(
        self, 
        host,
        mode,
        user_id,
        campaign_names: list,
    ):

        self.host = host
        self.mode = mode
        self.user_id = user_id
        self.request_counter = 0 

        self.wallet = Wallet(self.user_id)
        logging.info(f"  [User-{self.user_id:03d}] Wallet initialized: {self.wallet.address}")

        self.campaign_names = campaign_names
         
        # Constrói todas as campanhas disponíveis para este usuário e as armazena
        self.available_campaigns = {}
        for contract, task_type in self.campaign_names:
            campaign_key = (contract, task_type)
            self.available_campaigns[campaign_key] = campaigns.build_campaign(contract=contract, task_type=task_type, address=self.wallet.address)
        logging.info(f"  [User-{self.user_id:03d}] Available campaigns: {list(self.available_campaigns.keys())}")


        self.task_http = Task(host, user_id)
        self.task_blockchain = TaskBlockchain(self.wallet, user_id)
   
        # Cria uma única instância de Task que será usada para fazer as requisições
        # A campanha e o tipo serão definidos dinamicamente a cada chamada
        # self.task_runner = Task(host=self.host, task_type="", campaign=[], user_id=self.user_id)
            
    def run_random_request(self):
        """
        Randomly selects a campaign, randomly selects a request inside it, executes it,
        and if required, interacts with the blockchain (tx_build campaigns).
        """
        results = []
        try:
            
            # 1. Pick a random campaign
            chosen_campaign_key = random.choice(list(self.available_campaigns.keys()))
            contract_type, task_type = chosen_campaign_key 
            
            # 2. Get its requests
            campaign_requests = self.available_campaigns[chosen_campaign_key]
            if not campaign_requests:
                logging.warning(f"[User-{self.user_id:03d}] Campaign {contract_type}_{task_type} is empty. Skipping.")
                return []

            # 3. Pick a single request (endpoint, payload)
            endpoint, payload = random.choice(campaign_requests)

            # 4. Request HTTP
            self.request_counter += 1
            result, transaction = self.task_http.run_request(
                endpoint=endpoint, 
                payload=payload,
                task_type=task_type,
                request_id=self.request_counter
            )

            results.append(result)

            # 5. Se for uma campanha de transação ("tx_build"), processa com a wallet
            if task_type =="API-BUILD" and self.mode == "api-blockchain":

                result, tx_hash, receipt_status = self.task_blockchain.execute(
                    tx_obj=transaction,
                    endpoint=endpoint,
                    request_id=self.request_counter
                )

                # result["tx_hash"] = tx_hash
                # result["receipt_status"] = receipt_status

                results.extend(result)

            return results

        except Exception as e:
            logging.error(
                f"[User-{self.user_id:03d}] Error while executing run_random_request: {e}",
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



        # def _create_tasks(self):
        #     tasks = {}
           
        #     # Cria tarefas sob demanda com base nas campanhas fornecidas
        #     if name := self.campaign_names.get("{}read_only"):
        #         self.campaign = campaigns.build_campaign(name, self.wallet.address)
        #         tasks["read_only"] = TaskReadOnly(self.host, "READ_ONLY", campaign, self.user_id)
    
        #     if name := self.campaign_names.get("tx_build"):
        #         self.campaign = campaigns.build_campaign(name, self.wallet.address)
        #         tasks["tx_build"] = TaskTxBuild(self.host, "TX_BUILD", campaign, self.user_id)
            
        #     # Exemplo com a nova tarefa sequencial
        #     if name := self.campaign_names.get("erc721_sequential"):
        #         campaign = campaigns.build_campaign(name, self.wallet.address)
        #         tasks["erc721_sequential"] = TaskErc721Sequential(self.host, campaign, self)
                
        #     return tasks



    #     self.tasks_read_only = []

    #     self.tasks_read_only.append(
    #         TaskReadOnly(
    #             host=self.host,
    #             task_type="READ_ONLY",
    #             campaign=self.campaign_read_only,
    #             user_id=self.user_id
    #         )
    #     )

    #     self.tasks_tx_build = []

    #     self.tasks_tx_build.append(
    #         TaskTxBuild(
    #             host=self.host,
    #             task_type="TX_BUILD",
    #             campaign=self.campaign_tx_build,
    #             user_id=self.user_id
    #         )
    #     )

    # def run_tasks_read_only(self):
    #     results = []
    #     for task in self.tasks_read_only:
    #         result, body = task.run()
    #         results.append(result)
    #     return results
 
    # def run_tasks_tx_build(self):
    #     results = []
    #     for task in self.tasks_tx_build:
    #         result, body = task.run()
    #         results.append(result)
    #     return results



    # def run_task(self, task_name: str):
    #     """Executa uma tarefa específica pelo nome."""
    #     task_to_run = self.tasks.get(task_name)
    #     if not task_to_run:
    #         logging.error(f"[User-{self.user_id:03d}] Tarefa '{task_name}' não encontrada.")
    #         return []
        
    #     # O método run de cada tarefa retorna uma lista de resultados
    #     return task_to_run.run()

    