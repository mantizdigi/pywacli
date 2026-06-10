import os

from pywacli.ai_engine.providers.base import ModelProviderAbstractClass

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from pywacli.ai_engine.load_history import LoadHistory


ZHIPUAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


class GLMProvider(ModelProviderAbstractClass):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = LoadHistory.history()

        api_key = os.environ.get("ZHIPUAI_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "ZHIPUAI_API_KEY not set. Run `pywacli --setup` to configure."
            )

        try:
            self.model = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=api_key,
                base_url=ZHIPUAI_BASE_URL,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize GLM: {e}") from e

    def generate(self, prompt: ChatPromptTemplate, chat_input):
        model_chain = prompt | self.model | StrOutputParser()
        response = model_chain.invoke({
            "history": self.history.messages,
            "input": chat_input
        })

        self.history.add_user_message(chat_input)
        self.history.add_ai_message(response)

        return response
