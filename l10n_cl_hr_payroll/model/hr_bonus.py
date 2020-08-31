# coding: utf-8
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

RO_STATES = {'draft': [('readonly', False)]}


class HrBonusSheet(models.Model):
    _name = 'hr.bonus.sheet'
    _description = 'Hoja de Bonos RRHH'
    _inherit = ['mail.thread']
    _order = 'date_issue desc, name desc, id desc'

    name = fields.Char('Ref', copy=False, default='Nuevo')
    date_issue = fields.Date('Fecha solicitud', default=fields.Date.today, copy=False, required=True, readonly=True, states=RO_STATES)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Por aprobar'),
        ('approve', 'Aprobado'),
        ('cancel', 'Cancelado'),
        ('done', 'En nómina')
    ], 'Estado', default='draft', copy=False, track_visibility='onchange')
    description = fields.Text('Descripción', compute='_compute_description')
    line_ids = fields.One2many('hr.bonus.line', 'sheet_id', 'Bonos', readonly=True, states=RO_STATES)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)
    bonus_count = fields.Integer('Cant. bonos', compute='_compute_total')
    amount_total = fields.Monetary('Monto Total', compute='_compute_total')

    @api.depends('line_ids')
    def _compute_description(self):
        for record in self:
            record.description = ', '.join(record.mapped('line_ids.haberesydesc_id.desc'))

    @api.depends('line_ids')
    def _compute_total(self):
        for record in self:
            record.amount_total = sum(record.line_ids.filtered(lambda l: l.haberesydesc_id.um == '$').mapped('amount'))
            record.bonus_count = len(record.line_ids)

    def back_draft(self):
        for record in self:
            if record.state in ['approve', 'done', 'cancel'] and not self.env.user.has_group('hr.group_hr_manager'):
                raise ValidationError(_('No tiene permisos para devolver a borrador el documento %s.') % record.name)
        self.write({'state': 'draft'})

    def confirm(self):
        self.write({'state': 'pending'})

    def approve(self):
        self.write({'state': 'approve'})

    def cancel(self):
        self.write({'state': 'cancel'})

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.bonus.sheet')
        return super(HrBonusSheet, self).create(vals)

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('%s debe estar en estado Borrador para poder borrarlo.') % record.name)
        return super(HrBonusSheet, self).unlink()

    def create_haberesydesc(self):
        employees = {}
        for line in self.mapped('line_ids'):
            # Se deben evaluar los casos:
            # 1.- Línea a insertar no tiene fecha fin y el hyd tampoco tiene: Se toma siempre
            # 2.- Línea a insertar tiene fecha fin y el hyd no tiene: fecha fin de línea debe ser mayor a fecha inicio de hyd
            # 3.- Línea a insertar no tiene fecha fin y el hyd si tiene: fecha inicio de línea debe ser menor a fecha fin de hyd debe ser
            # 4.- Línea a insertar y hyd tienen fecha fin: se compara rango exacto de fechas
            if line.date_to:
                hyd_ids = line.employee_id.haberes_descuentos_ids.filtered(lambda hd: hd.name == line.haberesydesc_id and line.date_to >= hd.fecha_desde and (line.date_from <= hd.fecha_hasta or not hd.fecha_hasta))
            else:
                hyd_ids = line.employee_id.haberes_descuentos_ids.filtered(lambda hd: hd.name == line.haberesydesc_id and (line.date_from < hd.fecha_hasta or not hd.fecha_hasta))
            if hyd_ids:
                hyd_ids.monto = line.amount
                vals = False
            else:
                vals = (0, 0, {
                    'name': line.haberesydesc_id.id,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'monto': line.amount
                })
            if vals:
                if line.employee_id in employees:
                    employees[line.employee_id].append(vals)
                else:
                    employees[line.employee_id] = [vals]
        for employee, values in employees.items():
            employee.haberes_descuentos_ids = values
        self.write({'state': 'done'})


class HrBonusLine(models.Model):
    _name = 'hr.bonus.line'
    _description = 'Línea de bonos RRHH'
    _rec_name = 'haberesydesc_id'

    haberesydesc_id = fields.Many2one('hr.balance', 'Haber/Descuento', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', 'Empleado', required=True, ondelete='cascade')
    date_from = fields.Date('Fecha desde', required=True, default=fields.Date.today)
    date_to = fields.Date('Fecha hasta')
    amount = fields.Float('Monto', required=True)
    sheet_id = fields.Many2one('hr.bonus.sheet', 'Hoja de bonos', ondelete='cascade')
    um = fields.Selection([
        ('$', '$'),
        ('u', 'u'),
        ('%', '%')], 'UM', related='haberesydesc_id.um', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError(_('Fecha desde no puede ser mayor a Fecha hasta.'))

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_('Monto debe ser mayor a 0.'))
