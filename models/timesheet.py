import contextlib
from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import Eval, Bool, If
from trytond.transaction import Transaction
import datetime

__all__ = ["Timesheet"]


class Timesheet(ModelSQL, ModelView):
    "AFX Timesheet"

    __name__ = "afx_timesheet.timesheet"

    date = fields.Date("Date", required=True)
    user = fields.Many2One("res.user", "User", required=True,
                          readonly=True, states={'readonly': True})
    project = fields.Many2One("afx.project", "AFX Project")
    task = fields.Many2One(
        "afx.project.task",
        "AFX Project Task",
        domain=[
            If(Bool(Eval("project")), ("project", "=", Eval("project", -1)), ()),
        ],
        depends=["project"],
    )
    detail = fields.Text("Detail")
    so_number = fields.Char("S/O Number")
    time_in = fields.Char("Time In", help="Format: HH:MM")
    time_out = fields.Char("Time Out", help="Format: HH:MM")
    total = fields.Function(
        fields.Char("Total Hours", help="Format: HH:MM"), "on_change_with_total"
    )

    # Search fields
    user_filter = fields.Many2One('res.user', 'User')
    month_filter = fields.Selection([
        ('', ''),
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
    ], 'Month')
    year_filter = fields.Selection([], 'Year')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.year_filter.selection = cls._year_get()

    @staticmethod
    def _year_get():
        today = datetime.date.today()
        return [('', '')] + [(str(y), str(y)) for y in range(today.year - 3, today.year + 1)]

    @classmethod
    def button_search(cls):
        domain = []

        user_filter = Transaction().context.get('user_filter')
        month_filter = Transaction().context.get('month_filter')
        year_filter = Transaction().context.get('year_filter')

        if user_filter:
            domain.append(('user', '=', user_filter))

        if month_filter and year_filter:
            with contextlib.suppress(ValueError, TypeError):
                year = int(year_filter)
                month = int(month_filter)

                start_date = datetime.date(year, month, 1)
                end_date = (
                    datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
                    if month == 12
                    else datetime.date(year, month + 1, 1)
                    - datetime.timedelta(days=1)
                )
                domain.extend([
                    ('date', '>=', start_date),
                    ('date', '<=', end_date),
                ])
        return {
            'domain': domain
        }

    @classmethod
    def button_clear(cls):
        return {
            'user_filter': None,
            'month_filter': '',
            'year_filter': ''
        }

    @classmethod
    def default_date(cls):
        return datetime.date.today()

    @classmethod
    def default_user(cls):
        return Transaction().user

    @fields.depends("time_in", "time_out")
    def on_change_with_total(self, name=None):
        if not (self.time_in and self.time_out):
            return "00:00"

        try:
            time_in_hours, time_in_minutes = map(int, self.time_in.split(":"))
            time_out_hours, time_out_minutes = map(int, self.time_out.split(":"))

            time_in_minutes_total = time_in_hours * 60 + time_in_minutes
            time_out_minutes_total = time_out_hours * 60 + time_out_minutes

            diff_minutes = time_out_minutes_total - time_in_minutes_total
            if diff_minutes < 0:
                diff_minutes += 24 * 60  # Assuming overnight shift

            hours = diff_minutes // 60
            minutes = diff_minutes % 60

            return f"{hours:02d}:{minutes:02d}"
        except (ValueError, AttributeError):
            return "00:00"