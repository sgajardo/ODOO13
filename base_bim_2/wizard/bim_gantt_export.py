import base64
from collections import OrderedDict

from bs4 import BeautifulSoup
from odoo import fields, models
from odoo.exceptions import ValidationError

MS_HEADER_FIELDS = OrderedDict(**{
    'SaveVersion': '14',
    'BuildNumber': '16.0.12624.20466',
    'Name': 'Gantt set1 microsoft project.xml',  # Nombre archivo
    'GUID': '320E2183-1799-EA11-A631-20CF30D8DAF5',  # vaya a sabe como lo genero
    'Title': 'Proyecto1',  # Nombre proyecto
    'CreationDate': '2020-05-18T09:00:00',  # fecha creación
    'LastSaved': '2020-05-18T16:17:00',  # fecha modificación
    'ScheduleFromStart': '1',
    'StartDate': '2020-05-18T09:00:00',  # fechas del proyecto
    'FinishDate': '2020-05-27T18:00:00',  # fechas del proyecto
    'FYStartDate': '1',
    'CriticalSlackLimit': '0',
    'CurrencyDigits': '2',
    'CurrencySymbol': '€',
    'CurrencyCode': 'EUR',
    'CurrencySymbolPosition': '3',
    'CalendarUID': '1',
    'DefaultStartTime': '08:00:00',
    'DefaultFinishTime': '19:00:00',
    'MinutesPerDay': '540',
    'MinutesPerWeek': '2400',
    'DaysPerMonth': '20',
    'DefaultTaskType': '0',
    'DefaultFixedCostAccrual': '3',
    'DefaultStandardRate': '0',
    'DefaultOvertimeRate': '0',
    'DurationFormat': '7',
    'WorkFormat': '2',
    'EditableActualCosts': '0',
    'HonorConstraints': '0',
    'InsertedProjectsLikeSummary': '1',
    'MultipleCriticalPaths': '0',
    'NewTasksEffortDriven': '0',
    'NewTasksEstimated': '1',
    'SplitsInProgressTasks': '1',
    'SpreadActualCost': '0',
    'SpreadPercentComplete': '0',
    'TaskUpdatesResource': '1',
    'FiscalYearStart': '0',
    'WeekStartDay': '1',
    'MoveCompletedEndsBack': '0',
    'MoveRemainingStartsBack': '0',
    'MoveRemainingStartsForward': '0',
    'MoveCompletedEndsForward': '0',
    'BaselineForEarnedValue': '0',
    'AutoAddNewResourcesAndTasks': '1',
    'CurrentDate': '2020-05-18T09:00:00',
    'MicrosoftProjectServerURL': '1',
    'Autolink': '0',
    'NewTaskStartDate': '0',
    'NewTasksAreManual': '1',
    'DefaultTaskEVMethod': '0',
    'ProjectExternallyEdited': '0',
    'ExtendedCreationDate': '1984-01-01T00:00:00',
    'ActualsInSync': '0',
    'RemoveFileProperties': '0',
    'AdminProject': '0',
    'UpdateManuallyScheduledTasksWhenEditingLinks': '1',
    'KeepTaskOnNearestWorkingTimeWhenMadeAutoScheduled': '0',
})

MS_TASK_FIELDS = OrderedDict(**{
    'UID': '0',  # Debe ser un ID único, como el record.id
    'GUID': '340E2183-1799-EA11-A631-20CF30D8DAF5',  # No se como hacen este hash
    'ID': '0',
    'Name': 'Proyecto1',
    'Active': '1',
    'Manual': '0',
    'Type': '1',  # No se como es el type, ver luego
    'IsNull': '0',
    'CreateDate': '2020-05-18T15:54:00',  # Puede ser la fecha actual...
    'WBS': '0',
    'OutlineNumber': '0',
    'OutlineLevel': '0',
    'Priority': '500',
    'Start': '2020-05-18T09:00:00',  # Fechas importantes...
    'Finish': '2020-05-27T18:00:00',  # Fechas importantes...
    'Duration': 'PT63H0M0S',  # Averiguar este idioma
    'ManualStart': '2020-05-18T09:00:00',
    'ManualFinish': '2020-05-27T18:00:00',
    'ManualDuration': 'PT63H0M0S',  # Averiguar este idioma
    'DurationFormat': '21',
    'FreeformDurationFormat': '7',
    'Work': 'PT63H0M0S',
    'ResumeValid': '0',
    'EffortDriven': '0',
    'Recurring': '0',
    'OverAllocated': '0',
    'Estimated': '0',
    'Milestone': '0',
    'Summary': '1',
    'DisplayAsSummary': '0',
    'Critical': '1',
    'IsSubproject': '0',
    'IsSubprojectReadOnly': '0',
    'ExternalTask': '0',
    'EarlyStart': '2020-05-18T09:00:00',
    'EarlyFinish': '2020-05-27T18:00:00',
    'LateStart': '2020-05-18T09:00:00',
    'LateFinish': '2020-05-27T18:00:00',
    'StartVariance': '0',
    'FinishVariance': '0',
    'WorkVariance': '3780000.00',
    'FreeSlack': '0',
    'TotalSlack': '0',
    'StartSlack': '0',
    'FinishSlack': '0',
    'FixedCost': '0',
    'FixedCostAccrual': '3',
    'PercentComplete': '0',
    'PercentWorkComplete': '0',
    'Cost': '88200',
    'OvertimeCost': '0',
    'OvertimeWork': 'PT0H0M0S',
    'ActualDuration': 'PT0H0M0S',
    'ActualCost': '0',
    'ActualOvertimeCost': '0',
    'ActualWork': 'PT0H0M0S',
    'ActualOvertimeWork': 'PT0H0M0S',
    'RegularWork': 'PT63H0M0S',
    'RemainingDuration': 'PT63H0M0S',
    'RemainingCost': '88200',
    'RemainingWork': 'PT63H0M0S',
    'RemainingOvertimeCost': '0',
    'RemainingOvertimeWork': 'PT0H0M0S',
    'ACWP': '0.00',
    'CV': '0.00',
    'ConstraintType': '0',
    'CalendarUID': '-1',
    'LevelAssignments': '1',
    'LevelingCanSplit': '1',
    'LevelingDelay': '0',
    'LevelingDelayFormat': '8',
    'IgnoreResourceCalendar': '0',
    'HideBar': '0',
    'Rollup': '0',
    'BCWS': '0.00',
    'BCWP': '0.00',
    'PhysicalPercentComplete': '0',
    'EarnedValueMethod': '0',
    'IsPublished': '0',
    'CommitmentType': '0',
})


