odoo.define('base_bim_2.Hierarchy', function (require) {
    "use strict";

    var HierarchyRenderer = require('hierarchy_view.renderer');
    var HierarchyController = require('hierarchy_view.controller');
    var core = require('web.core');

    var QWeb = core.qweb;

    HierarchyRenderer.include({
        events: _.extend({}, HierarchyRenderer.prototype.events, {
            'click .oh_contextmenu [data-action="cert_massive"]': 'certMassive',
            'click .oh_contextmenu [data-action="deep_copy"]': 'copyRecord',
            'click .oh_contextmenu [data-action="deep_cut"]': 'cutRecord',
            'click .oh_contextmenu [data-action="deep_paste"]': 'pasteRecord',
            'click .oh_contextmenu [data-action="move_up"]': 'moveRecord',
            'click .oh_contextmenu [data-action="move_down"]': 'moveRecord',
            'click .oh_contextmenu [data-action="update_concept"]': 'updateRecord',
            'click .o_bim_measures_visible': 'toggleMeasuresVisible',
        }),
        start: function () {
            var self = this;

            var checkParams = this._rpc({
                model: 'ir.config_parameter',
                method: 'get_param',
                args: ['bim.measures.always.open'],
            }).then(function (param) {
                self.measuresAlwaysOpen = param === 'True';
            });

            return Promise.all([checkParams, this._super()]);
        },
        display_children: function (ev) {
            var model = this.getParent().model;
            var res_id = $(ev.currentTarget).get()[0].dataset.resId;
            var record = model.get(res_id);
            var node = this.arch.children.find(f => f.attrs.name === 'measuring_ids');
            this.defs = this.defs || [];
            var $measures = record.data.measuring_ids.count > 0 ? QWeb.render('bim.HierarchyMeasures', { note: record.data.note, measuresOpen: this.measuresAlwaysOpen }) : '';
            this.$('.bimHierarchyMeasuresPlaceholder').html($measures);
            if (record.data.measuring_ids) {
                var self = this;
                var measuring_data = record.data.measuring_ids;
                model.load({
                    context: measuring_data.context,
                    domain: [['id', 'in', measuring_data.res_ids]],
                    fields: measuring_data.fields,
                    fieldsInfo: measuring_data.fieldsInfo,
                    viewType: 'list',
                    limit: 6,
                    modelName: measuring_data.model,
                    type: 'list',
                }).then(function (res_id) {
                    record.data.measuring_ids = model.get(res_id);
                    var widget = self._renderFieldWidget(node, record);
                    self.$('.bimHierarchyMeasuresPlaceholder .card-body').html(widget);
                    self._rpc({
                        model: 'bim.concepts',
                        method: 'get_first_attachment',
                        args: [record.data.id],
                    }).then(function (image_b64) {
                        if (image_b64) {
                            self.$('.bimHierarchyMeasuresPlaceholder .card-body').prepend(`<img style="padding: 5px; max-height: 180px; max-width: 30%;" src="data:image/png;base64,${image_b64}" alt="img"/>`);
                        }
                    });
                });
            }
            this._super.apply(this, arguments);
        },
        _postProcessField: function (widget, node) {
            if (node.tag === 'field' && node.attrs.name === 'measuring_ids') {
                widget.$el.addClass('w-100');
            }
            return this._super.apply(this, arguments);
        },
        context_menu_parent: function (ev) {
            this._super.apply(this, arguments);
            var self = this;
            $.when(this._rpcPasteContextmenu(true)).then(function () {
                self.$contextmenu.css('top', ev.pageY).css('left', ev.pageX).show();
            });
        },
        context_menu_child: function (ev) {
            this._super.apply(this, arguments);
            this._rpcPasteContextmenu(false);
        },
        _rpcPasteContextmenu: function (touch_outside) {
            var self = this;
            return this._rpc({
                model: 'res.users',
                method: 'read',
                args: [[this.state.context.uid], ['copied_bim_concept_id', 'cut_bim_concept_id']],
            }).then(function (users) {
                var user = users[0];
                var $paste_btn = self.$contextmenu.find('[data-action="deep_paste"]');
                if (user.copied_bim_concept_id || user.cut_bim_concept_id) {
                    $paste_btn.removeClass('d-none').data('id', user.copied_bim_concept_id || user.cut_bim_concept_id);
                } else {
                    $paste_btn.addClass('d-none').removeAttr('data-id');
                }
                if (touch_outside) {
                    self.$contextmenu.find('[data-action!="deep_paste"]').addClass('d-none');
                } else {
                    self.$contextmenu.find('[data-action!="deep_paste"]').removeClass('d-none');
                }
            });
        },
        copyRecord: function () {
            var res_id = this.$(`.oh_title [data-res-id="${this.contextResId}"]`).get()[0].dataset.id;
            this._rpc({
                model: 'res.users',
                method: 'write',
                args: [[this.state.context.uid], { copied_bim_concept_id: res_id, cut_bim_concept_id: false }],
            });
        },
        cutRecord: function () {
            var res_id = this.$(`.oh_title [data-res-id="${this.contextResId}"]`).get()[0].dataset.id;
            this._rpc({
                model: 'res.users',
                method: 'write',
                args: [[this.state.context.uid], { cut_bim_concept_id: res_id, copied_bim_concept_id: false }],
            });
        },
        pasteRecord: function () {
            var self = this;
            var $a = this.contextResId ? this.$(`.oh_title [data-res-id="${this.contextResId}"]`) : false;
            var $li = $a ? $a.closest('li') : false;
            var parent_id = $a ? $a.get()[0].dataset.id : false;
            this._rpc({
                model: 'res.users',
                method: 'copy_bim_concept',
                args: [this.state.context.uid, parent_id],
                context: this.state.context,
            }).then(function (new_id) {
                if (!new_id) {
                    alert('Solo puedes pegar capítulos en la raiz del presupuesto.');
                    return false;
                }
                // Verifying that record is not present in this view, in case it is, just remove it
                var $a_dupe = self.$(`.oh_title a[data-id="${new_id}"]`);
                if ($a_dupe.length) {
                    var $li_dupe = $a_dupe.closest('li');
                    var $ul_dupe = $li_dupe.parent();
                    $li_dupe.remove();
                    if (!$ul_dupe.children().length) {
                        var $oh_title_dupe = $ul_dupe.siblings('.oh_title');
                        $oh_title_dupe.find('>.fa-caret-down').removeClass('fa-caret-down').addClass('fa-angle-right text-muted');
                        $oh_title_dupe.find('>a').get()[0].dataset.childs = false;
                        $ul_dupe.remove();
                    }
                }

                if ($a && !$a.data('childs')) {
                    $a.get()[0].dataset.childs = true;
                    $li.find('.oh_title .fa.fa-angle-right').removeClass('fa-angle-right text-muted').addClass('fa-caret-right');
                }
                if ($li) {
                    self.refresh_record($li);
                } else {
                    var model = self.getParent().model;
                    model.load({
                        context: self.state.context,
                        domain: [['id', '=', new_id]],
                        fields: self.state.fields,
                        fieldsInfo: self.state.fieldsInfo,
                        viewType: 'hierarchy',
                        modelName: self.state.model,
                        type: 'list',
                    }).then(function (res_id) {
                        var new_state = model.get(res_id);
                        if (!$a_dupe.length) {
                            self.state.data = self.state.data.concat(new_state.data);
                        }
                        self.renderSidebar();
                    });
                }
            });
        },
        moveRecord: function (ev) {
            var action = $(ev.currentTarget).get(0).dataset.action;
            var $a = $(`.oh_title [data-res-id="${this.contextResId}"]`);
            var res_id = parseInt($a.get()[0].dataset.id);
            var $li = $a.closest('li');
            if ((!$li.prev().length && action === 'move_up') || (!$li.next().length && action === 'move_down')) return;
            this._rpc({
                model: 'bim.concepts',
                method: 'move_record',
                args: [res_id, action],
            }).then(function () {
                if (action === 'move_up') {
                    var $prev = $li.prev();
                    $li.insertBefore($prev);
                } else {
                    var $next = $li.next();
                    $li.insertAfter($next);
                }
            });
        },
        updateRecord: function () {
            var $a = $(`.oh_title [data-res-id="${this.contextResId}"]`);
            var res_id = parseInt($a.get()[0].dataset.id);
            this._rpc({
                model: 'bim.concepts',
                method: 'update_concept',
                args: [res_id],
            }).then(function () {
                $a.trigger('click');
                $a.trigger('click');
            });
        },
        certMassive: function () {
            var $a = $(`.oh_title [data-res-id="${this.contextResId}"]`);
            var res_id = parseInt($a.get()[0].dataset.id);
            this._rpc({
                model: 'bim.concepts',
                method: 'cert_massive',
                args: [res_id],
            }).then(function () {
                $a.trigger('click');
                $a.trigger('click');
            });
        },
        toggleMeasuresVisible: function () {
            if (this.measuresAlwaysOpen) {
                this.$('.o_bim_measures_visible i').removeClass('fa-check-square-o').addClass('fa-square-o');
            } else {
                this.$('.o_bim_measures_visible i').removeClass('fa-square-o').addClass('fa-check-square-o');
            }
            this.measuresAlwaysOpen = !this.measuresAlwaysOpen;
            this._rpc({
                model: 'ir.config_parameter',
                method: 'set_param_sudo',
                args: ['bim.measures.always.open', this.measuresAlwaysOpen ? 'True' : 'False'],
            });
        },
    });

    HierarchyController.include({
        events: _.extend({}, HierarchyController.prototype.events, {
            'click [aria-labelledby="bim_budget_type_dropdown"] button': '_changeBudgetType',
            'click #update_budget_amount': '_updateBudgetAmount',
        }),
        _changeBudgetType: function (ev) {
            var self = this;
            var $button = $(ev.currentTarget);
            if ($button.hasClass('active')) {
                return;
            }
            var type = $button.data('type');
            var budget_id = this.initialState.context.default_budget_id;
            this._rpc({
                model: 'bim.budget',
                method: 'write',
                args: [budget_id, { type: type }]
            }).then(function () {
                self.__parentedParent.doAction({
                    type: 'ir.actions.act_window',
                    name: 'Concepto',
                    res_model: 'bim.concepts',
                    views: [[false, 'hierarchy'], [false, 'folder'], [false, 'list'], [false, 'form']],
                    domain: self.initialState.domain,
                }, {
                    replace_last_action: true,
                    additional_context: {
                        budget_type: type,
                        default_budget_id: budget_id,
                    },
                });
            });
        },
        _updateBudgetAmount: function () {
            var self = this;
            var budget_id = this.initialState.context.default_budget_id;
            var type = this.$('[aria-labelledby="bim_budget_type_dropdown"] .active').get(0).dataset.type;
            this._rpc({
                model: 'bim.budget',
                method: 'update_amount',
                args: [budget_id],
            }).then(function () {
                self.__parentedParent.doAction({
                    type: 'ir.actions.act_window',
                    name: 'Concepto',
                    res_model: 'bim.concepts',
                    views: [[false, 'hierarchy'], [false, 'folder'], [false, 'list'], [false, 'form']],
                    domain: self.initialState.domain,
                }, {
                    replace_last_action: true,
                    additional_context: {
                        budget_type: type,
                        default_budget_id: budget_id,
                    },
                });
            });
        }
    });
});