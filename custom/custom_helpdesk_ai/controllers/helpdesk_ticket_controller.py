import json
import logging

from odoo import http

_logger = logging.getLogger(__name__)


class HelpdeskTicketController(http.Controller):

    @http.route('/helpdesk_ticket/update_ai_analysis', type='json', auth='bearer', methods=['POST'])
    def update_ai_analysis(self, **kwargs):
        _logger.info("Received AI analysis update request with data: %s", kwargs)

        ticket_id = kwargs.get('ticket_id')
        category = kwargs.get('category')
        priority = kwargs.get('priority')
        required_skill = kwargs.get('required_skill')
        suggested_user_id = kwargs.get('suggested_user_id')
        related_tickets = kwargs.get('related_tickets')

        if not ticket_id:
            _logger.error("Missing ticket_id in the request payload.")
            return {'error': 'Missing ticket_id'}

        ticket = http.request.env['helpdesk.ticket'].sudo().browse(ticket_id)
        if not ticket.exists():
            _logger.error("Ticket with ID %s not found.", ticket_id)
            return {'error': 'Ticket not found'}

        update_vals = {
            'ai_category': category,
            'ai_priority': priority,
            'ai_required_skill': required_skill,
            'ai_related_tickets': json.dumps(related_tickets),
            'ai_suggested_user_id': suggested_user_id,
            }
        _logger.debug("Updating ticket %s with values: %s", ticket_id, update_vals)

        try:
            ticket.write(update_vals)
            ticket.message_post(body="🧠 AI Analysis updated via webhook.")
            _logger.info("Successfully updated ticket %s with AI analysis.", ticket_id)
        except Exception as e:
            _logger.exception("Failed to update ticket %s: %s", ticket_id, str(e))
            return {'error': 'Failed to update ticket'}

        return {'status': 'success'}
