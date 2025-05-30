import json

from odoo import models, fields, api, _, exceptions
import requests
import os
from dotenv import load_dotenv
import asyncio

import logging

from odoo.addons.custom_helpdesk_ai.services.llm_connection import get_ai_analysis_chain, invoke_ai_analysis
from odoo.addons.custom_helpdesk_ai.services.smartness_chain import get_smartness_chain

_logger = logging.getLogger(__name__)

load_dotenv()

llm_api_key = os.environ.get("OPENAI_API_KEY")

if not llm_api_key:
    # Log an error or raise a configuration exception
    _logger.error("LLM API Key not found in environment variables.")


def call_local_llm_api(subject, description, user_data):
    try:
        response = requests.post(
            "http://localhost:1234/analyze_ticket",
            json={
                "subject": subject,
                "description": description,
                "users": user_data,
                },
            timeout=10,
            )
        return response.json()
    except Exception as e:
        _logger.error(f"LLM API call failed: {e}")
        return None


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    ai_category = fields.Text(string='AI Category', readonly=True, tracking=True)
    ai_priority = fields.Selection([
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent')], string='AI Priority', readonly=True, tracking=True)
    ai_required_skill = fields.Char(string='AI Required Skill', readonly=True, tracking=True)
    ai_suggested_user_id = fields.Many2one('res.users', string='AI Suggested Assignee', readonly=True, tracking=True)
    ai_related_tickets = fields.Text(string="AI Related Tickets", tracking=True, readonly=True)

    # --- Cached Langchain Chain ---
    _ai_analysis_chain = None

    @api.model
    def _get_cached_ai_analysis_chain(self):
        """Gets or initializes the Langchain chain, caching it at the model level."""
        if HelpdeskTicket._ai_analysis_chain is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                HelpdeskTicket._ai_analysis_chain = get_ai_analysis_chain(api_key)
            else:
                _logger.error("Cannot initialize AI chain: OPENAI_API_KEY not set.")
                # Prevent repeated attempts if key is missing
                HelpdeskTicket._ai_analysis_chain = False
        return HelpdeskTicket._ai_analysis_chain if HelpdeskTicket._ai_analysis_chain else None

    def run_full_ai_ticket_analysis(self):
        self.ensure_one()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise exceptions.UserError("Missing API key for Gemini.")

        # --- Step 1: SMART analysis ---
        smart_chain = asyncio.run(get_smartness_chain(api_key))
        try:
            smart_result = smart_chain.invoke({
                "subject": self.name or "",
                "description": self.description or "",
                })
            # You can persist or log smart_result if desired
        except Exception as e:
            _logger.warning(f"SMART analysis failed: {e}")
            return  # Skip further analysis

        # --- Check SMARTness ---
        met_count = sum(
            1 for k, v in smart_result.dict().items()
            if v['status'].lower() == 'met'
            )
        if met_count < 3:
            _logger.info(f"Ticket {self.id} is not SMART enough (only {met_count}/5 criteria met). Skipping AI assignment.")
            return

        # --- Step 2: Standard AI analysis ---
        users = self.team_id.member_ids
        user_data = [
            {
                "id": user.id,
                "name": user.name,
                "skills": [s.strip() for s in (user.skills or "").lower().split(",") if s.strip()]
                }
            for user in users if user.skills
            ]

        chain = self._get_cached_ai_analysis_chain()
        result = invoke_ai_analysis(chain, self.name, self.description, user_data)

        if not result:
            return

        update_vals = {
            'ai_category': result.get('category'),
            'ai_priority': result.get('priority'),
            'ai_required_skill': result.get('required_skill'),
            }

        # --- Step 3: Auto-assign based on skill ---
        if result.get("required_skill"):
            candidates = self.env['res.users'].search([])  # Later filter by skill
            for user in candidates:
                if result["required_skill"].lower() in (user.groups_id.mapped('name') + [user.name.lower()]):
                    update_vals['ai_suggested_user_id'] = user.id
                    break

        self.write(update_vals)
        self.message_post(body=f"AI Analysis completed. SMART ticket.\nAssigned values: {update_vals}")

    def action_analyze_ticket_and_update(self):
        for ticket in self:
            users_data = [{
                "id": user.id,
                "name": user.name,
                "skills": [s.strip() for s in (user.skills or "").lower().split(",") if s.strip()]
                } for user in ticket.team_id.member_ids if user.skills]

            payload = {
                "ticket_id": ticket.id,
                "subject": ticket.name or "",
                "description": ticket.description or "",
                "users": users_data
                }

            # Fire-and-forget call to FastAPI
            try:
                requests.post("http://172.17.0.1:1234/analyze_ticket", json=payload, timeout=2)
                ticket.message_post(body="🧠 AI analysis request sent. Processing in background.")
            except Exception as e:
                _logger.error(f"Failed to send AI analysis request for ticket {ticket.id}: {e}")
                ticket.message_post(body="❌ Failed to send AI analysis request.")



    # def action_analyze_ticket_and_update(self):
    #     for ticket in self:
    #         try:
    #             # Prepare payload for API
    #             users_data = [
    #                 {
    #                     "id": user.id,
    #                     "name": user.name,
    #                     "skills": [s.strip() for s in (user.skills or "").lower().split(",") if s.strip()]
    #                     }
    #                 for user in ticket.team_id.member_ids if user.skills
    #                 ]
    #
    #             payload = {
    #                 "subject": ticket.name or "",
    #                 "description": ticket.description or "",
    #                 "users": users_data
    #                 }
    #
    #             # Call your FastAPI server (adjust URL if needed)
    #             response = requests.post("http://172.17.0.1:1234/analyze_ticket", json=payload)
    #             response.raise_for_status()
    #             result = response.json()
    #
    #             update_vals = {
    #                 'ai_category': result.get('category'),
    #                 'ai_priority': result.get('priority'),
    #                 'ai_required_skill': result.get('required_skill'),
    #                 'ai_related_tickets': json.dumps(result.get('related_tickets', [])),
    #                 }
    #
    #             # Suggested user logic...
    #
    #             ticket.write(update_vals)
    #
    #             # Post message with a snippet of related tickets
    #             related_preview = "\n".join(r['text'] for r in result.get('related_tickets', [])[:3])
    #             ticket.message_post(
    #                 body=(
    #                     f"🧠 AI Analysis completed:<br/>"
    #                     f"📂 Category: {update_vals.get('ai_category') or 'N/A'}<br/>"
    #                     f"⚡ Priority: {update_vals.get('ai_priority') or 'N/A'}<br/>"
    #                     f"🛠️ Skill: {update_vals.get('ai_required_skill') or 'N/A'}<br/>"
    #                     f"👤 Suggested: {ticket.ai_suggested_user_id.name if ticket.ai_suggested_user_id else 'N/A'}<br/>"
    #                     f"🔗 Related Tickets:<br/><pre>{related_preview}</pre>"
    #                 )
    #                 )
    #
    #         except requests.exceptions.RequestException as e:
    #             _logger.error(f"Failed to call AI API for ticket {ticket.id}: {e}", exc_info=True)
    #             ticket.message_post(body="❌ AI Analysis failed due to API error.")