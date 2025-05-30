from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langchain.pydantic_v1 import BaseModel, Field


class SmartnessResult(BaseModel):
    specific: dict
    measurable: dict
    achievable: dict
    relevant: dict
    time_bound: dict


async def get_smartness_chain(api_key):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-pro",
        google_api_key=api_key,
        temperature=0
        )

    prompt_template = """
    Analyze the following ticket according to SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound).
    Return JSON with keys: specific, measurable, achievable, relevant, time_bound, each with a "status" (Met, Not Met, Partially Met) and "reason".

    Title: {subject}
    Text: {description}
    """

    prompt = ChatPromptTemplate.from_template(prompt_template)
    parser = JsonOutputParser(pydantic_object=SmartnessResult)
    return prompt | llm | parser
