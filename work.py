# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If, And
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
    contract = fields.Many2One('contract.contract', 'Contract',
        domain=[('party', '=', Eval('party')), ('state', '!=', 'draft')],
        states={
            'required': And(Eval('type') == 'project',
                Eval('helpdesk', False)),
            'invisible': Eval('type') != 'project',
            }, depends=['type', 'helpdesk', 'party'])

    @staticmethod
    def default_helpdesk():
        return False

    @staticmethod
    def default_tracker():
        if Transaction().context.get('helpdesk'):
            Tracker = Pool().get('project.work.tracker')
            tracker = Tracker.search([('helpdesk', '=', True)])
            return tracker and tracker[0].id

    def on_change_with_helpdesk(self, name=None):
        return self.tracker.helpdesk if self.tracker else None

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
                        ('type', '=', 'project')
                    ), (
                        ('helpdesk', '=', False),
                        ('type', '=', 'project')
                    )
                )
            )
        expr_project = ((Eval('type') == 'project') & Eval('helpdesk'))
        expr_task = ((Eval('type') == 'task') & Eval('helpdesk'))
        if 'invisible' in cls.code.states:
            cls.code.states['invisible'] |= expr_project
        else:
            cls.code.states['invisible'] = expr_project
        if 'invisible' in cls.assigned_employee.states:
            cls.assigned_employee.states['invisible'] |= expr_project
        else:
            cls.assigned_employee.states['invisible'] = expr_project
        if 'required' in cls.assigned_employee.states:
            cls.assigned_employee.states['required'] |= expr_task
        else:
            cls.assigned_employee.states['required'] = expr_task
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

    @classmethod
    def validate(cls, works):
        super(Work, cls).validate(works)
        for work in works:
            work.check_helpdesk_project_creation()
            work.check_helpdesk_task_creation()
