from trytond.model import ModelSQL, ModelView, fields, Workflow
from trytond.pyson import Eval
from datetime import datetime, timedelta
from trytond.pool import Pool
from trytond.transaction import Transaction

DAYS = [
    ('Sunday', 'Sunday'),
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday')
]

class TimeSheet(ModelSQL, ModelView):
    "TimeSheet"
    __name__ = "afx.module.timesheet"
    _rec_name = "no"

    no = fields.Char("No", readonly=True)
    day = fields.Selection(DAYS, "Day", readonly=True)
    date = fields.Date("Date", required=True)
    task = fields.Text("Task", required=True)
    project_name = fields.Char("Project Name", required=True)
    detail = fields.Text("Detail", required=True)
    s_o_no = fields.Char("S/O No", required=True)
    time_in = fields.Time("Time In", required=True)
    time_out = fields.Time("Time Out", required=True)
    total = fields.Function(fields.Char("Total"), 'get_total_duration')
    user = fields.Many2One('res.user', 'User', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order = [('no', 'ASC')]

    @classmethod
    def default_no(cls):
        return None

    @classmethod
    def default_user(cls):
        return Transaction().user

    @classmethod
    def create(cls, vlist):
        # Also calculate day for all new records
        for values in vlist:
            if 'date' in values and not values.get('day'):
                date_obj = values['date']
                if isinstance(date_obj, str):
                    date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
                day_name = date_obj.strftime('%A')
                values['day'] = day_name

            # Set current user if not provided
            if 'user' not in values:
                values['user'] = Transaction().user

        # Generate sequence number for new records
        sequence = cls.get_next_sequence()
        for values in vlist:
            values['no'] = sequence
            sequence = cls.get_next_sequence(sequence)
        return super().create(vlist)

    @classmethod
    def write(cls, *args):
        """Update day field whenever date is changed"""
        actions = iter(args)
        for records, values in zip(actions, actions):
            if 'date' in values:
                date_obj = values['date']
                if isinstance(date_obj, str):
                    date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
                day_name = date_obj.strftime('%A')
                values['day'] = day_name
        super().write(*args)

    @classmethod
    def get_next_sequence(cls, sequence=None):
        """Generate the next sequence number"""
        if sequence is None:
            if timesheets := cls.search([], order=[('no', 'DESC')], limit=1):
                last_no = timesheets[0].no
                try:
                    # If it's numeric, increment it
                    next_val = int(last_no) + 1
                    return str(next_val).zfill(len(last_no))
                except (ValueError, TypeError):
                    # If not numeric, use timestamp
                    return str(int(datetime.now().timestamp()))
            return '001'  # Start with '001' if no records
        else:
            try:
                next_val = int(sequence) + 1
                return str(next_val).zfill(len(sequence))
            except (ValueError, TypeError):
                return str(int(datetime.now().timestamp()))

    def get_total_duration(self, name):
        """Calculate the duration between time_out and time_in as HH:MM format"""
        if not self.time_in or not self.time_out:
            return '00:00'

        date_obj = datetime.now().date()
        dt_in = datetime.combine(date_obj, self.time_in)
        dt_out = datetime.combine(date_obj, self.time_out)

        if dt_out < dt_in:
            dt_out += timedelta(days=1)

        duration = dt_out - dt_in
        total_hours, remainder = divmod(duration.seconds, 3600)
        total_minutes = remainder // 60

        return f"{total_hours:02d}:{total_minutes:02d}"
