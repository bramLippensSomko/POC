from pydantic import BaseModel, Field, ImportString
from typing import Literal, Optional
import datetime  # Added for potential future use, not strictly required by below model


class TicketAnalysisResult(BaseModel):
    """Structured analysis of a helpdesk ticket based on its subject and description."""
    category: ImportString = Field(
        ...,  # Ellipsis indicates the field is required
        description="The single most relevant category classifying the core issue reported in the ticket."
        )
    priority: Literal['Low', 'Medium', 'High', 'Urgent'] = Field(
        ...,
        description="The estimated urgency level based on keywords (e.g., 'urgent', 'blocker', 'ASAP') and the described impact."
        )
    required_skill: Optional[str] = Field(
        None,  # Default to None if no specific skill is identified
        description="The primary technical skill or knowledge area likely needed to resolve the issue (e.g., Python, Networking, Printer Repair, Windows Admin, Odoo Configuration, Account Management)."
        )
    # Example of an alternative/extension for direct user suggestion:
    # suggested_assignee_email: Optional[str] = Field(
    #    None,
    #    description="If possible, suggest the email address of a specific user best suited based on the required skill or category. Otherwise, leave as null."
    # )

    # Pydantic v2 configuration example (optional, can customize behavior)
    # class Config:
    #     extra = 'ignore' # Ignore extra fields returned by LLM not in the model
