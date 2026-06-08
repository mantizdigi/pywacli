from pywacli.ai_engine.providers.base import ModelProviderAbstractClass

from langchain_zhipuai_dev.chat import ChatZhipuAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from pywacli.ai_engine.load_history import LoadHistory


class GLMProvider(ModelProviderAbstractClass):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = LoadHistory.history()

        try:
            self.model = ChatZhipuAI(
                model_name=self.model_name,
                temperature=self.temperature
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
