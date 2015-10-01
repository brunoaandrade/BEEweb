$(function() {
    function MaintenanceViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.users = parameters[1];
        self.printerProfiles = parameters[2];
        self.printerState = parameters[3];

        self.receiving = ko.observable(false);
        self.sending = ko.observable(false);
        self.callbacks = [];
        self.maintenanceDialog = $('#maintenance_dialog');

        self.show = function() {
            // show settings, ensure centered position
            self.maintenanceDialog.modal({
                minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });

            return false;
        };

        self.hide = function() {
            self.maintenanceDialog.modal("hide");
        };

        self.startHeating = function() {
            var data = {
                target: 210
            };

            $.ajax({
                url: API_BASEURL + "maintenance/start_heating",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function() {
                    $('#start-heating-btn').hide();
                    $('#cancel-heating-btn').show();
                },
                error: function() {  }
            });
        }

        self.cancelHeating = function() {

        }

        self.requestData = function(callback) {
            if (self.receiving()) {
                if (callback) {
                    self.callbacks.push(callback);
                }
                return;
            }

            self.receiving(true);
            $.ajax({
                url: API_BASEURL + "settings",
                type: "GET",
                dataType: "json",
                success: function(response) {
                    if (callback) {
                        self.callbacks.push(callback);
                    }

                    try {
                        self.fromResponse(response);

                        var cb;
                        while (self.callbacks.length) {
                            cb = self.callbacks.shift();
                            try {
                                cb();
                            } catch(exc) {
                                log.error("Error calling settings callback", cb, ":", (exc.stack || exc));
                            }
                        }
                    } finally {
                        self.receiving(false);
                        self.callbacks = [];
                    }
                },
                error: function(xhr) {
                    self.receiving(false);
                }
            });
        };

    }

    OCTOPRINT_VIEWMODELS.push([
        MaintenanceViewModel,
        ["loginStateViewModel", "usersViewModel", "printerProfilesViewModel", "printerStateViewModel"],
        ["#maintenance_dialog", "#navbar_maintenance"]
    ]);
});
