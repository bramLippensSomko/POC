{
    'name': 'POC - Helpdesk AI Ticket Analysis',
    'version': '18.0.1.0.0',
    'author': 'Bram Lippens',
    'category': 'Services/Helpdesk',
    'description': """""",
    'website': 'https://www.somko.be',
    'images': [],
    'depends': ['helpdesk'],
    'data': [
        'security/ir.model.access.csv',

        'data/mock_ticket_data.xml',
        'data/ir_action_data.xml',

        'views/helpdesk_ticket.xml',
        ],
    'qweb': [],
    'demo': [],
    'test': [],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
}