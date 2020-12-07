odoo.define('folder_view.view', function (require) {
    "use strict";

    var core = require('web.core');
    var viewRegistry = require('web.view_registry');
    var ListView = require('web.ListView');
    var FolderRenderer = require('folder_view.renderer');

    var _lt = core._lt;

    var FolderView = ListView.extend({
        accesskey: 'f',
        display_name: _lt('Folder'),
        icon: 'fa-folder-open',
        viewType: 'folder',
        config: _.extend({}, ListView.prototype.config, {
            Renderer: FolderRenderer,
        }),
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);
            this.loadParams.domain = (this.loadParams.domain || []).push(['parent_id', '=', false]);
        },
    });

    viewRegistry.add('folder', FolderView);
    return FolderView;
});