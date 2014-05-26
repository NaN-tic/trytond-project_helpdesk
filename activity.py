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
        cls._error_messages.update({
                'missing_party': ('You have selected to create a task, in this'
                ' case you have to specify the party.'),
                })

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

    @classmethod
    def create_resource_task(cls, vals, model, activity=None):
        party = vals.get('party') or (activity and activity.party and
            activity.party.id) or None
        subject = vals.get('subject') or (activity and activity.subject) or ""
        description = vals.get('description') or (activity and
            activity.description) or ""
        employee = vals.get('employee') or (activity and activity.employee and
            activity.employee.id) or None
        if not party:
            cls.raise_user_error('missing_party')
        Work = Pool().get(model)
        project = Work.search([
                ('party', '=', party),
                ('helpdesk', '=', True),
                ('type', '=', 'project'),
                ], order=[])
        if project:
            Tracker = Pool().get('project.work.tracker')
            tracker = Tracker.search([('helpdesk', '=', True)])
            task_vals = {
                'timesheet_work_name': subject,
                'problem': description,
                'parent': project[0].id,
                'party': party,
                'assigned_employee': employee,
                'tracker': tracker and tracker[0].id or None,
                'helpdesk': True,
                'type': 'task',
                'project_invoice_method': 'hours',
            }
            task = Work.create([task_vals])
            new_id = str(task[0].id)
            return "%s,%s" % (model, new_id)
        return False

    @classmethod
    def create(cls, vlist):
        for vals in vlist:
            if vals.get('resource'):
                model, id = vals['resource'].split(',')
                if model == 'project.work' and id == '-1':
                    resource = cls.create_resource_task(vals, model)
                    if resource:
                        vals['resource'] = resource
        return super(Activity, cls).create(vlist)

    @classmethod
    def write(cls, activities, vals):
        super(Activity, cls).write(activities, vals)
        if vals.get('resource'):
            model, id = vals['resource'].split(',')
            if model == 'project.work' and id == '-1':
                for activity in activities:
                    resource = cls.create_resource_task(vals, model, activity)
                    if resource:
                        vals['resource'] = resource
                        super(Activity, cls).write([activity], vals)
                return
        return super(Activity, cls).write(activities, vals)
