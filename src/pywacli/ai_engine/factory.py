
class AIEngineFactory:

    @staticmethod
    def create(provider, **kwargs):
        from pywacli.cli.config_manager import load_ai_provider_keys
        load_ai_provider_keys()

        if provider == "ollama":
            from pywacli.ai_engine.providers.ollama_provider import OllamaProvider
            return OllamaProvider(**kwargs)

        elif provider == "openai":
            from pywacli.ai_engine.providers.openai_provider import OpenAIProvider
            return OpenAIProvider(**kwargs)

        elif provider == "gemini":
            from pywacli.ai_engine.providers.gemini_provider import GeminiProvider
            return GeminiProvider(**kwargs)

        elif provider == "claude":
            from pywacli.ai_engine.providers.claude_provider import ClaudeProvider
            return ClaudeProvider(**kwargs)

        elif provider == "glm":
            from pywacli.ai_engine.providers.glm_provider import GLMProvider
            return GLMProvider(**kwargs)

        else:
            raise ValueError("Invalid provider")

    @staticmethod
    def create_prompt(prompt_type):
        from pywacli.ai_engine.prompt_template import PromptTempate
        return PromptTempate(prompt_type=prompt_type)
