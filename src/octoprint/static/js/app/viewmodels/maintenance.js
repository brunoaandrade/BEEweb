$(function() {
    function MaintenanceViewModel(parameters) {
        var self = this;
        var TARGET_TEMPERATURE = 210;
        var cancelTemperatureUpdate = false;
        var fetchTemperatureRetries = 5;

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

        /***************************************************************************/
        /*******                   Filament Change functions            ************/
        /***************************************************************************/
        self.startHeating = function() {
            var data = {
                command: "target",
                targets: {
                    'tool0': TARGET_TEMPERATURE
                }
            };

            $.ajax({
                url: API_BASEURL + "maintenance/start_heating",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function() {
                    $('#start-heating-btn').addClass('hidden');
                    $('#progress-bar-div').removeClass('hidden');

                    self._updateTempProgress();
                },
                error: function() {  }
            });
        }

        self.cancelHeating = function() {
            var data = {
                command: "target",
                targets: {
                    'tool0': 0
                }
            };

            $.ajax({
                url: API_BASEURL + "maintenance/start_heating",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function() {
                    $('#start-heating-btn').removeClass('hidden');
                    $('#progress-bar-div').addClass('hidden');
                },
                error: function() {  }
            });

            cancelTemperatureUpdate = true;
        }

        self._updateTempProgress = function() {

            fetchTemperatureRetries = 5;

            $.ajax({
                url: API_BASEURL + "maintenance/temperature",
                type: "GET",
                dataType: "json",
                success: function(data) {
                    if (!cancelTemperatureUpdate) {
                        var current_temp = data['temperature'];
                        var progress = ((current_temp / TARGET_TEMPERATURE) * 100).toFixed(0);

                        var tempProgress = $("#temperature_progress");
                        var tempProgressBar = $(".bar", tempProgress);

                        var progressStr = progress + "%";
                        tempProgressBar.css('width', progressStr);
                        tempProgressBar.text(progressStr);

                        if (progress >= 100) {
                            // Heating is finished, let's move on
                            $('#step2').removeClass('hidden');
                            $('#step1').addClass('hidden');
                        } else {

                            setTimeout(function() { self._updateTempProgress() }, 2000);
                        }
                    }
                },
                error: function() {
                    while (fetchTemperatureRetries > 0)
                        setTimeout(function() { self._updateTempProgress() }, 2000);
                        fetchTemperatureRetries -= 1;
                    }
            });
        }

        self.loadFilament = function() {
            $.ajax({
                url: API_BASEURL + "maintenance/load",
                type: "POST",
                dataType: "json",
                success: function() { },
                error: function() {  }
            });
        }

        self.unloadFilament = function() {
            $.ajax({
                url: API_BASEURL + "maintenance/unload",
                type: "POST",
                dataType: "json",
                success: function() {
                    $('#step3').removeClass('hidden');
                    $('#step2').addClass('hidden');
                },
                error: function() {  }
            });
        }

        self.nextStep3 = function() {
            $('#step4').removeClass('hidden');
            $('#step3').addClass('hidden');
        }

        self.nextStep4 = function() {
            $('#step5').removeClass('hidden');
            $('#step4').addClass('hidden');
        }

        /***************************************************************************/
        /*******               end Filament Change functions            ************/
        /***************************************************************************/

    }

    OCTOPRINT_VIEWMODELS.push([
        MaintenanceViewModel,
        ["loginStateViewModel", "usersViewModel", "printerProfilesViewModel", "printerStateViewModel"],
        ["#maintenance_dialog", "#navbar_maintenance"]
    ]);
});
