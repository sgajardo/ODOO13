import base64
from collections import OrderedDict
import datetime

from bs4 import BeautifulSoup
from odoo import fields, models
from odoo.exceptions import ValidationError

MS_HEADER_FIELDS = OrderedDict(**{
    # 'SaveVersion': '14',
    # 'BuildNumber': '16.0.12624.20466',
    # 'Name': 'Gantt set1 microsoft project.xml',  # Nombre archivo
    # 'GUID': '320E2183-1799-EA11-A631-20CF30D8DAF5',  # vaya a sabe como lo genero
    # 'Title': 'Proyecto1',  # Nombre proyecto
    # 'CreationDate': '2020-05-18T09:00:00',  # fecha creación
    # 'LastSaved': '2020-05-18T16:17:00',  # fecha modificación
    'ScheduleFromStart': '1',
    # 'StartDate': '2020-05-18T09:00:00',  # fechas del proyecto
    # 'FinishDate': '2020-05-27T18:00:00',  # fechas del proyecto
    'FYStartDate': '1',
    'CriticalSlackLimit': '0',
    'CurrencyDigits': '2',
    'CurrencySymbol': '€',
    'CurrencyCode': 'EUR',
    'CurrencySymbolPosition': '3',
    'CalendarUID': '1',
    'DefaultStartTime': '09:00:00',
    'DefaultFinishTime': '18:00:00',
    'MinutesPerDay': '540',
    'MinutesPerWeek': '2700',
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
    # 'CurrentDate': '2020-05-18T09:00:00',
    'MicrosoftProjectServerURL': '1',
    'Autolink': '0',
    'NewTaskStartDate': '0',
    'NewTasksAreManual': '1',
    'DefaultTaskEVMethod': '0',
    'ProjectExternallyEdited': '0',
    # 'ExtendedCreationDate': '1984-01-01T00:00:00',
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

MS_RESOURCES_FIELDS = {
    'UID': '0',
    'ID': '0',
    'Type': '1',
    'IsNull': '0',
    'MaxUnits': '1.00',
    'PeakUnits': '0.00',
    'OverAllocated': '0',
    'CanLevel': '1',
    'AccrueAt': '3',
    'Work': 'PT0H0M0S',
    'RegularWork': 'PT0H0M0S',
    'OvertimeWork': 'PT0H0M0S',
    'ActualWork': 'PT0H0M0S',
    'RemainingWork': 'PT0H0M0S',
    'ActualOvertimeWork': 'PT0H0M0S',
    'RemainingOvertimeWork': 'PT0H0M0S',
    'PercentWorkComplete': '0',
    'StandardRate': '0',
    'StandardRateFormat': '2',
    'Cost': '0',
    'OvertimeRate': '0',
    'OvertimeRateFormat': '2',
    'OvertimeCost': '0',
    'CostPerUse': '0',
    'ActualCost': '0',
    'ActualOvertimeCost': '0',
    'RemainingCost': '0',
    'RemainingOvertimeCost': '0',
    'WorkVariance': '0.00',
    'CostVariance': '0',
    'SV': '0.00',
    'CV': '0.00',
    'ACWP': '0.00',
    'CalendarUID': '2',
    'BCWS': '0.00',
    'BCWP': '0.00',
    'IsGeneric': '0',
    'IsInactive': '0',
    'IsEnterprise': '0',
    'BookingType': '0',
    'IsCostResource': '0',
    'IsBudget': '0',
}

MS_PREDECESSOR_MAPPING = {
    'ff': '0',
    'fs': '1',
    'sf': '2',
    'ss': '3',
}


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
        working_hours = self.env.company.working_hours
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
            'MinutesPerDay': working_hours * 60,
            'MinutesPerWeek': working_hours * 300,
        })
        # Atributos iniciales del documento
        for tag, value in header.items():
            xml_tag = xml.new_tag(tag)
            xml_tag.append(str(value))
            root.append(xml_tag)

        # La hoja de recursos
        views_root = xml.new_tag('Views')
        view_tag = xml.new_tag('View')
        name_tag = xml.new_tag('Name')
        name_tag.append('H&amp;oja de recursos')
        view_tag.append(name_tag)
        customized_tag = xml.new_tag('IsCustomized')
        customized_tag.append('true')
        view_tag.append(customized_tag)
        views_root.append(view_tag)
        root.append(views_root)
        # Los tasks
        tasks_root = xml.new_tag('Tasks')
        project_task = {
            'UID': '0',
            'ID': '0',
            'Name': self.budget_id.project_id.name,
            'CreateDate': self.budget_id.project_id.create_date.strftime(dt_format),
            'Start': datetime.datetime.combine(self.budget_id.date_start, datetime.time(9, 0)).strftime(dt_format),
            'Finish': datetime.datetime.combine(self.budget_id.date_end, datetime.time(9, 0)).strftime(dt_format),
            'WBS': '0',
            'OutlineNumber': '0',
            'OutlineLevel': '0',
            'CalendarUID': '1',
        }
        project_task_tag = xml.new_tag('Task')
        for tag, value in project_task.items():
            field_tag = xml.new_tag(tag)
            field_tag.append(str(value))
            project_task_tag.append(field_tag)
        tasks_root.append(project_task_tag)

        budget_task = {
            'UID': '1',
            'ID': '1',
            'Name': self.budget_id.name,
            'CreateDate': self.budget_id.create_date.strftime(dt_format),
            'Start': datetime.datetime.combine(self.budget_id.date_start, datetime.time(9, 0)).strftime(dt_format),
            'Finish': datetime.datetime.combine(self.budget_id.date_end, datetime.time(9, 0)).strftime(dt_format),
            'WBS': '1',
            'OutlineNumber': '1',
            'OutlineLevel': '1',
            'CalendarUID': '1',
        }
        budget_task_tag = xml.new_tag('Task')
        for tag, value in budget_task.items():
            field_tag = xml.new_tag(tag)
            field_tag.append(str(value))
            budget_task_tag.append(field_tag)
        tasks_root.append(budget_task_tag)
        for concept in self.budget_id.concept_ids:
            if concept.type not in ['chapter', 'departure'] or concept.parent_id:
                continue
            concepts_tags = generate_concepts_xml(concept, xml, working_hours, dt_format)
            for concept_tag in concepts_tags:
                tasks_root.append(concept_tag)
        root.append(tasks_root)

        # Recursos
        resources_root = xml.new_tag('Resources')
        resource_tag = xml.new_tag('Resource')
        for tag, value in MS_RESOURCES_FIELDS.copy().items():
            field_tag = xml.new_tag(tag)
            field_tag.append(str(value))
            resource_tag.append(field_tag)
        resources_root.append(resource_tag)
        products = [False]
        for i, prod in enumerate(self.budget_id.concept_ids.mapped('product_id'), 1):
            duration = get_duration(sum(self.budget_id.concept_ids.filtered_domain([('product_id', '=', prod.id)]).mapped('parent_id.duration')), working_hours)
            prod_values = {
                'UID': i,
                'ID': i,
                'Name': prod.name,
                'Initials': prod.resource_type,
                'Type': '1' if prod.resource_type in ['H', 'Q'] else '0',
                'Cost': prod.standard_price,
                'RemainingCost': prod.standard_price,
                'CostVariance': prod.standard_price,
                'StandardRate': prod.standard_price if prod.resource_type in ['H', 'Q'] else '1',
                'StandardRateFormat': '2' if prod.resource_type in ['H', 'Q', 'A'] else '8',
                'IsCostResource': '1' if prod.resource_type == 'A' else '0',
                'Work': duration,
                'RegularWork': duration,
                'RemainingWork': duration,
                'CostPerUse': prod.standard_price,
            }
            products.append(prod)
            resource_tag = xml.new_tag('Resource')
            for tag, value in prod_values.items():
                field_tag = xml.new_tag(tag)
                field_tag.append(str(value))
                resource_tag.append(field_tag)
            resources_root.append(resource_tag)
        root.append(resources_root)

        # Asignaciones
        assignments_root = xml.new_tag('Assignments')
        for i, resource in enumerate(self.budget_id.concept_ids, 1):
            if resource.type in ['chapter', 'departure']:
                continue
            assignment_tag = xml.new_tag('Assignment')
            assignment_vals = {
                'UID': i,
                'TaskUID': resource.parent_id.id,
                'ResourceUID': products.index(resource.product_id),
                'Units': resource.available if resource.product_id.resource_type in ['H', 'Q'] else resource.quantity,
                'Cost': resource.balance,
                'HasFixedRateUnits': '1' if resource.product_id.resource_type in ['H', 'Q'] else '0',
                'FixedMaterial': '1' if resource.product_id.resource_type == 'M' else '0',
                'Work': get_duration(resource.quantity * resource.parent_id.quantity / working_hours, working_hours),
            }
            for tag, value in assignment_vals.items():
                field_tag = xml.new_tag(tag)
                field_tag.append(str(value))
                assignment_tag.append(field_tag)
            assignments_root.append(assignment_tag)
        root.append(assignments_root)

        xml.append(root)
        return xml


