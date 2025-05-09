from odoo import models, fields, api, _, exceptions
import os
from dotenv import load_dotenv

import logging

from odoo.addons.custom_helpdesk_ai.services.llm_connection import get_ai_analysis_chain, invoke_ai_analysis

_logger = logging.getLogger(__name__)

load_dotenv()

llm_api_key = os.environ.get("OPENAI_API_KEY")

if not llm_api_key:
    # Log an error or raise a configuration exception
    _logger.error("LLM API Key not found in environment variables.")


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

    def run_ai_ticket_analysis(self):
        """
        Runs the AI analysis on the ticket description and returns the structured result.
        This method is designed to be called by a server action or button.
        Returns: A dictionary representation of TicketAnalysisResult or None if analysis fails.
        """
        self.ensure_one()
        analysis_result_dict = None
        _logger.info(f"Starting AI analysis for ticket ID {self.id} ('{self.name}')")

        chain = self._get_cached_ai_analysis_chain()
        if not chain:
            _logger.error(f"AI analysis chain unavailable for ticket {self.id}.")
            raise exceptions.UserError("AI Analysis Service is not configured or unavailable.")

        # Invoke the analysis using the helper function
        analysis_pydantic_obj = invoke_ai_analysis(chain, self.name, self.description)

        if analysis_pydantic_obj:
            # Convert Pydantic object to dictionary for easier handling in Odoo
            analysis_result_dict = analysis_pydantic_obj.dict()
            _logger.info(f"AI analysis successful for ticket {self.id}. Raw results: {analysis_result_dict}")
            self.ai_category = analysis_result_dict.get('category')
            self.ai_priority = analysis_result_dict.get('priority')
            self.ai_required_skill = analysis_result_dict.get('required_skill')
        else:
            # Error logging already happened within invoke_ai_analysis
            _logger.warning(f"AI analysis did not return results for ticket {self.id}.")
            raise exceptions.UserError("AI Analysis failed to produce results for this ticket.")

    def action_analyze_ticket_and_update(self):
        """Button action or server action target to run analysis and update the ticket."""
        for ticket in self:
            analysis_data = ticket.run_ai_ticket_analysis()
            if analysis_data:
                update_vals = {}
                # --- Mapping Logic ---
                # Simple mapping for selection fields assuming values match
                if analysis_data.get('category'):
                    update_vals['ai_category'] = analysis_data['category']
                if analysis_data.get('priority') in dict(self._fields['ai_priority'].selection):
                    update_vals['ai_priority'] = analysis_data['priority']
                if analysis_data.get('required_skill'):
                    update_vals['ai_required_skill'] = analysis_data['required_skill']

                # Example: Find suggested user based on skill (requires users to have skills defined)
                # This is a simplified example; real logic might be more complex
                # if analysis_data.get('required_skill'):
                #    # Assuming a 'skill_ids' Many2many field on res.users and a 'res.skill' model
                #    skill_name = analysis_data.get('required_skill')
                #    # Search for users with that skill, perhaps prioritizing by availability/workload
                #    suggested_user = self.env['res.users'].search([('skill_ids.name', '=ilike', skill_name)], limit=1)
                #    if suggested_user:
                #        update_vals['ai_suggested_user_id'] = suggested_user.id
                #        _logger.info(f"Suggested assignee for ticket {ticket.id}: {suggested_user.name}")

                if update_vals:
                    try:
                        ticket.write(update_vals)
                        _logger.info(f"Ticket {ticket.id} updated with AI analysis: {update_vals}")
                        ticket.message_post(body=f"AI Analysis Completed: Category='{update_vals.get('ai_category', 'N/A')}', Priority='{update_vals.get('ai_priority', 'N/A')}', Skill='{update_vals.get('ai_required_skill', 'N/A')}'")
                    except Exception as e:
                        _logger.error(f"Failed to write AI analysis results to ticket {ticket.id}: {e}", exc_info=True)
                else:
                    _logger.info(f"No valid update values derived from AI analysis for ticket {ticket.id}.")
            else:
                _logger.warning(f"AI Analysis failed or returned no data for ticket {ticket.id}, skipping update.")
