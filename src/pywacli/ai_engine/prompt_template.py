from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pywacli.ai_engine.skill_generator import SkillGenerator


class PromptTempate:
    def __init__(self, prompt_type="personal"):

        PROMPT_TYPE = {
            "personal": self.__build_prompt(SkillGenerator.personal),
            "sales": self.__build_prompt(SkillGenerator.sales),
            "scheduler": self.__build_prompt(SkillGenerator.scheduler),
            "customer_support": self.__build_prompt(SkillGenerator.customer_support),
            "translator": self.__build_prompt(SkillGenerator.translator),
            "summarizer": self.__build_prompt(SkillGenerator.summarizer),
            "content_writer": self.__build_prompt(SkillGenerator.content_writer),
            "lead_qualifier": self.__build_prompt(SkillGenerator.lead_qualifier),
            "appointment_booking": self.__build_prompt(SkillGenerator.appointment_booking),
            "order_tracking": self.__build_prompt(SkillGenerator.order_tracking),
            "faq_bot": self.__build_prompt(SkillGenerator.faq_bot),
        }

        self.prompt_template = PROMPT_TYPE.get(prompt_type)
        if self.prompt_template is None:
            available = ", ".join(PROMPT_TYPE.keys())
            raise ValueError(
                f"Invalid prompt_type '{prompt_type}'. Available: {available}"
            )

    @staticmethod
    def __build_prompt(skill_fn):
        return ChatPromptTemplate.from_messages([
            ("system", skill_fn()),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
