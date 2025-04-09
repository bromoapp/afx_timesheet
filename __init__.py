# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from .afx_timesheet import TimeSheet


__all__ = ['register']

def register():
    Pool.register(
        TimeSheet,
        module='afx_timesheet', type_='model')
    Pool.register(
        module='afx_timesheet', type_='wizard')
    Pool.register(
        module='afx_timesheet', type_='report')
