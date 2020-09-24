odoo.define('hierarchy_view.renderer', function (require) {
    "use strict";

    var BasicRenderer = require('web.BasicRenderer');
    var field_utils = require('web.field_utils');
    var viewUtils = require('web.viewUtils');
    var config = require('web.config');
    var core = require('web.core');
    var dialogs = require('web.view_dialogs');

    var QWeb = core.qweb;
    var _t = core._t;

    var DECORATIONS = [
        'decoration-bf',
        'decoration-it',
        'decoration-danger',
        'decoration-info',
        'decoration-muted',
        'decoration-primary',
        'decoration-success',
        'decoration-warning'
    ];

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

    var FIELD_CLASSES = {
        char: 'o_list_char',
        float: 'o_list_number',
        integer: 'o_list_number',
        monetary: 'o_list_number',
        text: 'o_list_text',
        many2one: 'o_list_many2one',
    };

    $(document).click(function () {
        $('.oh_contextmenu').hide();
        $('.oh_title a').removeClass('text-muted font-weight-bold');
    });
    $(document).contextmenu(function (ev) {
        if ($(ev.target).closest('.o_hierarchy_sidebar_container').length == 0) {
            $('.oh_contextmenu').hide();
            $('.oh_title a').removeClass('text-muted font-weight-bold');
        }
    });

    var HierarchyRenderer = BasicRenderer.extend({
        template: 'HierarchyView',
        events: {
            'contextmenu .o_hierarchy_sidebar_container': 'context_menu_parent',
            'click .o_hierarchy_sidebar_container a[data-childs="true"]': 'display_children',
            'contextmenu .o_hierarchy_sidebar_container a': 'context_menu_child',
            'click .oh_contextmenu [data-action="open"]': 'openRecord',
            'click .oh_contextmenu [data-action="create"]': 'openNewForm',
            'click .oh_contextmenu [data-action="copy"]': 'openNewForm',
            'click .oh_contextmenu [data-action="unlink"]': 'deleteRecord',
            'click tbody tr': '_onRowClicked',
        },
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.rowDecorations = _.chain(this.arch.attrs)
                .pick(function (value, key) {
                    return DECORATIONS.indexOf(key) >= 0;
                }).mapObject(function (value) {
                    return py.parse(py.tokenize(value));
                }).value();
            this.parent_field = params.arch.attrs.parent_field || 'parent_id';
            this.listData = this.state.data;
            this.$contextmenu = undefined;
            this.contextResId = undefined;
        },
        willStart: function () {
            this._processColumns();
            return this._super.apply(this, arguments);
        },
        renderSidebar: function () {
            var elements = QWeb.render('HierarchySidebarList', { records: this.state.data });
            this.$('.o_hierarchy_sidebar_container').html(elements).resizable({
                handles: 'e',
                maxWidth: 600,
                minWidth: 200,
            });
            this.$('ul').show();
        },
        context_menu_parent: function (ev) {
            ev.preventDefault();
            this.contextResId = undefined;
            this.contextParentId = undefined;
        },
        context_menu_child: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            this.$('.oh_title a').removeClass('text-primary font-weight-bold');
            var $a = $(ev.currentTarget);
            $a.addClass('text-muted font-weight-bold');
            this.contextResId = $a.get()[0].dataset.resId;
            this.contextParentId = $a.get()[0].dataset.parentId;
            if (this.$contextmenu.height() + ev.pageY >= window.innerHeight) {
                this.$contextmenu.css('top', '').css('bottom', window.innerHeight - ev.pageY).css('left', ev.pageX).show();
            } else {
                this.$contextmenu.css('top', ev.pageY).css('bottom', '').css('left', ev.pageX).show();
            }
            
        },
        openRecord: function (ev) {
            ev.preventDefault();
            this.trigger_up('open_record', { id: this.contextResId, target: ev.target });
        },
        openNewForm: function (ev) {
            ev.preventDefault();
            var self = this;
            var $a = this.$(`.oh_title [data-res-id="${this.contextResId}"]`);
            var $li = $a.closest('li');
            var parent_id = $(ev.target).data('action') === 'create' ? $a.data('id') : $a.data('parentId');
            var context = {};
            context['default_' + this.parent_field] = parent_id;
            new dialogs.FormViewDialog(this, {
                res_model: this.state.model,
                title: _t('Create ') + ' ' + (this.arch.attrs.string || ''),
                disable_multiple_selection: true,
                context: _.extend({}, this.state.context, context),
                on_saved: function () {
                    if (!parent_id) {
                        var controller = self.__parentedParent;
                        controller.__parentedParent.doAction({
                            type: 'ir.actions.act_window',
                            name: controller._title,
                            res_model: self.state.model,
                            views: controller.actionViews.map(act_view => [false, act_view.type]),
                            domain: controller.initialState.domain,
                        }, {
                            replace_last_action: true,
                            additional_context: controller.initialState.context,
                        });
                    }
                    else {
                        if ($(ev.target).data('action') === 'create') {
                            if (!$a.data('childs')) {
                                $a.get()[0].dataset.childs = true;
                                $li.find('.oh_title .fa.fa-angle-right').removeClass('fa-angle-right text-muted').addClass('fa-caret-right');
                            }
                            self.refresh_record($li);
                        } else {
                            self.refresh_record($li.parent().closest('li'));
                        }
                    }
                },
            }).open();
        },
        deleteRecord: function (ev) {
            ev.preventDefault();
            var self = this;
            var $a = this.$(`.oh_title [data-res-id="${this.contextResId}"]`);
            var $li = $a.closest('li');
            var $ul = $li.parent();
            if (confirm(_t("Are you sure you want to delete this record ?"))) {
                self.getParent().model.deleteRecords([self.contextResId], self.state.model).then(function () {
                    $li.hide(function () {
                        $li.remove();
                        if (!$ul.children().length) {
                            var $oh_title = $ul.siblings('.oh_title');
                            $oh_title.find('>.fa-caret-down').removeClass('fa-caret-down').addClass('fa-angle-right text-muted');
                            var $a2 = $oh_title.find('>a').get();
                            if ($a2.length) {
                                $a2[0].dataset.childs = false;
                            }
                            $ul.remove();
                        }
                    });
                });
            }
        },
        refresh_record: function ($li) {
            $li.find('>.oh_title i.fa-caret-down').removeClass('fa-caret-down').addClass('fa-caret-right');
            $li.find('>ul').remove();
            $li.find('a').trigger('click');
        },
        display_children: function (ev) {
            var model = this.getParent().model;
            var $a = $(ev.currentTarget);
            this.$('a').removeClass('unfolded');
            $a.addClass('unfolded');
            var $li = $a.closest('li');
            if ($li.find('>.oh_title i.fa-caret-down').length) {
                $li.find('>ul').slideUp();
                $li.find('>.oh_title i.fa-caret-down').removeClass('fa-caret-down').addClass('fa-caret-right');
                var res_id = $li.parent().parent().find('>.oh_title a').data('resId');
                var new_state = model.get(res_id);
                this.listData = new_state ? new_state.data : this.state.data;
                this.renderListData();
                return;
            } else if ($li.find('ul').length) {
                $li.find('>.oh_title i.fa-caret-right').removeClass('fa-caret-right').addClass('fa-caret-down');
                var res_id = $a.data('resId');
                var new_state = model.get(res_id);
                this.listData = new_state.data;
                this.renderListData();
                $li.find('>ul').slideDown();
                return;
            }
            $li.find('>.oh_title i.fa-caret-right').removeClass('fa-caret-right').addClass('fa-caret-down');
            var res_id = $a.data('id');
            var self = this;
            model.load({
                context: this.state.context,
                domain: [[this.parent_field, '=', res_id]],
                fields: this.state.fields,
                fieldsInfo: this.state.fieldsInfo,
                viewType: 'hierarchy',
                modelName: this.state.model,
                type: 'list',
            }).then(function (res_id) {
                var new_state = model.get(res_id);
                self.listData = new_state.data;
                self.renderListData();
                $a.data('resId', res_id);
                if (self.listData.length) {
                    var elements = QWeb.render('HierarchySidebarList', { records: self.listData });
                    $li.append(elements);
                }
                $li.find('>ul').slideDown();
            });
        },
        renderListData: function () {
            this._computeAggregates();
            var $table = $('<table>').addClass('o_list_table table table-sm table-hover table-striped');
            $table.append(this._renderHeader());
            $table.append(this._renderBody());
            $table.append(this._renderFooter());
            this.$('.o_hierarchy_widget').html($table);
        },
        _renderView: function () {
            this._computeAggregates();
            this.renderSidebar();
            this.renderListData();
            var contextmenu = QWeb.render('HierarchyContextMenu');
            this.$el.append(contextmenu);
            this.$contextmenu = this.$('.oh_contextmenu');
            return this._super.apply(this, arguments);
        },
        // ---------- List methods -------------
        _computeAggregates: function () {
            var self = this;
            var data = [];
            // if (this.selection.length) {
            //     utils.traverse_records(this.state, function (record) {
            //         if (_.contains(self.selection, record.id)) {
            //             data.push(record); // find selected records
            //         }
            //     });
            // } else {
                data = this.listData;
            // }

            _.each(this.columns, this._computeColumnAggregates.bind(this, data));
        },
        _computeColumnAggregates: function (data, column) {
            var attrs = column.attrs;
            var field = this.state.fields[attrs.name];
            if (!field) {
                return;
            }
            var type = field.type;
            if (type !== 'integer' && type !== 'float' && type !== 'monetary') {
                return;
            }
            var func = (attrs.sum && 'sum') || (attrs.avg && 'avg') ||
                (attrs.max && 'max') || (attrs.min && 'min');
            if (func) {
                var count = 0;
                var aggregateValue = 0;
                if (func === 'max') {
                    aggregateValue = -Infinity;
                } else if (func === 'min') {
                    aggregateValue = Infinity;
                }
                _.each(data, function (d) {
                    count += 1;
                    var value = (d.type === 'record') ? d.data[attrs.name] : d.aggregateValues[attrs.name];
                    if (func === 'avg') {
                        aggregateValue += value;
                    } else if (func === 'sum') {
                        aggregateValue += value;
                    } else if (func === 'max') {
                        aggregateValue = Math.max(aggregateValue, value);
                    } else if (func === 'min') {
                        aggregateValue = Math.min(aggregateValue, value);
                    }
                });
                if (func === 'avg') {
                    aggregateValue = count ? aggregateValue / count : aggregateValue;
                }
                column.aggregate = {
                    help: attrs[func],
                    value: aggregateValue,
                };
            }
        },
        _processColumns: function () {
            var self = this;
            this.columns = [];
            _.each(this.arch.children, function (c) {
                var reject = c.attrs.modifiers.column_invisible;
                if (c.attrs.class) {
                    if (c.attrs.class.match(/\boe_edit_only\b/)) {
                        c.attrs.editOnly = true;
                    }
                    if (c.attrs.class.match(/\boe_read_only\b/)) {
                        c.attrs.readOnly = true;
                    }
                }
                if (!reject && c.attrs.widget === 'handle') {
                    self.handleField = c.attrs.name;
                    if (self.isGrouped) {
                        reject = true;
                    }
                }

                if (!reject) {
                    self.columns.push(c);
                }
            });
        },
        _renderHeader: function () {
            var $tr = $('<tr>').append(_.map(this.columns, this._renderHeaderCell.bind(this)));
            return $('<thead>').append($tr);
        },
        _renderHeaderCell: function (node) {
            const { icon, name, string } = node.attrs;
            var field = this.state.fields[name];
            var $th = $('<th>');
            if (name) {
                $th.attr('data-name', name);
            } else if (string) {
                $th.attr('data-string', string);
            } else if (icon) {
                $th.attr('data-icon', icon);
            }
            if (node.attrs.editOnly) {
                $th.addClass('oe_edit_only');
            }
            if (node.attrs.readOnly) {
                $th.addClass('oe_read_only');
            }
            if (!field) {
                return $th;
            }
            var description = string || field.string;
            if (node.attrs.widget) {
                $th.addClass(' o_' + node.attrs.widget + '_cell');
                if (this.state.fieldsInfo.hierarchy[name].Widget.prototype.noLabel) {
                    description = '';
                }
            }
            $th.text(description).attr('tabindex', -1);

            if (field.type === 'float' || field.type === 'integer' || field.type === 'monetary') {
                $th.addClass('o_list_number_th');
            }

            if (config.isDebug()) {
                var fieldDescr = {
                    field: field,
                    name: name,
                    string: description || name,
                    record: this.state,
                    attrs: _.extend({}, node.attrs, this.state.fieldsInfo.hierarchy[name]),
                };
                this._addFieldTooltip(fieldDescr, $th);
            } else {
                $th.attr('title', description);
            }
            return $th;
        },
        _renderBody: function () {
            var self = this;
            var $rows = this._renderRows();
            while ($rows.length < 4) {
                $rows.push(self._renderEmptyRow());
            }
            return $('<tbody>').append($rows);
        },
        _renderRows: function () {
            return this.listData.map(this._renderRow.bind(this));
        },
        _renderRow: function (record) {
            var self = this;
            var $cells = this.columns.map(function (node, index) {
                return self._renderBodyCell(record, node, { mode: 'readonly' });
            });

            var $tr = $('<tr/>', { class: 'o_data_row' }).attr('data-id', record.id).append($cells);
            this._setDecorationClasses(record, $tr);
            return $tr;
        },
        _renderEmptyRow: function () {
            var $td = $('<td>&nbsp;</td>').attr('colspan', this.columns.length);
            return $('<tr>').append($td);
        },
        _renderBodyCell: function (record, node, options) {
            var tdClassName = 'o_data_cell';
            if (node.tag === 'button') {
                tdClassName += ' o_list_button';
            } else if (node.tag === 'field') {
                tdClassName += ' o_field_cell';
                var typeClass = FIELD_CLASSES[this.state.fields[node.attrs.name].type];
                if (typeClass) {
                    tdClassName += (' ' + typeClass);
                }
                if (node.attrs.widget) {
                    tdClassName += (' o_' + node.attrs.widget + '_cell');
                }
            }
            if (node.attrs.editOnly) {
                tdClassName += ' oe_edit_only';
            }
            if (node.attrs.readOnly) {
                tdClassName += ' oe_read_only';
            }
            var $td = $('<td>', { class: tdClassName, tabindex: -1 });

            if (node.attrs.options) {
                var opts = typeof node.attrs.options === 'string' ? JSON.parse(node.attrs.options.replace(/"/g, '<->').replace(/'/g, '"').replace(/<->/g, "'")) : node.attrs.options;
                this._setCellDecorations(record, opts, $td);
            }

            var modifiers = this._registerModifiers(node, record, $td, _.pick(options, 'mode'));
            if (modifiers.invisible && !(options && options.renderInvisible)) {
                return $td;
            }

            if (node.tag === 'button') {
                return $td.append(this._renderButton(record, node));
            } else if (node.tag === 'widget') {
                return $td.append(this._renderWidget(record, node));
            }
            if (node.attrs.widget || (options && options.renderWidgets)) {
                var $el = this._renderFieldWidget(node, record, _.pick(options, 'mode'));
                return $td.append($el);
            }
            this._handleAttributes($td, node);
            var name = node.attrs.name;
            var field = this.state.fields[name];
            var value = record.data[name];
            var formatter = field_utils.format[field.type];
            var formatOptions = {
                escape: true,
                data: record.data,
                isPassword: 'password' in node.attrs,
                digits: node.attrs.digits && JSON.parse(node.attrs.digits),
            };
            var formattedValue = formatter(value, field, formatOptions);
            var title = '';
            if (field.type !== 'boolean') {
                title = formatter(value, field, _.extend(formatOptions, { escape: false }));
            }
            return $td.html(formattedValue).attr('title', title);
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
        _setDecorationClasses: function (record, $tr) {
            _.each(this.rowDecorations, function (expr, decoration) {
                var cssClass = decoration.replace('decoration', 'text');
                $tr.toggleClass(cssClass, py.PY_isTrue(py.evaluate(expr, record.evalContext)));
            });
        },
        _renderFooter: function () {
            var aggregates = {};
            _.each(this.columns, function (column) {
                if ('aggregate' in column) {
                    aggregates[column.attrs.name] = column.aggregate;
                }
            });
            var $cells = this._renderAggregateCells(aggregates);
            return $('<tfoot>').append($('<tr>').append($cells));
        },
        _renderAggregateCells: function (aggregateValues) {
            var self = this;

            return _.map(this.columns, function (column) {
                var $cell = $('<td>');
                if (config.isDebug()) {
                    $cell.addClass(column.attrs.name);
                }
                if (column.attrs.editOnly) {
                    $cell.addClass('oe_edit_only');
                }
                if (column.attrs.readOnly) {
                    $cell.addClass('oe_read_only');
                }
                if (column.attrs.name in aggregateValues) {
                    var field = self.state.fields[column.attrs.name];
                    var value = aggregateValues[column.attrs.name].value;
                    var help = aggregateValues[column.attrs.name].help;
                    var formatFunc = field_utils.format[column.attrs.widget];
                    if (!formatFunc) {
                        formatFunc = field_utils.format[field.type];
                    }
                    var formattedValue = formatFunc(value, field, { escape: true });
                    $cell.addClass('o_list_number').attr('title', help).html(formattedValue);
                }
                return $cell;
            });
        },
        _renderButton: function (record, node) {
            var self = this;
            var nodeWithoutWidth = Object.assign({}, node);
            delete nodeWithoutWidth.attrs.width;
            var $button = viewUtils.renderButtonFromNode(nodeWithoutWidth, {
                extraClass: node.attrs.icon ? 'o_icon_button' : undefined,
                textAsTitle: !!node.attrs.icon,
            });
            this._handleAttributes($button, node);
            this._registerModifiers(node, record, $button);

            if (record.res_id) {
                $button.on("click", function (e) {
                    e.stopPropagation();
                    self.trigger_up('button_clicked', {
                        attrs: node.attrs,
                        record: record,
                    });
                });
            } else {
                if (node.attrs.options.warn) {
                    $button.on("click", function (e) {
                        e.stopPropagation();
                        self.do_warn(_t("Warning"), _t('Please click on the "save" button first.'));
                    });
                } else {
                    $button.prop('disabled', true);
                }
            }
            return $button;
        },
        _updateFooter: function () {
            this._computeAggregates();
            this.$('tfoot').replaceWith(this._renderFooter());
        },
        _onRowClicked: function (ev) {
            if (!ev.target.closest('.o_list_record_selector') && !$(ev.target).prop('special_click')) {
                var id = $(ev.currentTarget).data('id');
                if (id) {
                    this.trigger_up('open_record', { id: id, target: ev.target });
                }
            }
        },
    });

    return HierarchyRenderer;
});