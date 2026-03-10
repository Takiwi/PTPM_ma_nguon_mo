import pytest
import discord
from unittest.mock import AsyncMock, MagicMock

from cogs.explain import Explain


class MockResponse:
    def __init__(self):
        self.text = "Đây là nội dung giải thích mẫu từ AI."


@pytest.mark.asyncio
async def test_explain_success():
    # Mock bot
    bot = MagicMock()

    # Tạo cog
    cog = Explain(bot)

    # Mock Gemini client
    mock_generate = AsyncMock(return_value=MockResponse())
    cog.client = MagicMock()
    cog.client.aio = MagicMock()
    cog.client.aio.models = MagicMock()
    cog.client.aio.models.generate_content = mock_generate

    # Mock interaction
    interaction = MagicMock(spec=discord.Interaction)

    interaction.user = MagicMock()
    interaction.user.display_name = "TestUser"
    interaction.user.avatar = None

    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()

    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    # Gọi hàm
    await cog.explain.callback(
        cog,
        interaction,
        field="Toán",
        concept="Định lý Pythagoras"
    )

    # Kiểm tra đã gửi embed
    interaction.followup.send.assert_called_once()

    args, kwargs = interaction.followup.send.call_args

    embed = kwargs["embed"]

    assert "Pythagoras" in embed.title