class BimGanttExport(models.TransientModel):
    _name = 'bim.gantt.export'
    _description = 'Exportador de proyectos Gantt'

    budget_id = fields.Many2one('bim.budget', 'Presupuesto', required=True)
    gantt_type = fields.Selection([('ms', 'Microsoft Project'),
                                   ('gp', 'Gantt Project')], 'Tipo de Gantt', default='ms', required=True)

    def print_xml(self):
        if self.gantt_type == 'gp':
            raise ValidationError('Aún no está implementado Gantt Project')
        elif self.gantt_type == 'ms':
            xml = self.generate_ms_project()
        else:
            raise ValidationError('Debe escoger algún tipo de gantt a generar.')

        filename = '%s_%s.xml' % (self.gantt_type, self.budget_id.code or self.budget_id.name)
        attach_vals = {
            'name': filename,
            'datas': base64.b64encode(str(xml).encode('utf-8')),
            'res_model': 'bim.budget',
            'res_id': self.budget_id.id,
            'store_fname': filename,
        }

        doc_id = self.env['ir.attachment'].create(attach_vals)
        return {
            'name': filename,
            'type': 'ir.actions.act_url',
            'url': 'web/content/%d?download=true' % doc_id.id,
            'target': 'self',
        }

    def generate_ms_project(self):
        xml = BeautifulSoup(features='lxml-xml')
        dt_format = '%Y-%m-%dT%H:%M:%S'
        root = xml.new_tag('Project')
        root['xmlns'] = 'http://schemas.microsoft.com/project'
        header = MS_HEADER_FIELDS.copy()
        header.update({
            'name': '%s_%s.xml' % (self.gantt_type, self.budget_id.code or self.budget_id.name),
            'title': self.budget_id.name,
            'CreationDate': fields.Datetime.now().strftime(dt_format),
            'LastSaved': fields.Datetime.now().strftime(dt_format),
            'StartDate': self.budget_id.date_start.strftime(dt_format),
            'FinishDate': self.budget_id.date_end.strftime(dt_format),
        })
        # Atributos iniciales del documento
        for tag, value in header.items():
            xml_tag = xml.new_tag(tag)
            xml_tag.append(value)
            root.append(xml_tag)
        # Los tasks
        tasks_root = xml.new_tag('Tasks')
        for concept in self.budget_id.concept_ids:
            concept_tag = xml.new_tag('Task')
            task_fields = MS_TASK_FIELDS.copy()
            start = concept.acs_date_start or fields.Date.today()  # Hay que darle alguna fecha
            end = concept.acs_date_end or start
            task_fields.update({
                'UID': concept.id,
                'ID': concept.id,
                'Name': concept.name,
                'CreateDate': concept.create_date.strftime(dt_format),
                'Start': start.strftime(dt_format),
                'Finish': end.strftime(dt_format),
                'WBS': get_wbs(concept),
            })
            for tag, value in task_fields.items():
                field_tag = xml.new_tag(tag)
                field_tag.append(str(value))
                concept_tag.append(field_tag)
            tasks_root.append(concept_tag)
        root.append(tasks_root)
        xml.append(root)
        return xml


def get_wbs(concept):
    if not concept.parent_id:
        return str(concept.id)
    return get_wbs(concept.parent_id) + '.' + str(concept.id)
