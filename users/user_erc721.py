from users.user import User

class UserERC721(User):
    """Usuário especializado para testes com contratos ERC-721."""

    def __init__(self, host: str, mode: str, user_id: int, interval_requests: float):
        
        super().__init__(
            host=host,
            mode=mode,
            contract="ERC-721",
            user_id=user_id,
            interval_requests=interval_requests,
            campaign_names=["API-READ-ONLY", "API-TX-BUILD"]
        )

