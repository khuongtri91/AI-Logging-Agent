from langchain_google_genai import ChatGoogleGenerativeAI

from src.utils.config import Settings

class GeminiModel:
    """Wrapper for Google Gemini LLM"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = ChatGoogleGenerativeAI(
            model=self.settings.gemini_api_model,
            google_api_key=self.settings.gemini_api_key,
            temperature=self.settings.temperature
        )
    
    def get_llm(self):
        """Get the LLM instance"""
        return self.llm
    
    def get_llm_with_tools(self, tools: list):
        """Get LLM with tools bound"""
        return self.llm.bind_tools(tools)
