odoo.define('hierarchy_view.view', function (require) {
    "use strict";

    var core = require('web.core');
    var viewRegistry = require('web.view_registry');
    var BasicView = require('web.BasicView');
    var HierarchyRenderer = require('hierarchy_view.renderer');
    var HierarchyController = require('hierarchy_view.controller');
    var HierarchyModel = require('hierarchy_view.model');
    var Context = require('web.Context');

    var _lt = core._lt;

    var HierarchyView = BasicView.extend({
        accesskey: 'h',
        display_name: _lt('Hierarchy'),
        icon: 'fa-sitemap',
        withSearchBar: false,
        searchMenuTypes: [],
        config: _.extend({}, BasicView.prototype.config, {
            Controller: HierarchyController,
            Renderer: HierarchyRenderer,
            Model: HierarchyModel,
        }),
        viewType: 'hierarchy',
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);
            this.loadParams.domain = (this.loadParams.domain || []).push(['parent_id', '=', false]);
        },
        getController: function (parent) {
            return this._loadSubviews(parent).then(this._super.bind(this, parent));
        },
        _loadSubviews: function (parent) {
            var self = this;
            var defs = [];
            if (this.loadParams && this.loadParams.fieldsInfo) {
                var fields = this.loadParams.fields;

                _.each(this.loadParams.fieldsInfo.hierarchy, function (attrs, fieldName) {
                    var field = fields[fieldName];
                    if (!field) {
                        return;
                    }
                    if (field.type !== 'one2many' && field.type !== 'many2many') {
                        return;
                    }
                    if (attrs.Widget.prototype.useSubview && !attrs.views[attrs.mode]) {
                        var context = {};
                        var regex = /'([a-z]*_view_ref)' *: *'(.*?)'/g;
                        var matches;
                        while (matches = regex.exec(attrs.context)) {
                            context[matches[1]] = matches[2];
                        }

                        // Remove *_view_ref coming from parent view
                        var refinedContext = _.pick(self.loadParams.context, function (value, key) {
                            return key.indexOf('_view_ref') === -1;
                        });
                        // Specify the main model to prevent access rights defined in the context
                        // (e.g. create: 0) to apply to subviews. We use here the same logic as
                        // the one applied by the server for inline views.
                        refinedContext.base_model_name = self.controllerParams.modelName;
                        defs.push(parent.loadViews(
                            field.relation,
                            new Context(context, self.userContext, refinedContext).eval(),
                            [[null, attrs.mode === 'tree' ? 'list' : attrs.mode]])
                            .then(function (views) {
                                for (var viewName in views) {
                                    // clone to make runbot green?
                                    attrs.views[viewName] = self._processFieldsView(views[viewName], viewName);
                                    attrs.views[viewName].fields = attrs.views[viewName].viewFields;
                                    self._processSubViewAttrs(attrs.views[viewName], attrs);
                                }
                                self._setSubViewLimit(attrs);
                            }));
                    } else {
                        self._setSubViewLimit(attrs);
                    }
                });
            }
            return Promise.all(defs);
        },
        _setSubViewLimit: function (attrs) {
            var view = attrs.views && attrs.views[attrs.mode];
            var limit = view && view.arch.attrs.limit && parseInt(view.arch.attrs.limit);
            if (!limit && attrs.widget === 'many2many_tags') {
                limit = 1000;
            }
            attrs.limit = limit || 40;
        },
    });

    viewRegistry.add('hierarchy', HierarchyView);
    return HierarchyView;
});