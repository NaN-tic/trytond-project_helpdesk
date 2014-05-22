# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['Activity']
__metaclass__ = PoolMeta


class Activity:
    __name__ = "activity.activity"

    main_contact = fields.Function(fields.Many2One('party.party',
            'Main Contact', domain=[
                ('id', 'in', Eval('allowed_contacts', [])),
                ], depends=['allowed_contacts']), 'get_main_contact',
                setter='set_main_contact')

    @classmethod
    def __setup__(cls):
        super(Activity, cls).__setup__()
        # Add Internal to activity type
        item = ('internal', 'Internal')
        if item not in cls.type.selection:
            cls.type.selection.append(item)

    def get_main_contact(self, name):
        if self.contacts:
            return self.contacts[0].id

    @classmethod
    def set_main_contact(cls, activities, name, value):
        Contact = Pool().get('activity.activity-party.party')
        contacts = [contact for activity in activities
                    for contact in activity.contacts ]
        Contact.delete(contacts)
        if value:
            to_create = []
            for activity in activities:
                to_create.append({
                        'party': value,
                        'activity': activity.id,
                        })
            Contact.create(to_create)
