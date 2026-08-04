from types import SimpleNamespace

from src.model import gemini


class FakeChatGoogleGenerativeAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def bind_tools(self, tools):
        return {"bound_tools": tools}


def test_gemini_model_initializes_llm(monkeypatch):
    monkeypatch.setattr(gemini, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI)
    settings = SimpleNamespace(
        gemini_api_model="gemini-test",
        gemini_api_key="test-key",
        temperature=0.1,
    )

    model = gemini.GeminiModel(settings)

    assert model.get_llm().kwargs == {
        "model": "gemini-test",
        "google_api_key": "test-key",
        "temperature": 0.1,
    }
    assert model.get_llm_with_tools(["tool"]) == {"bound_tools": ["tool"]}
