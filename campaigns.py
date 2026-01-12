import copy

payload_mint_root_batch = {
    "from": "<FROM>",
    "to": "<TO>",
    "productName": "Tomate",
    "productExpeditionDate": "2025-06-11",
    "productType": "Tomate BRS Zamir",
    "batchId": "<BATCH_ID>",
    "unitOfMeasure": "kg",
    "batchQuantity": 1000000,
}

payload_split_batch = {
    "from": "<FROM>",
    "to": "<TO>",
    "parentTokenId": "<TOKEN_ID>",
    "newUnitOfMeasure": "kg",
    "newBatchQuantity": 1,
}

payload_set_product_is_active = {
    "from": "<FROM>",
    "tokenId": "<TOKEN_ID>",
    "active": True,
}

payload_add_status = {
    "from": "<FROM>",
    "tokenId": "<TOKEN_ID>",
    "message": "Enviado para a cooperativa",
    "buyerName": "Comprador 1",
    "buyerIdentification": "Id Comprador 1",
    "currentLocation": "Alegrete",
    "updateType": 2,
}

payload_get_users_batches = {
    "userAddress": ["<FROM>"],
}

payload_get_tokens_by_batch_id = {
    "batchId": "<BATCH_ID>",
}

payload_get_batch_products = {
    "tokenIds": [1, 2],
}

payload_get_batch_histories = {
    "tokenIds": [1, 2],
}

erc721_tx_build = [
    ("/api/erc721/mintRootBatchTx", payload_mint_root_batch),
    ("/api/erc721/splitBatchTx", payload_split_batch),
    ("/api/erc721/setProductIsActiveTx", payload_set_product_is_active),
    ("/api/erc721/addStatusTx", payload_add_status),
]

erc1155_tx_build = [
    ("/api/erc1155/mintRootBatchTx", payload_mint_root_batch),
    ("/api/erc1155/splitBatchTx", payload_split_batch),
    ("/api/erc1155/setProductIsActiveTx", payload_set_product_is_active),
    ("/api/erc1155/addStatusTx", payload_add_status),
]

erc721_read_only = [
    ("/api/erc721/getUsersBatches", payload_get_users_batches),
    ("/api/erc721/getTokensByBatchId", payload_get_tokens_by_batch_id),
    ("/api/erc721/getBatchProducts", payload_get_batch_products),
    ("/api/erc721/getBatchHistories", payload_get_batch_histories),
]

erc1155_read_only = [
    ("/api/erc1155/getUsersBatches", payload_get_users_batches),
    ("/api/erc1155/getTokensByBatchId", payload_get_tokens_by_batch_id),
    ("/api/erc1155/getBatchProducts", payload_get_batch_products),
    ("/api/erc1155/getBatchHistories", payload_get_batch_histories),
]

CAMPAIGNS = {
    ("ERC-721", "API-TX-BUILD"): erc721_tx_build,
    ("ERC-1155", "API-TX-BUILD"): erc1155_tx_build,

    ("ERC-721", "API-READ-ONLY"): erc721_read_only,
    ("ERC-1155", "API-READ-ONLY"): erc1155_read_only,

    # Full = build + read
    # "erc721_full": erc721_tx_build + erc721_read_only,
    # "erc1155_full": erc1155_tx_build + erc1155_read_only,

    # Mixed
    # "mixed_tx_build": erc721_tx_build + erc1155_tx_build,
    # "mixed_read_only": erc721_read_only + erc1155_read_only,
    # "mixed_full": erc721_tx_build + erc721_read_only + erc1155_tx_build + erc1155_read_only,
}

def _replace_placeholders(obj, address: str, batch_id: str):
    """
    Substitui recursivamente <FROM>, <TO> e <BATCH_ID> em qualquer estrutura (dict, list, str).
    """
    if isinstance(obj, dict):
        return {k: _replace_placeholders(v, address, batch_id) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_placeholders(v, address, batch_id) for v in obj]
    elif isinstance(obj, str):
        return obj.replace("<FROM>", address).replace("<TO>", address).replace("<BATCH_ID>", batch_id)
    return obj


def build_campaign(contract: str, task_type: str, address: str, batch_id: str):   
    """
    Constrói uma campanha substituindo <FROM>, <TO> e <BATCH_ID> pelos valores reais.
    Retorna uma lista de (endpoint, payload).
    """
        
    campaign_key = (contract, task_type)
    if campaign_key not in CAMPAIGNS:
        raise ValueError(f"Campaign '{contract} {task_type}' not found.")

    final_campaign = []
    for endpoint, payload in CAMPAIGNS[campaign_key]:
        payload_copy = copy.deepcopy(payload)
        replaced = _replace_placeholders(payload_copy, address, batch_id)
        final_campaign.append((endpoint, replaced))

    return final_campaign


def build_campaign_sequential(
    contract: str,
    address: str,
    batch_id: str,
    n_split_batch_tx: int = None,
    n_set_product_is_active_tx: int = None,
    n_add_status_tx: int = None
):
    """
    Builds a SEQUENTIAL campaign with the following fixed order:

        mintRootBatchTx -> n splitBatchTx -> n setProductIsActiveTx -> n addStatusTx

    This function returns the campaign in the exact same format expected by
    User._build_user_campaigns(), meaning a list of (endpoint, payload) tuples.

    Parameters
    ----------
    contract : str
        Either "ERC-721" or "ERC-1155".
    address : str
        Address used to replace <FROM> and <TO> placeholders.
    batch_id : str
        Batch ID used to replace <BATCH_ID> placeholders.
    n_split_batch_tx : int
        Number of repeated splitBatchTx calls.
    n_set_product_is_active_tx : int
        Number of repeated setProductIsActiveTx calls.
    n_add_status_tx : int
        Number of repeated addStatusTx calls.

    Returns
    -------
    list[tuple[str, dict]]
        A list of (endpoint, payload) tuples in sequential order.

    Raises
    ------
    ValueError
        If the contract type is invalid.
    """

    # Select correct template set
    if contract == "ERC-721":
        tx_templates = erc721_tx_build
    elif contract == "ERC-1155":
        tx_templates = erc1155_tx_build
    else:
        raise ValueError("Contract must be 'ERC-721' or 'ERC-1155'.")

    mint_tpl = tx_templates[0]   # mintRootBatchTx
    split_tpl = tx_templates[1]  # splitBatchTx
    active_tpl = tx_templates[2] # setProductIsActiveTx
    status_tpl = tx_templates[3] # addStatusTx

    campaign = []

    # 1. mintRootBatchTx (always once)
    endpoint, payload = mint_tpl
    replaced = _replace_placeholders(copy.deepcopy(payload), address, batch_id)
    campaign.append((endpoint, replaced))

    # 2. splitBatchTx (n times)
    if n_split_batch_tx:
        for _ in range(n_split_batch_tx):
            endpoint, payload = split_tpl
            replaced = _replace_placeholders(copy.deepcopy(payload), address, batch_id)
            campaign.append((endpoint, replaced))

    # 3. setProductIsActiveTx (n times)
    if n_set_product_is_active_tx:
        for _ in range(n_set_product_is_active_tx):
            endpoint, payload = active_tpl
            replaced = _replace_placeholders(copy.deepcopy(payload), address, batch_id)
            campaign.append((endpoint, replaced))

    # 4. addStatusTx (n times)
    if n_add_status_tx:
        for _ in range(n_add_status_tx):
            endpoint, payload = status_tpl
            replaced = _replace_placeholders(copy.deepcopy(payload), address, batch_id)
            campaign.append((endpoint, replaced))

    return campaign
