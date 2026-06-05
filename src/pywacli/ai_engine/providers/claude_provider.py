from pywacli.ai_engine.providers.base import ModelProviderAbstractClass

from langchain_claude import ChatClaude
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory

from pywacli.ai_engine.load_history import LoadHistory
history = LoadHistory.history()


class ClaudeProvider(ModelProviderAbstractClass):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        try:
            self.model = ChatClaude(
                model=self.model_name,
                temprature = self.temprature
            )
        except Exception as e:
            print(f"Error in {e}")
    
    def generate(self,prompt:ChatPromptTemplate,chat_input):
        model_chain = prompt | self.model | StrOutputParser()
        response = model_chain.invoke({
            "history":history.messages,
            "input":chat_input
        })

        history.add_user_message(chat_input)
        history.add_ai_message(response)

        return response
    