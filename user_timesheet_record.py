from trytond.model import ModelSQL, ModelView, fields
from datetime import time, datetime, timedelta
from trytond.pool import Pool
import logging

logger = logging.getLogger(__name__)

class UserTimesheetRecord(ModelSQL, ModelView):
    "Timesheet Record"
    __name__ = 'afx.user.timesheet.record'

    unique_id = fields.Char("Uuid")
    timesheet = fields.Many2One('afx.user.timesheet', "Timesheet")
    date = fields.Date("Date", required=True)
    day = fields.Char("Day")
    task = fields.Selection([], "Status", sort=False)
    project = fields.Many2One('afx.project', "Project", domain=[
        ('so_no', '!=', None)
    ])
    detail = fields.Text("Detail")
    so_no = fields.Char(
        "S/O Number",
        help="Automatically filled based on the selected project.",
        on_change_with=['project']  # Trigger computation when project changes
    )
    time_in = fields.Time(
        "Time In", 
        help="Format: HH:MM"
    )
    time_out = fields.Time(
        'Time Out', 
        help='Format: HH:MM'
    )
    total = fields.Float(
        'Total Hours',
        digits=(16, 2),  # Two decimal places
        help="Calculated total hours spent from Time In to Time Out."
    )
    
    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.task.selection = cls._task_get()

    def _task_get():
        tasks = [
            ('',''),
            ('IN_PROJECT', 'In Project'),
            ('LEAVE_ANNUAL', 'Leave - Annual'),
            ('LEAVE_UNPAID', 'Leave - Unpaid'),
            ('LEAVE_HALFDAY', 'Leave - Halfday'),
            ('LEAVE_MEDICAL', 'Leave - Medical'),
            ('LEAVE_MARRIAGE', 'Leave - Marriage'),
            ('LEAVE_PATERNAL', 'Leave - Paternal'),
            ('LEAVE_MATERNITY', 'Leave - Maternity'),
            ('LEAVE_EMERGENCY', 'Leave - Emergency'),
            ('LEAVE_COMPASSIONATE', 'Leave - Compassionate'),
            ('LEAVE_HOSPITALIZATION', 'Leave - Hospitalization'),
        ]
        return [] + tasks

    # -------- DEFAULT METHODS --------
    @staticmethod
    def default_time_in():
        """
        Provide a default value for the Time In field.
        """
        return time(9, 0)  # Default value: 9:00 AM

    @staticmethod
    def default_time_out():
        """
        Provide a default value for the Time Out field.
        """
        return time(17, 0)  # Default value: 5:00 PM
    
    # -------- ONCHANGE METHOD --------
    @fields.depends('task', 'project', 'detail', 'so_no', 'time_in', 'time_out', 'total')
    def on_change_task(self):
        """
        When the task is changed, if it is not 'IN_PROJECT', empty and disable all fields.
        """
        if self.task != 'IN_PROJECT':
            # Reset all fields to their default (empty) state
            self.project = None
            self.detail = None
            self.so_no = None
            self.time_in = None
            self.time_out = None
            self.total = None

    @fields.depends('project')  # Declare dependency on the 'project' field
    def on_change_with_so_no(self, name=None):
        """
        Automatically fill the S/O Number based on the selected project.
        """
        if self.project and self.project.so_no:
            return self.project.so_no
        return None  # Return None if no project is selected or so_no is not se
    
    @fields.depends('time_in', 'time_out')  # Trigger when time_in or time_out changes
    def on_change_time_in(self):
        """
        Calculate total hours when time_in changes.
        """
        self.calculate_total_hours()

    @fields.depends('time_in', 'time_out')  # Trigger when time_in or time_out changes
    def on_change_time_out(self):
        """
        Calculate total hours when time_out changes.
        """
        self.calculate_total_hours()

    # -------- FUNCTION METHODS --------
    def calculate_total_hours(self):
        """
        Calculate the total hours spent from time_in to time_out.
        """
        if self.time_in and self.time_out:
            # Convert time_in and time_out to datetime objects for easier manipulation
            today = datetime.today().date()
            time_in_dt = datetime.combine(today, self.time_in)
            time_out_dt = datetime.combine(today, self.time_out)

            # Handle cases where time_out is on the next day (e.g., working past midnight)
            if time_out_dt < time_in_dt:
                time_out_dt += timedelta(days=1)

            # Calculate the difference in hours
            delta = time_out_dt - time_in_dt
            total_seconds = delta.total_seconds()
            total_hours = total_seconds / 3600  # Convert seconds to hours

            # Round to two decimal places
            self.total = round(total_hours, 2)
        else:
            self.total = 0.0  # Reset total if either time_in or time_out is mis

    # -------- OVERRIDE METHODS --------
    @classmethod
    def write(cls, records, values, *args):
        """
        Override the write method to handle creation of ProjectMember and ProjectTask records.
        """
        pool = Pool()
        ProjectMember = pool.get('afx.project.member')
        ProjectTask = pool.get('afx.project.task')

        # Call the super method to ensure the write operation is performed
        super(UserTimesheetRecord, cls).write(records, values, *args)

        for record in records:
            if record.unique_id:
                # Check if the 'project' field has been updated and has a value
                if record.project:
                    project_id = record.project
                    # Get the user from the timesheet field
                    user = record.timesheet.user if record.timesheet else None
                    if not user:
                        logger.warning("No user found for timesheet record")
                        continue

                    # Step 1: Check if a ProjectMember record already exists for the user and project
                    existing_project_member = ProjectMember.search([
                        ('project', '=', project_id),
                        ('member', '=', user.id),
                    ])
                    if existing_project_member:
                        # Use the existing ProjectMember record
                        project_member = existing_project_member[0]
                    else:
                        # Create a new ProjectMember record
                        project_member_values = {
                            'project': project_id,
                            'member': user.id,
                            'role': 'Default Role',  # You can adjust this as needed
                            'rate': 0,  # Default rate, adjust as needed
                            'est_start_date': record.date,  # Use the date from the timesheet record
                            'est_end_date': record.date,  # Use the same date for simplicity
                        }
                        project_member, = ProjectMember.create([project_member_values])

                    # Step 2: Check if a ProjectTask record with the same unique_id already exists
                    try:
                        project_task = None
                        existing_project_task = ProjectTask.search([
                            ('unique_id', '=', record.unique_id)
                        ])
                        if existing_project_task:
                            # Update the existing ProjectTask record
                            project_task = existing_project_task[0]  # Assign the existing record to project_task
                            project_task_values = {
                                'project': project_id,
                                'activity': record.detail,
                                'pic': project_member.id,
                                'start_time': record.time_in,
                                'end_time': record.time_out,
                                'total_hours': record.total,
                                'priority': 'medium',
                                'status': 'to_do',
                            }
                            ProjectTask.write([project_task], project_task_values)
                        if not existing_project_task:
                            # Create a new ProjectTask record
                            project_task_values = {
                                'unique_id': record.unique_id,
                                'project': project_id,
                                'activity': record.detail,
                                'pic': project_member.id,
                                'start_time': record.time_in,
                                'end_time': record.time_out,
                                'total_hours': record.total,
                                'priority': 'medium',
                                'status': 'to_do',
                            }
                            project_task, = ProjectTask.create([project_task_values])  # Assign the newly created record to project_task
                            # Ensure project_task is always defined before proceeding
                            if 'project_task' not in locals():
                                logger.error(f"Failed to create or update ProjectTask for record {record.id}")
                                continue
                    except Exception as e:
                        # Log the exception and continue processing other records
                        logger.error(f"An error occurred while processing record {record.id}: {str(e)}")
                        continue
                else:
                    existing_project_task = ProjectTask.search([
                        ('unique_id', '=', record.unique_id)
                    ])
                    if existing_project_task:
                        ProjectTask.delete(existing_project_task)

        return True