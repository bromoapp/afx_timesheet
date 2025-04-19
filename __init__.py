# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from . import user_timesheet
from . import user_timesheet_record

def register():
    Pool.register(
        user_timesheet.UserTimesheet,
        user_timesheet_record.UserTimesheetRecord,
        module='afx_timesheet', type_='model')
    # Pool.register(
    #     module='afx_timesheet', type_='wizard')
    # Pool.register(
    #     module='afx_timesheet', type_='report')
