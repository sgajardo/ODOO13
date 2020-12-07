odoo.define('ticket_pro.crash_manager', function (require) {
    "use strict";

    var CrashManager = require('web.CrashManager');
    var rpc = require('web.rpc');
    var session = require('web.session');

    CrashManager.include({
        show_error: function (error) {
            if (session.raise_ticket) {
                rpc.query({
                    model: 'ticket.pro',
                    method: 'create',
                    args: [{
                        title: error.data.message,
                        obs: error.data.debug
                    }]
                });
            }
            return this._super(error);
        }
    });
});