def sort_concepts(concept):
    return (concept.sequence, concept.id)


def get_wbs(concept):
    if not concept.parent_id:
        return '1.' + str(concept.budget_id.concept_ids.filtered(lambda c: not c.parent_id).sorted(sort_concepts).mapped('id').index(concept.id) + 1)
    return get_wbs(concept.parent_id) + '.' + str(concept.parent_id.child_ids.sorted(sort_concepts).mapped('id').index(concept.id) + 1)

def get_duration(days, workable):
    """ Recibe la cantidad de horas y las horas laborables, y devuelve la cantidad
        de días, horas, minutos y segundos """
    hours = int(days * workable)
    minutes = int(((days * workable) - hours) * 60)
    seconds = int(((((days * workable) - hours) * 60) - minutes) * 60)
    return 'PT%dH%dM%dS' % (hours, minutes, seconds)


def generate_concepts_xml(concept, xml, working_hours, dt_format):
    wbs = get_wbs(concept).split('.')
    concept_tag = xml.new_tag('Task')
    start = concept.acs_date_start or fields.Datetime.now()  # Hay que darle alguna fecha
    end = concept.acs_date_end or start
    task_fields = {
        'UID': concept.id,
        'ID': concept.id,
        'Name': concept.name,
        'CreateDate': concept.create_date.strftime(dt_format),
        'Start': start.replace(hour=9, minute=0, second=0).strftime(dt_format),
        'Finish': end.replace(hour=18, minute=0, second=0).strftime(dt_format),
        'Duration': get_duration(concept.duration, working_hours),
        'WBS': '.'.join(wbs),
        'OutlineNumber': wbs[-1],
        'OutlineLevel': len(wbs),
        'CalendarUID': '1',
    }
    for tag, value in task_fields.items():
        field_tag = xml.new_tag(tag)
        field_tag.append(str(value))
        concept_tag.append(field_tag)
    # Verificamos las predecesoras
    for predecessor in concept.bim_predecessor_concept_ids:
        predecessor_link_tag = xml.new_tag('PredecessorLink')
        predecessor_vals = {
            'PredecessorUID': predecessor.name.id,
            'Type': MS_PREDECESSOR_MAPPING.get(predecessor.pred_type, '1'),
            'LinkLag': predecessor.difference * working_hours * 600,
            'LagFormat': '7',
        }
        for tag, value in predecessor_vals.items():
            field_tag = xml.new_tag(tag)
            field_tag.append(str(value))
            predecessor_link_tag.append(field_tag)

        concept_tag.append(predecessor_link_tag)
    concepts = [concept_tag]
    for child in concept.child_ids:
        if child.type in ['chapter', 'departure']:
            concepts.extend(generate_concepts_xml(child, xml, working_hours, dt_format))
    return concepts
