# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .work import *
from .activity import *

def register():
    Pool.register(
        Activity,
        Work,
        WorkType,
        module='project_helpdesk', type_='model')
