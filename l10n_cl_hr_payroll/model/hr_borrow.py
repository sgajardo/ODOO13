from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero


class HrPrestamos(models.Model):
    _name = 'hr.borrow'
    _description = 'Prestamos'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('Código', translate=True, default='Nuevo', readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Empleado')
    date_start = fields.Date('Periodo de Inicio')
    rut_r = fields.Char('RUT', related='employee_id.identification_id')
    cuotas = fields.Integer()
    valor_total = fields.Integer('Valor Total')
    line_ids = fields.One2many('hr.borrow.line', 'borrow_id', 'Líneas Cuotas', help='Cuotas de Prestamo')
    desc = fields.Text('Nota')
    amount_total = fields.Float('Importe Total', compute='_compute_all', help='Monto total del Prestamo', store=True)
    amount_paid = fields.Float('Importe Cobrado', compute='_compute_all', help='Monto cobrado del Prestamo', store=True)
    amount_due = fields.Float('Deuda', compute='_compute_all', help='Monto a pagar del Prestamo', store=True)

    inputs_id = fields.Many2one('hr.payslip.input.type', string='Entrada', required=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.borrow') or 'Nuevo'
        return super(HrPrestamos, self).create(vals)

    @api.onchange('valor_total', 'cuotas', 'date_start')
    def onchange_values(self):
        account_precision = self.env['decimal.precision'].precision_get('Account')
        if not float_is_zero(self.valor_total, account_precision) and self.cuotas > 0 and self.date_start:
            date_for = fields.Date.from_string(self.date_start)
            lines = []
            for i in range(self.cuotas):
                index = i + 1
                date_line = date_for + relativedelta(months=1)
                lines.append((0, 0, {
                    'name': 'Cuota %s' % index,
                    'num_cuota': index,
                    'amount': self.valor_total / self.cuotas,
                    'date_due': fields.Date.to_string(date_line)
                }))
                date_for = date_line
            self.line_ids = lines

    @api.depends('line_ids.amount', 'line_ids.cobrado')
    def _compute_all(self):
        for prestamo in self:
            prestamo.amount_total = sum(x.amount for x in prestamo.line_ids)
            prestamo.amount_paid = sum(x.amount for x in prestamo.line_ids if(x.cobrado is True))
            prestamo.amount_due = prestamo.amount_total - prestamo.amount_paid


class HrPrestamosLine(models.Model):
    _description = 'Cuotas de Prestamos'
    _name = 'hr.borrow.line'

    name = fields.Char('Cuota', reaonly=True)
    num_cuota = fields.Integer('Número', help='Número de cuota', readonly=True)
    borrow_id = fields.Many2one('hr.borrow', 'Prestamo', ondelete='cascade', readonly=True)
    amount = fields.Float('Monto', help='Monto de la cuota')
    date_due = fields.Date('Fecha Vencimiento', help='Fecha de vencimiento de la cuota')
    cobrado = fields.Boolean()
    payslip_id = fields.Many2one('hr.payslip', 'Nómina', help='Nómina en la que se pagó esta cuota')

    def cobrar(self, payslip_id):
        """ Marca una cuota como pagada y agrega el monto cobrado al préstamo """
        if any(self.mapped('payslip_id')):
            raise ValidationError(_('Algunas cuotas de préstamos fueron pagadas en las nóminas: %s') % ', '.join(self.mapped('payslip_id.name')))
        self.write({'cobrado': True, 'payslip_id': payslip_id.id})
        return self.mapped('borrow_id')._compute_all()

    def descobrar(self):
        """ Devuelve las cuotas como no cobradas y le elimina la entrada de nómina """
        self.write({'cobrado': False, 'payslip_id': False})
        return self.mapped('borrow_id')._compute_all()
