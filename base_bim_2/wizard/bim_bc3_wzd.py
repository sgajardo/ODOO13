import base64

from odoo import fields, models


class BimBc3Wizard(models.TransientModel):
    _name = 'bim.bc3.wizard'
    _description = 'BC3 Import'

    bc3_file = fields.Binary('Archivo BC3', required=True, track_visibility='onchange')
    filename = fields.Char('Nombre archivo')

    def do_action(self):
        concept_obj = self.env['bim.concepts']
        external_concept = concept_obj.browse(self.env.context.get('concept_id'))
        uom_obj = self.env['uom.uom']
        product_obj = self.env['product.product']
        children_codes = {}
        budget = external_concept.budget_id
        concepts = concept_obj.browse()
        data = base64.b64decode(self.bc3_file).decode('latin-1')
        nats = ['not_used', 'labor', 'equip', 'material']
        res_types = ['A', 'H', 'Q', 'M']
        pending = ''
        rows = data.split('\n')
        next_index = 0
        for row in rows:
            next_index += 1
            row = row.strip()
            if row and pending:
                row = pending + row
                pending = ''

            next_row = rows[next_index] if len(rows) > next_index else False
            if row and next_row and next_row[0] != '~':
                pending = row
                continue
            else:
                pending = ''

            if not row or row[0] != '~':
                continue
            elif row[1] == 'C':
                datas = row[3:].split('|')
                code, uom, name, price, ___, ctype = datas[:6]
                ctype = int(ctype)
                if external_concept.type == 'departure' and ctype == 0 and '#' in code:
                    continue
                concept = concept_obj.create({
                    'code': code,
                    'type': 'aux' if '%' in code else nats[ctype] if 0 < ctype < 4 else 'departure',
                    'uom_id': uom_obj.search(['|', ('name', 'ilike', uom), ('alt_names', 'ilike', uom)], limit=1).id if uom else None,
                    'name': name,
                    'budget_id': budget.id,
                    'quantity': 1,
                    'amount_fixed': price,
                    'amount_type': 'fixed',
                    'parent_id': external_concept.id,
                })

                if concept.type not in ['chapter', 'departure']:
                    product = product_obj.search([('name', 'ilike', name)], limit=1)
                    if not product:
                        res_type = res_types[ctype] if ctype < 4 else None
                        product = product_obj.create({
                            'name': name,
                            'resource_type': res_type,
                            'type': 'product' if res_type == 3 else 'service',
                        })
                    concept.product_id = product

                for i, (parent_code, child_data) in enumerate(children_codes.get(code, {}).items()):
                    parent = concepts.filtered_domain([('code', '=', parent_code)])
                    parent.amount_type = 'compute'
                    if i == 0:
                        concept.parent_id = parent
                        concept.quantity = child_data.get('qty', 0)
                        concept.sequence = child_data.get('seq', 0)
                    elif parent:
                        copy_concept = self.env.user.recursive_create(concept, parent.id, budget.id)
                        copy_concept.quantity = child_data.get('qty', 0)
                        copy_concept.sequence = child_data.get('seq', 0)

                concepts += concept

            elif row[1] == 'D':
                datas = row[3:-1].split('|')
                parent_code = datas[0].replace('#', '')
                children = datas[1:]
                for seq, (code, __, qty) in enumerate(zip(*[iter(children[0].split('\\'))] * 3), 1):
                    qty = float(qty)
                    if code in children_codes:
                        children_codes[code][parent_code] = {'qty': qty, 'seq': seq}
                    else:
                        children_codes[code] = {parent_code: {'qty': qty, 'seq': seq}}
                    child = concepts.filtered_domain([('code', '=', code)]) if code else concept_obj.browse()
                    parent = concepts.filtered_domain([('code', '=', parent_code)]) if parent_code else concept_obj.browse()
                    if parent and child:
                        if child.parent_id:
                            child = self.env.user.recursive_create(child, parent.id, budget.id)
                        parent.child_ids += child
                        parent.amount_type = 'compute'
                    child.sequence = seq
                    child.quantity = qty
        for concept in concepts:
            concept.onchange_function()
        return {'ir.actions.act_window_close'}
