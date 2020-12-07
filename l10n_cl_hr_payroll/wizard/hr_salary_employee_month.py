from odoo import api, fields, models
import time


class hr_salary_employee_bymonth(models.TransientModel):

    _name = 'hr.salary.employee.month'
    _description = 'Libro de Remuneraciones Haberes'

    def _get_default_end_date(self):
        date = fields.Date.from_string(fields.Date.today())
        return date.strftime('%Y') + '-' + date.strftime('%m') + '-' + date.strftime('%d')

    no_header = fields.Boolean('Sin Encabezado', help="Imprimir libro de remuneraciones sin encabezado ni pie de página de la compañía")
    end_date = fields.Date(string='Fecha', required=True, default=_get_default_end_date)

    def print_report(self):
        action = self.env.ref('l10n_cl_hr_payroll.report_hrsalarybymonth').report_action(self)
        action.update({'close_on_report_download': True})
        return action

    def get_worked_days(self, emp_id, emp_salary, mes, ano):

        self.env.cr.execute(
            '''select sum(number_of_days) from hr_payslip_worked_days as p
left join hr_payslip as r on r.id = p.payslip_id
left join hr_work_entry_type w on p.work_entry_type_id = w.id
where r.employee_id = %s  and (to_char(r.date_to,'mm')= %s)
and (to_char(r.date_to,'yyyy')= %s) and ('WORK100' = w.code)
''', (emp_id, mes, ano,))

        max = self.env.cr.fetchone()

        emp_salary.append(max[0])

        return emp_salary

    def get_employe_basic_info(self, emp_salary, cod_id, mes, ano):

        self.env.cr.execute(
            '''select sum(pl.total) from hr_payslip_line as pl
left join hr_payslip as p on pl.slip_id = p.id
left join hr_employee as emp on emp.id = p.employee_id
left join resource_resource as r on r.id = emp.resource_id
where p.state not in ('draft', 'verify', 'cancel') and (pl.code like %s) and (to_char(p.date_to,'mm')=%s)
and (to_char(p.date_to,'yyyy')=%s)
group by r.name, p.date_to''', (cod_id, mes, ano,))

        max = self.env.cr.fetchone()

        if max is None:
            emp_salary.append(0.00)
        else:
            emp_salary.append(max[0])

        return emp_salary

    def get_analytic(self, form):
        emp_salary = []
        salary_list = []
        last_year = form['end_date'][0:4]
        last_month = form['end_date'][5:7]
        cont = 0

        self.env.cr.execute(
            '''select sum(pl.total), w.name from hr_payslip_line as pl
left join hr_payslip as p on pl.slip_id = p.id
left join hr_employee as emp on emp.id = p.employee_id
left join hr_contract as r on r.id = p.contract_id
left join account_analytic_account as w on w.id = r.analytic_account_id
where p.state not in ('draft', 'verify', 'cancel') and (to_char(p.date_to,'mm')=%s)
and (to_char(p.date_to,'yyyy')=%s)
group by w.name order by name''', (last_month, last_year,))

        id_data = self.env.cr.fetchall()
        if id_data is None:
            emp_salary.append(0.00)
            emp_salary.append(0.00)

        else:
            for index in id_data:
                emp_salary.append(id_data[cont][0])
                emp_salary.append(id_data[cont][1])

                cont = cont + 1
                salary_list.append(emp_salary)

                emp_salary = []

        return salary_list

    def get_salary(self, emp_id, emp_salary, cod_id, mes, ano):

        self.env.cr.execute(
            '''select sum(pl.total) from hr_payslip_line as pl
left join hr_payslip as p on pl.slip_id = p.id
left join hr_employee as emp on emp.id = p.employee_id
left join resource_resource as r on r.id = emp.resource_id
where p.state not in ('draft', 'verify', 'cancel') and p.employee_id = %s and (pl.code like %s)
and (to_char(p.date_to,'mm')=%s) and (to_char(p.date_to,'yyyy')=%s)
group by r.name, p.date_to,emp.id''', (emp_id, cod_id, mes, ano,))

        max = self.env.cr.fetchone()

        if max is None:
            emp_salary.append(0.00)
        else:
            emp_salary.append(max[0])

        return emp_salary

    def get_employee2(self, form):
        emp_salary = []
        salary_list = []
        last_year = form['end_date'].strftime('%Y')
        last_month = form['end_date'].strftime('%m')
        cont = 0

        self.env.cr.execute(
            '''select emp.id, emp.identification_id, emp.first_name, emp.middle_name, emp.last_name, emp.mothers_name
from hr_payslip as p left join hr_employee as emp on emp.id = p.employee_id
left join hr_contract as r on r.id = p.contract_id
where p.state not in ('draft', 'verify', 'cancel')  and (to_char(p.date_to,'mm')=%s)
and (to_char(p.date_to,'yyyy')=%s)
group by emp.id, emp.middle_name, emp.last_name, emp.mothers_name, emp.identification_id
order by last_name''', (last_month, last_year,))

        id_data = self.env.cr.fetchall()
        if id_data is None:
            emp_salary.append(0.00)
            emp_salary.append(0.00)
            emp_salary.append(0.00)
            emp_salary.append(0.00)
            emp_salary.append(0.00)
        else:
            for index in id_data:
                emp_salary.append(id_data[cont][0])
                emp_salary.append(id_data[cont][1])
                emp_salary.append(id_data[cont][2])
                emp_salary.append(id_data[cont][3])
                emp_salary.append(id_data[cont][4])
                emp_salary.append(id_data[cont][5])
                emp_salary = self.get_worked_days(
                    id_data[cont][0], emp_salary, last_month, last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'SUELDO', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'HEX%', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'GRAT', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'BONO', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'TOTIM', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'ASIGFAM', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'TOTNOI', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'TOTNOI', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'HAB', last_month, last_year)

                cont = cont + 1
                salary_list.append(emp_salary)

                emp_salary = []

        return salary_list

    def get_employee(self, form):
        emp_salary = []
        salary_list = []
        last_year = form['end_date'].strftime('%Y')
        last_month = form['end_date'].strftime('%m')
        cont = 0

        self.env.cr.execute(
            '''select emp.id, emp.identification_id, emp.first_name, emp.middle_name, emp.last_name, emp.mothers_name
from hr_payslip as p left join hr_employee as emp on emp.id = p.employee_id
left join hr_contract as r on r.id = p.contract_id
where p.state not in ('draft', 'verify', 'cancel')  and (to_char(p.date_to,'mm')=%s)
and (to_char(p.date_to,'yyyy')=%s)
group by emp.id, emp.middle_name, emp.last_name, emp.mothers_name, emp.identification_id
order by last_name''', (last_month, last_year))

        id_data = self.env.cr.fetchall()
        if id_data is None:
            emp_salary.append(0.00)
            emp_salary.append(0.00)
            emp_salary.append(0.00)
            emp_salary.append(0.00)
            emp_salary.append(0.00)
        else:
            for index in id_data:
                emp_salary.append(id_data[cont][0])
                emp_salary.append(id_data[cont][1])
                emp_salary.append(id_data[cont][2])
                emp_salary.append(id_data[cont][3])
                emp_salary.append(id_data[cont][4])
                emp_salary.append(id_data[cont][5])
                emp_salary = self.get_worked_days(
                    id_data[cont][0], emp_salary, last_month, last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'PREV', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'SALUD', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'IMPUNI', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'SECE', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'ADISA', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'TODELE', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'SMT', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'TDE', last_month,
                    last_year)
                emp_salary = self.get_salary(
                    id_data[cont][0], emp_salary, 'LIQ', last_month,
                    last_year)

                cont = cont + 1
                salary_list.append(emp_salary)

                emp_salary = []
        return salary_list
