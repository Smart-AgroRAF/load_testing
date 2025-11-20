from users.user import User

class UserERC1155(User):
    """Usuário especializado para testes com contratos ERC-1155."""

    def __init__(self, host: str, mode: str, user_id: int):

        super().__init__(
            host=host,
            mode=mode,
            user_id=user_id,
            campaign_names=[("ERC-1155", "API-READ"), ("ERC-1155", "API-BUILD")]
        )
