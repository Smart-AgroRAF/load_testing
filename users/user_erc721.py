from users.user import User

class UserERC721(User):
    """Usuário especializado para testes com contratos ERC-721."""

    def __init__(self, host: str, mode: str, user_id: int):
        
        super().__init__(
            host=host,
            mode=mode,
            user_id=user_id,
            campaign_names=[("ERC-721", "API-READ"), ("ERC-721", "API-BUILD")]
        )

