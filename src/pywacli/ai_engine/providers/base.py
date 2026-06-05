from abc import ABC , abstractmethod
from langchain_core.prompts import ChatPromptTemplate

class ModelProviderAbstractClass(ABC):

    def __init__(self,**kwargs):
        self.model_name=kwargs.get("model_name")
        self.temprature=kwargs.get("temprature")
        self.model=None

    @abstractmethod
    def generate(self,prompt:ChatPromptTemplate)-> str:
        pass
