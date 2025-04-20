from trytond.model import ModelSQL, ModelView, fields
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.pyson import Eval
from trytond.pool import Pool
from datetime import time
import datetime
import calendar
import logging
import hashlib
import os

logger = logging.getLogger(__name__)

class UserTimesheet(ModelSQL, ModelView):
    "User Timesheet"
    __name__ = 'afx.user.timesheet'

    # Hardcoded
    MAIN_COMPANY = 1
    UUID_PREFIX = "tsr_"
    ADMIN = "Timesheet Administration"

    year = fields.Selection([], "Year", help='Format: YYYY', required=True, states={
        'readonly': Eval('id', -1) > 0
    }, depends=['id'])
    month = fields.Selection([], "Month", sort=False, required=True, states={
        'readonly': Eval('id', -1) > 0
    }, depends=['id'])
    user = fields.Many2One('company.employee', "User", required=True, domain=[
        ('company', '=', MAIN_COMPANY)
    ])
    records = fields.One2Many('afx.user.timesheet.record', 'timesheet', "Records", required=False, domain=[
        ('date.month', '=', Eval('month'))
    ])

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.year.selection = cls._year_get()
        cls.month.selection = cls._month_get()

    def _year_get():
        today = datetime.date.today()
        # Rule 1: If the month is December, include this year and the previous year
        if today.month == 12:
            years = [(str(today.year - 1), str(today.year - 1)), (str(today.year), str(today.year))]
        # Rule 2: Otherwise, include only this year
        else:
            years = [(str(today.year), str(today.year))]
        # Add the default empty tuple at the beginning
        return [] + years
    
    def _month_get():
        today = datetime.date.today()
        current_month = today.month
        months = [
            ('1', 'JAN'), ('2', 'FEB'), ('3', 'MAR'), ('4', 'APR'),
            ('5', 'MAY'), ('6', 'JUN'), ('7', 'JUL'), ('8', 'AUG'),
            ('9', 'SEP'), ('10', 'OCT'), ('11', 'NOV'), ('12', 'DEC')
        ]
        if current_month == 1:
            result = months[-1:] + months[:current_month]
        else:
            result = months[:current_month]
        return [] + result
    
    # ------- DEFAULT VALUES --------    
    @classmethod
    def default_user(cls):
        if (Transaction().user - 1) < 1:
            return None
        else:
            return Transaction().user
        
    # -------- ONCHANGE METHOD --------
    @fields.depends('month', 'records')
    def on_change_month(self):
        """
        When the month changes, filter the records to only include those
        matching the selected month.
        """
        if self.month:
            # Clear existing records that do not match the selected month
            filtered_records = [
                record for record in self.records
                if record.date and record.date.month == int(self.month)
            ]
            self.records = filtered_records

    # -------- OVERRIDE METHODS --------
    @classmethod
    def search(cls, domain, offset=0, limit=None, order=None, count=False, query=False):
        """
        Override the search method to filter timesheet records based on the logged-in user.
        So the logged-in user only sees timesheet records related to him/her self
        """
        # Get the logged-in user's ID
        user_id = Transaction().user

        # Get required models from pool to get user's group to determine search
        # limitation
        pool = Pool()
        UserGroup = pool.get('res.user-res.group')
        Group = pool.get('res.group')

        current_user_groups = UserGroup.search([
            ('user', '=', user_id)
        ])

        _is_admin = False
        if current_user_groups:
            for user_group in current_user_groups:
                group = Group.search([
                    ('id', '=', user_group.group)
                ])
                if group:
                    if group[0].name == cls.ADMIN:
                        _is_admin = True
        
        if _is_admin == False:
            # Add a condition to filter projects where the user is involved
            domain = [
                ('OR',
                    [('user', '=', user_id)],
                ),
                # *domain  # Preserve any existing domain conditions
            ]
        else:
            domain = []

        return super(UserTimesheet, cls).search(domain, offset=offset, limit=limit, order=order, count=count, query=query)
    
    @classmethod
    def create(cls, record):
        """
        Override the save method to add user timesheet record automatically
        based on selected Month & Year
        """
        data = record[0]
        year = int(data.get('year', None))
        month = int(data.get('month', None))

        new_timesheet = super(UserTimesheet,cls).create(record)
        if new_timesheet:  # Ensure the list is not empty
            timesheet_id = new_timesheet[0].id  # Access the first record's ID
            for date_info in cls.generate_dates_list(year, month):
                pool = Pool()
                UserTimesheetRecord = pool.get('afx.user.timesheet.record')
                # Prepare the data for creating a new UserTimesheetRecord
                random_data = os.urandom(16)
                unique_id = cls.UUID_PREFIX + hashlib.sha256(random_data).hexdigest()
                record_data = {
                    'unique_id': unique_id,         # Create unique_id
                    'timesheet': timesheet_id,      # Link to the newly created timesheet
                    'date': date_info,              # Date from the generated list
                    'day': None,                    # Day name derived from the date
                    'task': '',                     # No task initially
                    'project': None,                # No project initially
                    'detail': '',                   # Optional detail (use None for empty)
                    'so_no': None,                  # Optional S/O Number (use None for empty)
                    'time_in': time(9, 0),          # Set Time In to 9:00 AM
                    'time_out': time(17, 0),        # Set Time Out to 5:00 PM
                    'total': 8.0,                   # Set Total Hours to 8.0
                }
                # Create the UserTimesheetRecord
                UserTimesheetRecord.create([record_data])
        return new_timesheet
    
    @classmethod
    def validate(cls, timesheets):
        super(UserTimesheet, cls).validate(timesheets)
        for timesheet in timesheets:
            cls.check_unique_user_year_month(timesheet)

    @classmethod
    def check_unique_user_year_month(cls, timesheet):
        existing = cls.search([
            ('user', '=', timesheet.user.id),
            ('year', '=', timesheet.year),
            ('month', '=', timesheet.month),
            ('id', '!=', timesheet.id),  # Exclude the current record if editing
        ], limit=1)
        if existing:
            raise UserError(
                "Duplicate Entry",
                f"A timesheet for user '{timesheet.user.name}' already exists "
                f"for the year {timesheet.year} and month {timesheet.month}."
            )

    # -------- UTIL METHODS --------'    
    @staticmethod
    def generate_dates_list(year, month):
        # Get the first and last day of the month
        start_date = datetime.date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime.date(year, month, last_day)
        
        # Generate all dates in the month
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += datetime.timedelta(days=1)
        
        return dates