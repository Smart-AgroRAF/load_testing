import copy

payload_mint_root_batch = {
    "from": "<FROM>",
    "to": "<TO>",
    "productName": "Tomate",
    "productExpeditionDate": "2025-06-11",
    "productType": "Tomate BRS Zamir",
    "batchId": "LOTE-01",
    "unitOfMeasure": "kg",
    "batchQuantity": 100,
}

payload_split_batch = {
    "from": "<FROM>",
    "to": "<TO>",
    "parentTokenId": 1,
    "newUnitOfMeasure": "kg",
    "newBatchQuantity": 50,
}

payload_set_product_is_active = {
    "from": "<FROM>",
    "tokenId": 1,
    "active": False,
}

payload_add_status = {
    "from": "<FROM>",
    "tokenId": 1,
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
    "batchId": "LOTE-01",
}

payload_get_batch_products = {
    "tokenIds": [1, 2],
}

payload_get_batch_histories = {
    "tokenIds": [1, 2],
}

erc721_tx_build = [
    ("/api/erc721/mintRootBatchTx", payload_mint_root_batch),
    # ("/api/erc721/splitBatchTx", payload_split_batch),
    # ("/api/erc721/setProductIsActiveTx", payload_set_product_is_active),
    # ("/api/erc721/addStatusTx", payload_add_status),
]

erc1155_tx_build = [
    ("/api/erc1155/mintRootBatchTx", payload_mint_root_batch),
    # ("/api/erc1155/splitBatchTx", payload_split_batch),
    # ("/api/erc1155/setProductIsActiveTx", payload_set_product_is_active),
    # ("/api/erc1155/addStatusTx", payload_add_status),
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
    ("ERC-721", "API-BUILD"): erc721_tx_build,
    ("ERC-1155", "API-BUILD"): erc1155_tx_build,

    ("ERC-721", "API-READ"): erc721_read_only,
    ("ERC-1155", "API-READ"): erc1155_read_only,

    # Full = build + read
    # "erc721_full": erc721_tx_build + erc721_read_only,
    # "erc1155_full": erc1155_tx_build + erc1155_read_only,

    # Mixed
    # "mixed_tx_build": erc721_tx_build + erc1155_tx_build,
    # "mixed_read_only": erc721_read_only + erc1155_read_only,
    # "mixed_full": erc721_tx_build + erc721_read_only + erc1155_tx_build + erc1155_read_only,
}

def _replace_placeholders(obj, address: str):
    """
    Substitui recursivamente <FROM> e <TO> em qualquer estrutura (dict, list, str).
    """
    if isinstance(obj, dict):
        return {k: _replace_placeholders(v, address) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_placeholders(v, address) for v in obj]
    elif isinstance(obj, str):
        return obj.replace("<FROM>", address).replace("<TO>", address)
    return obj


def build_campaign(contract: str, task_type: str, address: str):   
    """
    Constrói uma campanha substituindo <FROM> e <TO> pelos endereços reais.
    Retorna uma lista de (endpoint, payload).
    """
        
    campaign_key = (contract, task_type)
    if campaign_key not in CAMPAIGNS:
        raise ValueError(f"Campaign '{contract} {task_type}' not found.")

    final_campaign = []
    for endpoint, payload in CAMPAIGNS[campaign_key]:
        payload_copy = copy.deepcopy(payload)
        replaced = _replace_placeholders(payload_copy, address)
        final_campaign.append((endpoint, replaced))

    return final_campaign
