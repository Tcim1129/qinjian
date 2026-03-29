"""情绪分析功能测试"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def positive_text():
    return "今天和对象一起看电影，感觉特别幸福，被支持被爱着。"


@pytest.fixture
def negative_text():
    return "又吵架了，感觉很累很沮丧，不知道怎么办。"


@pytest.fixture
def neutral_text():
    return "今天正常上班，没什么特别的事情。"


class TestAnalyzeSentiment:
    """情绪分析测试"""

    @pytest.mark.asyncio
    async def test_positive_sentiment(self, positive_text):
        """测试积极情绪识别"""
        from app.ai import analyze_sentiment

        with patch("app.ai.chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (
                '{"sentiment": "positive", "score": 8, "emotions": ["幸福", "被爱"]}'
            )

            result = await analyze_sentiment(positive_text)

            assert result["sentiment"] == "positive"
            assert 7 <= result["score"] <= 10
            assert len(result["emotions"]) > 0

    @pytest.mark.asyncio
    async def test_negative_sentiment(self, negative_text):
        """测试消极情绪识别"""
        from app.ai import analyze_sentiment

        with patch("app.ai.chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (
                '{"sentiment": "negative", "score": 3, "emotions": ["沮丧", "疲惫"]}'
            )

            result = await analyze_sentiment(negative_text)

            assert result["sentiment"] == "negative"
            assert 0 <= result["score"] <= 4
            assert len(result["emotions"]) > 0

    @pytest.mark.asyncio
    async def test_neutral_sentiment(self, neutral_text):
        """测试中性情绪识别"""
        from app.ai import analyze_sentiment

        with patch("app.ai.chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (
                '{"sentiment": "neutral", "score": 5, "emotions": []}'
            )

            result = await analyze_sentiment(neutral_text)

            assert result["sentiment"] == "neutral"
            assert 4 <= result["score"] <= 6

    @pytest.mark.asyncio
    async def test_invalid_json_returns_default(self):
        """测试无效JSON返回默认值"""
        from app.ai import analyze_sentiment

        with patch("app.ai.chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "invalid json response"

            result = await analyze_sentiment("测试文本")

            assert result["sentiment"] == "neutral"
            assert result["score"] == 5
            assert result["emotions"] == []

    @pytest.mark.asyncio
    async def test_empty_text(self):
        """测试空文本"""
        from app.ai import analyze_sentiment

        with patch("app.ai.chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (
                '{"sentiment": "neutral", "score": 5, "emotions": []}'
            )

            result = await analyze_sentiment("")

            assert "sentiment" in result
            assert "score" in result
            assert "emotions" in result


class TestSentimentIntegration:
    """情绪分析集成测试"""

    @pytest.mark.asyncio
    async def test_score_range(self):
        """测试分数范围在0-10"""
        from app.ai import analyze_sentiment

        test_cases = [
            ('{"sentiment": "positive", "score": 0, "emotions": []}', 0),
            ('{"sentiment": "positive", "score": 10, "emotions": []}', 10),
            ('{"sentiment": "positive", "score": 5, "emotions": []}', 5),
        ]

        for response, expected_score in test_cases:
            with patch("app.ai.chat_completion", new_callable=AsyncMock) as mock_chat:
                mock_chat.return_value = response
                result = await analyze_sentiment("测试")
                assert result["score"] == expected_score

    @pytest.mark.asyncio
    async def test_emotions_is_list(self):
        """测试情绪标签是列表"""
        from app.ai import analyze_sentiment

        with patch("app.ai.chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = (
                '{"sentiment": "positive", "score": 7, "emotions": ["开心", "满足"]}'
            )

            result = await analyze_sentiment("今天很开心")

            assert isinstance(result["emotions"], list)
            assert "开心" in result["emotions"]
