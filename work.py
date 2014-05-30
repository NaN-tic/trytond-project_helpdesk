# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If
from trytond.transaction import Transaction

__all__ = ['Work', 'WorkType']
__metaclass__ = PoolMeta


class WorkType:
    __name__ = 'project.work.tracker'

    helpdesk = fields.Boolean('Helpdesk', select=True)

    @staticmethod
    def default_helpdesk():
        return False


class Work:
    __name__ = 'project.work'
    helpdesk = fields.Boolean('Helpdesk', select=True,
        on_change_with=['tracker'])
    activities = fields.One2Many('activity.activity', 'resource',
        'Activities', context={
            'opportunity_party': Eval('party'),
            }, depends=['party'])
    project_remaining_hours = fields.Function(
        fields.Float('Work Remaining Hours', digits=(16, 2)),
        'get_project_remainig_hours')
    attachments = fields.Function(fields.One2Many('ir.attachment', None,
            'Attachments', on_change_with=['activity']),
        'on_change_with_attachments')

    @staticmethod
    def default_helpdesk():
        return False

    @staticmethod
    def default_tracker():
        if Transaction().context.get('helpdesk'):
            Tracker = Pool().get('project.work.tracker')
            tracker = Tracker.search([('helpdesk', '=', True)])
            return tracker and tracker[0].id

    @staticmethod
    def default_project_invoice_method():
        if Transaction().context.get('helpdesk'):
            return 'hours'
        return 'to_decide'

    def on_change_with_helpdesk(self, name=None):
        return self.tracker.helpdesk if self.tracker else None

    def on_change_with_attachments(self, name=None):
        Attachment = Pool().get('ir.attachment')
        attachs = Attachment.search([
                ('resource', 'like', str(self))])
        if attachs:
            attachs = [a.id for a in attachs]
        if self.activities:
            for activity in self.activities:
                activity_attachs = Attachment.search([
                        ('resource', 'ilike', str(activity))])
                if activity_attachs:
                    attachs.extend([a.id for a in activity_attachs])
        return attachs or None

    @classmethod
    def __setup__(cls):
        super(Work, cls).__setup__()
        if not 'helpdesk' in cls.parent.depends:
            cls.parent.depends.append('helpdesk')
            if not cls.parent.domain:
                cls.parent.domain = []
            cls.parent.domain.append(
                If(Eval('helpdesk', False), (
                        ('helpdesk', '=', True),
                        ('type', '=', 'project'),
                        ('state', '!=', 'done'),
                    ), (
                        ('helpdesk', '=', False),
                        ('type', '=', 'project'),
                        ('state', '!=', 'done'),
                    )
                )
            )
        expr_project = ((Eval('type') == 'project') & Eval('helpdesk'))
        expr_helpdesk_task = ((Eval('type') == 'task') & Eval('helpdesk'))
        if 'invisible' in cls.code.states:
            cls.code.states['invisible'] |= expr_project
        else:
            cls.code.states['invisible'] = expr_project
        if 'invisible' in cls.assigned_employee.states:
            cls.assigned_employee.states['invisible'] |= expr_project
        else:
            cls.assigned_employee.states['invisible'] = expr_project
        cls._error_messages.update({
                'invalid_parent': ('Project "%(work)s" can not be created as '
                    'child of "%s(parent)s", Helpdesk Project must be unique'),
                'invalid_helpdesk': ('Helpdesk Task "%(work)s" can not be '
                    'created out of Helpdesk Project "%s(parent)s"'),
                })

    def check_helpdesk_project_creation(self):
        if self.type != 'project':
            return
        if self.helpdesk and self.parent:
            self.raise_user_error('invalid_parent', {
                    'work': self.rec_name,
                    'parent': self.parent.rec_name
                    })

    def check_helpdesk_task_creation(self):
        if self.type != 'task':
            return
        if self.parent and self.parent.helpdesk != self.helpdesk:
            self.raise_user_error('invalid_helpdesk', {
                    'work': self.rec_name,
                    'parent': self.parent.rec_name
                    })

    def get_project_remainig_hours(self, name):
        result = None
        if self.parent:
            result = (self.parent.effort or 0) - (self.parent.hours or 0)
        else:
            result = (self.effort or 0) - (self.hours or 0)
        return result >= 0 and result or None

    @classmethod
    def validate(cls, works):
        super(Work, cls).validate(works)
        for work in works:
            work.check_helpdesk_project_creation()
            work.check_helpdesk_task_creation()
