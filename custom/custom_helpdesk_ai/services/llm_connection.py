# This code would typically reside in a utility function or within the Odoo model method
import logging

from openai import RateLimitError
import time

# from langchain_openai import ChatOpenAI
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException  # For error handling
from langchain.pydantic_v1 import BaseModel, Field

_logger = logging.getLogger(__name__)


class TicketAnalysisResult(BaseModel):
    category: str
    priority: str
    required_skill: str | None = None  # Can be optional/null


def get_ai_analysis_chain(api_key):
    """Returns an AI analysis chain using Gemini, wrapped with asyncio."""
    try:
        return asyncio.run(_get_ai_analysis_chain_async(api_key))
    except Exception as e:
        _logger.error(f"Failed to initialize Gemini AI analysis chain: {e}", exc_info=True)
        return None


async def _get_ai_analysis_chain_async(api_key):
    if not api_key:
        _logger.error("API Key not provided for Gemini.")
        return None

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=api_key,
        temperature=0
        )

    prompt_template = """Analyze the following helpdesk ticket subject and description. Based *only* on the provided text, determine the most appropriate category, estimate the priority level, and identify the primary technical skill likely required for resolution.

Subject: {subject}
Description: {description}

Return only a JSON object with the following structure:
{{ 
  "category": "...",
  "priority": "...",
  "required_skill": "..."  // or null if not known
}}"""

    prompt = ChatPromptTemplate.from_template(prompt_template)
    parser = JsonOutputParser(key=None)
    chain = prompt | llm | parser
    return chain


def invoke_ai_analysis(chain, ticket_subject, ticket_description, retries=5, delay=5):
    """Invokes the Langchain chain and handles potential errors with retry logic."""
    if not chain:
        _logger.error("AI analysis chain is not available.")
        return None
    if not ticket_description:
        _logger.warning("Cannot run AI analysis: Ticket description is empty.")
        return None

    attempt = 0
    while attempt < retries:
        try:
            _logger.info(f"Invoking AI analysis chain... Attempt {attempt + 1}")
            result = chain.invoke({
                "subject": ticket_subject or "",  # Handle potentially empty subject
                "description": ticket_description
            })

            _logger.info(f"AI analysis successful. Result: {result}")
            return result  # The result is a Pydantic object (TicketAnalysisResult)

        except RateLimitError as e:
            _logger.warning(f"Rate limit hit on attempt {attempt + 1}. Retrying in {delay} seconds...")
            time.sleep(delay)

        except OutputParserException as e:
            _logger.error(f"Error parsing LLM output: {e}", exc_info=True)
            return None  # Don't retry on parse errors

        except Exception as e:
            _logger.error(f"Unexpected error on attempt {attempt + 1}: {e}", exc_info=True)

        attempt += 1

    _logger.error("Exceeded maximum number of retries for AI analysis.")
    return None


# --- Example Usage (Conceptual - would be called from Odoo method) ---
# my_chain = get_ai_analysis_chain(llm_api_key)
# if my_chain:
#    analysis_pydantic_obj = invoke_ai_analysis(my_chain, "Subject", "Description...")
#    if analysis_pydantic_obj:
#        analysis_dict = analysis_pydantic_obj.dict() # Convert to dictionary if needed
#        print(analysis_dict)
