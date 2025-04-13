# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from . import models

__all__ = ['register']


def register():
    Pool.register(
        models.timesheet.Timesheet,
        models.timesheet_wizard.TimesheetMonthlyContext,
        module='afx_timesheet', type_='model')
    Pool.register(
        models.timesheet_wizard.TimesheetMonthly,
        module='afx_timesheet', type_='wizard')
