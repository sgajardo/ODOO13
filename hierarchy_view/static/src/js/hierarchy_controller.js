odoo.define('hierarchy_view.controller', function (require) {
    "use strict";

    var BasicController = require('web.BasicController');
    var core = require('web.core');
    
    var qweb = core.qweb;

    var HierarchyController = BasicController.extend({
        buttons_template: 'HierarchyView.buttons',
        events: {
            'click .o_hierarchy_button_add': '_onClickCreate',
            'click .o_hierarchy_button_unfold': '_onClickUnfold',
            'click .o_hierarchy_button_fold': '_onClickFold',
        },
        renderButtons: function ($node) {
            this.$buttons = $(qweb.render(this.buttons_template, {widget: this}));
            this.$buttons.appendTo($node);
        },
        _onClickCreate: function () {
            this.trigger_up('switch_view', {view_type: 'form', res_id: undefined});
        },
        _onClickUnfold: function () {
            this.$('.o_hierarchy_sidebar_container .oh_title>.fa-caret-right').siblings('a').trigger('click');
        },
        _onClickFold: function () {
            _.each(this.$('.o_hierarchy_sidebar_container .oh_title>.fa-caret-down').siblings('a').sort((x, y) => (y.dataset.parentId || 0) - (x.dataset.parentId || 0)), function (el) {
                $(el).trigger('click');
            });
        },
    });

    return HierarchyController;
});