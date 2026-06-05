from langchain_core.prompts import ChatPromptTemplate,MessagePlaceHolder
from pywacli.ai_engine.skill_generator import SkillGenerator


class PromptTempate:
    def __init__(self,prompt_type="personal"):

        self.__prompt_template = ChatPromptTemplate()
        PROMPT_TYPE={
            "personal":self.__call_personal_prompt(),
            "sales":self.__call_sales_prompt(),
            "scheduler":self.__call_scheduler_prompt()
        }
        for type in PROMPT_TYPE.keys():
            if type == prompt_type:
                self.prompt_template = PROMPT_TYPE.get(type)
                break

    def __call_sales_prompt(self):
        return self.__prompt_template.from_messages([
            ("system",SkillGenerator.sales()),
            MessagePlaceHolder(variable_name="history"),
            ("human","{input}")
        ])

    def __call_personal_prompt(self):
        return self.__prompt_template.from_messages([
            ("system",SkillGenerator.personal()),
            MessagePlaceHolder(variable_name="history"),
            ("human","{input}")
        ])

    def __call_scheduler_prompt(self):
        return self.__prompt_template.from_messages([
            ("system",SkillGenerator.scheduler()),
            MessagePlaceHolder(variable_name="history"),
            ("human","{input}")
        ])