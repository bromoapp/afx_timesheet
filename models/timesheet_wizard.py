from datetime import date
from dateutil.relativedelta import relativedelta
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import PYSONEncoder
import time

__all__ = ['TimesheetMonthlyContext', 'TimesheetMonthly']


class TimesheetMonthlyContext(ModelView):
    "Timesheet Monthly Selection"
    __name__ = 'afx_timesheet.timesheet.monthly.context'

    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], 'Month', required=True)
    year = fields.Selection([], 'Year', required=True)

    @classmethod
    def default_month(cls):
        today = date.today()
        return str(today.month)

    @classmethod
    def default_year(cls):
        today = date.today()
        return str(today.year)

    @staticmethod
    def year_get():
        today = date.today()
        return [(str(y), str(y)) for y in range(today.year - 1, today.year + 1)]

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.year.selection = cls.year_get()


class TimesheetMonthly(Wizard):
    "Timesheet Monthly"
    __name__ = 'afx_timesheet.timesheet.monthly'

    start = StateView('afx_timesheet.timesheet.monthly.context',
        'afx_timesheet.timesheet_monthly_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'open_', 'tryton-ok', default=True),
        ])
    open_ = StateAction('afx_timesheet.act_timesheet_month_list')

    def do_open_(self, action):
        year = int(self.start.year)
        month = int(self.start.month)

        # Calculate start and end dates for the selected month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - relativedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - relativedelta(days=1)

        # Set domain to filter by date range
        domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ]

        # Clone the action to avoid modifying the original
        action = action.copy()

        # Generate unique timestamp for this specific instance
        timestamp = int(time.time() * 1000)

        # Get month name for display
        month_name = dict(self.start.__class__.month.selection)[self.start.month]
        title = f"Timesheets - {month_name} {self.start.year}"

        # Update action with domain
        action['pyson_domain'] = PYSONEncoder().encode(domain)
        action['domain'] = domain

        # Set unique action properties to force UI refresh
        action['name'] = title
        action['display_name'] = title  # Explicitly set display_name for navbar
        action['res_id'] = None  # Ensure we're viewing list, not specific record
        action['window_title'] = title  # Set window title explicitly

        # Create unique action ID by adding timestamp
        action['id'] = f"{action['id']}_{timestamp}"

        # Set context to refresh UI and bypass caching
        action['context'] = {
            'no_filter': True,
            '_timestamp': timestamp,
            'title': title,  # Add title to context
            'active_year': year,
            'active_month': month,
        }
        action['search_value'] = ''

        # Add unique keyword for tab identification
        action['keyword'] = f"timesheet_monthly_{month}_{year}_{timestamp}"

        print('action:', action)

        # Return with reload flag to force UI refresh
        return action, {'reload': True}
