import json
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from langchain_ollama import OllamaLLM
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from pydantic import BaseModel
from typing import List, Dict
import requests

app = FastAPI()
llm = OllamaLLM(model="llama3")

template = """
{text}

Return the following JSON:
{{
  "smart": "Yes" or "No",
  "topic": "...",
  "priority": "low" or "medium" or "high",
  "skills": ["skill1", "skill2", ...]
}}
"""

prompt = PromptTemplate(template=template, input_variables=["text"])
chain = LLMChain(llm=llm, prompt=prompt)

embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = FAISS.load_local("faiss_index", embedding, allow_dangerous_deserialization=True)

class PromptInput(BaseModel):
    prompt: str

class TextInput(BaseModel):
    text: str

class TicketUser(BaseModel):
    id: int
    name: str
    skills: List[str]

class TicketRequest(BaseModel):
    ticket_id: int
    subject: str
    description: str
    users: List[TicketUser]


@app.post("/ai-enhance")
def enhance_ticket(input: PromptInput):
    output = chain.run(input.prompt)
    return parse_response(output)

@app.post("/related-tickets")
def related_tickets(input: TextInput):
    docs = vectorstore.similarity_search(input.text, k=3)
    ids = [doc.metadata.get("id") for doc in docs]  # extract IDs from metadata
    return {"ids": ids}

def parse_response(text):
    import re, json
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return json.loads(match.group(0)) if match else {}

def extract_id(text):
    import re
    match = re.search(r"\[ID:(\d+)\]", text)
    return int(match.group(1)) if match else None


def analyze_and_push_back(ticket_id, subject, description, users):
    full_text = f"Subject: {subject}\n\nDescription: {description}"

    smartness_prompt = f"""
        Check if this ticket meets the SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound).
        Respond with 'met' or 'not met' for each.

        {full_text}

        Please respond ONLY with a single JSON object, no explanations, no extra text, formatted exactly as:

        {{
        "specific": "...",
        "measurable": "...",
        "achievable": "...",
        "relevant": "...",
        "time_bound": "..."
        }}
        """

    smartness_result = llm.invoke(smartness_prompt)
    print("smartness_result:", repr(smartness_result))

    # Safely parse smartness_result
    try:
        smartness_data = json.loads(smartness_result) if smartness_result else {}
    except json.JSONDecodeError:
        print("Failed to decode smartness_result as JSON, returning empty dict.")
        smartness_data = {}

    # Check how many criteria were met
    smart_met = sum(1 for v in smartness_data.values() if isinstance(v, str) and v.lower() == "met")
    if smart_met < 3:
        return {
            "smartness": smartness_data,
            "message": "Ticket is not SMART enough. Skipping AI analysis."
        }

    # 2. Vector search for related tickets
    results = vectorstore.similarity_search(full_text, k=3)
    related = [{"text": r.page_content} for r in results]

    # 3. LLM-based classification (category, priority, skill)
    classification_prompt = f"""
        Based on the following helpdesk ticket, predict the category, urgency level, and required skill to solve it.

        Ticket:
        {full_text}

        Please respond ONLY with a single JSON object, no explanations, no extra text, formatted exactly as:
        {{
        "category": "...",
        "priority": "Low | Medium | High | Urgent",
        "required_skill": "..."
        }}
        """
    classification_result = llm.invoke(classification_prompt)
    print("classification_result:", repr(classification_result))
    try:
        classification_data = json.loads(classification_result) if classification_result else {}
    except json.JSONDecodeError:
        print("Failed to decode classification_result as JSON, returning empty dict.")
        classification_data = {}

    # 4. Match user by skill
    required_skill = classification_data.get("required_skill", "").lower()
    matched_user_id = None
    for user in users:
        user_skills = [s.strip().lower() for s in user.get("skills", [])]
        if required_skill and required_skill in user_skills:
            matched_user_id = user["id"]
            break

    result = {
        "params":{
            "smartness": smartness_data,
            "category": classification_data.get("category"),
            "priority": classification_data.get("priority"),
            "required_skill": required_skill,
            "related_tickets": related,
            "suggested_user_id": matched_user_id,
            "ticket_id": ticket_id
        }  
    }

    # Call back Odoo API to update ticket
    odool_url = "http://poc.localhost:9563/helpdesk_ticket/update_ai_analysis"
    odool_api_key = "4c22655765f99122170cfd010a612bf6fa5629cb"
    headers = {"Authorization": f"Bearer {odool_api_key}"}
    print('sending post request')
    response = requests.post(odool_url, json=result, headers=headers)
    if response.ok:
        print(f"Request succeeded with status code {response.status_code}")
        print("Response content:", response.text)
    else:
        print(f"Request failed with status code {response.status_code}")
        print("Response content:", response.text)


@app.post("/analyze_ticket")
def analyze_ticket(data: TicketRequest, background_tasks: BackgroundTasks):
    # Receive the request and start background task
    background_tasks.add_task(
        analyze_and_push_back,
        ticket_id=data.ticket_id,
        subject=data.subject,
        description=data.description,
        users=data.users
    )
    return {"status": "processing", "message": "Ticket analysis started"}

