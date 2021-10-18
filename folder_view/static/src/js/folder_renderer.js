odoo.define('folder_view.renderer', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');

    var CELL_DECORATIONS = [
        'text-danger',
        'text-info',
        'text-muted',
        'text-primary',
        'text-success',
        'text-warning',
        'bg-light',
        'bg-dark',
        'bg-danger',
        'bg-info',
        'bg-primary',
        'bg-success',
        'bg-warning',
    ];

    var FolderRenderer = ListRenderer.extend({
        init: function (parent, state, params) {
            state.fieldsInfo.list = state.fieldsInfo.folder;
            this._super.apply(this, arguments);
            this.parent_field = params.arch.attrs.parent_field || 'parent_id';
        },
        _getNumberOfCols: function () {
            return this._super.apply(this, arguments) + 1;
        },
        _renderHeader: function () {
            var $thead = this._super.apply(this, arguments);
            if (this.hasSelectors) {
                $thead.find('.o_list_record_selector').after('<th/>');
            } else {
                $thead.find('tr').prepend('<th class="o_folder_open_record"/>');
            }
            return $thead;
        },
        _renderFooter: function () {
            var $tfoot = this._super.apply(this, arguments);
            $tfoot.find('tr').prepend('<th/>');
            return $tfoot;
        },
        _renderRow: function (record) {
            var $row = this._super.apply(this, arguments);
            var el = '<td class="o_folder_open_record"><button class="btn"><i class="fa fa-external-link"/></button></td>';
            if (this.hasSelectors) {
                $row.find('.o_list_record_selector').after(el);
            } else {
                $row.prepend(el);
            }
            return $row;
        },
        _renderBodyCell: function (record, node, options) {
            var $td = this._super.apply(this, arguments);
            if (node.attrs.options) {
                var opts = typeof node.attrs.options === 'string' ? JSON.parse(node.attrs.options.replace(/"/g, '<->').replace(/'/g, '"').replace(/<->/g, "'")) : node.attrs.options;
                this._setCellDecorations(record, opts, $td);
            }
            return $td;
        },
        _onRowClicked: function (ev) {
            var id = $(ev.currentTarget).data('id');
            var record = this._getRecord(id);
            if (ev.target.closest('.o_folder_open_record')) {
                if (id) {
                    this.trigger_up('open_record', { id: id, target: ev.target });
                }
            } else if (!ev.target.closest('.o_list_record_selector') && !$(ev.target).prop('special_click')) {
                var context = {};
                var default_field = 'default_' + this.parent_field;
                context[default_field] = record.res_id;
                this.do_action({
                    type: 'ir.actions.act_window',
                    name: record.data.display_name || record.data.name,
                    view_type: 'folder,form',
                    view_mode: 'form',
                    views: [[false, 'folder'], [false, 'form']],
                    res_model: this.state.model,
                    domain: [[this.parent_field, '=', record.res_id]],
                    context: context,
                });
            }
        },
        _setCellDecorations: function (record, options, $td) {
            var decorations = _.chain(options)
                .pick(function (value, key) {
                    return CELL_DECORATIONS.indexOf(key) >= 0;
                }).mapObject(function (value) {
                    return py.parse(py.tokenize(value));
                }).value();
            _.each(decorations, function (expr, cssClass) {
                $td.toggleClass(cssClass, py.PY_isTrue(py.evaluate(expr, record.evalContext)));
            });
        },
    });

    return FolderRenderer;
});