$(function() {
    function MaintenanceViewModel(parameters) {
        var self = this;
        var cancelTemperatureUpdate = false;
        var fetchTemperatureRetries = 5;
        var TARGET_TEMPERATURE = 200;

        self.loginState = parameters[0];
        self.users = parameters[1];
        self.printerProfiles = parameters[2];
        self.printerState = parameters[3];

        self.receiving = ko.observable(false);
        self.sending = ko.observable(false);
        self.callbacks = [];

        self.commandLock = ko.observable(false);
        self.operationLock = ko.observable(false);

        self.maintenanceDialog = $('#maintenance_dialog');
        self.filamentProfiles = ko.observableArray();
        self.selectedFilament = ko.observable();
        self.filamentResponse = ko.observable(false);
        self.filamentResponseError = ko.observable(false);

        self.show = function() {
            // show settings, ensure centered position
            self.maintenanceDialog.modal({
                minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });

            // Gets the available filament list
            self._getFilamentProfiles();

            return false;
        };

        self.hide = function() {
            self.maintenanceDialog.modal("hide");
        };

        self._heatingDone = function() {
            $.ajax({
                url: API_BASEURL + "maintenance/heating_done",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                success: function() {

                },
                error: function() {

                }
            });
        }

        /***************************************************************************/
        /*******                   Filament Change functions            ************/
        /***************************************************************************/
        self.startHeating = function() {
            cancelTemperatureUpdate = false;
            self.commandLock(true);
            self.operationLock(true);

            $.ajax({
                url: API_BASEURL + "maintenance/start_heating",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    $('#start-heating-btn').addClass('hidden');
                    $('#progress-bar-div').removeClass('hidden');

                    self._updateTempProgress();

                    self.commandLock(false);
                },
                error: function() { self.commandLock(false);  }
            });
        }

        self.cancelHeating = function() {

            $.ajax({
                url: API_BASEURL + "maintenance/cancel_heating",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    $('#start-heating-btn').removeClass('hidden');
                    $('#progress-bar-div').addClass('hidden');

                    var tempProgress = $("#temperature_progress");
                    var tempProgressBar = $(".bar", tempProgress);
                    tempProgressBar.css('width', '0%');
                    tempProgressBar.text('0%');

                    self.commandLock(false);
                    self.operationLock(false);

                },
                error: function() {
                    self.commandLock(false);
                    self.operationLock(false);
                }
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
                            self._heatingDone();

                            $('#step2').removeClass('hidden');
                            $('#step1').addClass('hidden');
                            $('#reset-change-filament').removeClass('hidden');
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
            self.commandLock(true);

            $.ajax({
                url: API_BASEURL + "maintenance/load",
                type: "POST",
                dataType: "json",
                success: function() {
                    self.nextStep4();

                    self.commandLock(false);
                },
                error: function() { self.commandLock(false); }
            });
        }

        self.unloadFilament = function() {
            self.commandLock(true);

            $.ajax({
                url: API_BASEURL + "maintenance/unload",
                type: "POST",
                dataType: "json",
                success: function() {
                    self.nextStep2();

                    self.commandLock(false);
                },
                error: function() { self.commandLock(false); }
            });
        }

        self.nextStep2 = function() {
            $('#step3').removeClass('hidden');
            $('#step2').addClass('hidden');
            $('#step1').addClass('hidden');
        }

        self.nextStep3 = function() {
            $('#step4').removeClass('hidden');
            $('#step3').addClass('hidden');
            $('#step2').addClass('hidden');
        }

        self.nextStep4 = function() {
            $('#step5').removeClass('hidden');
            $('#step4').addClass('hidden');
            $('#step3').addClass('hidden');
            $('#step2').addClass('hidden');

            self.filamentResponse(false);
            self.filamentResponseError(false);
        }

        self.changeFilamentStep0 = function() {
            $('#step2').addClass('hidden');
            $('#step3').addClass('hidden');
            $('#step4').addClass('hidden');
            $('#step5').addClass('hidden');
            $('#step1').removeClass('hidden');

            var tempProgress = $("#temperature_progress");
            var tempProgressBar = $(".bar", tempProgress);

            tempProgressBar.css('width', '0%');
            tempProgressBar.text('0%');

            $('#start-heating-btn').removeClass('hidden');
            $('#progress-bar-div').addClass('hidden');
            $('#reset-change-filament').addClass('hidden');

            self.operationLock(false);
        }

        self.saveFilament = function() {
            self.commandLock(true);

            self.filamentResponse(false);
            self.filamentResponseError(false);

            var data = {
                command: "filament",
                filamentStr: self.selectedFilament()
            };

            $.ajax({
                url: API_BASEURL + "maintenance/save_filament",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function(data) {
                    var response = data['response'];

                    if (response.indexOf('ok') > -1) {
                        self.filamentResponse(true);

                        self.commandLock(false);
                        self.operationLock(false);

                        // Goes to home position
                        self._sendCustomCommand('G28');
                    } else {
                        self.filamentResponseError(true);
                        self.commandLock(false);
                    }
                },
                error: function() {
                    self.commandLock(false);
                    self.operationLock(false);
                    self.filamentResponseError(true);
                }
            });
        }
        self._getFilamentProfiles = function() {

            $.ajax({
                url: API_BASEURL + "maintenance/filament_profiles",
                type: "GET",
                dataType: "json",
                success: function(data) {
                    var profiles = data;
                    self.filamentProfiles.removeAll();

                    _.each(profiles, function(profile) {

                        self.filamentProfiles.push({
                            key: profile.key,
                            name: profile.displayName
                        });
                    });
                }
            });

        }
        /***************************************************************************/
        /**********             end Filament Change functions           ************/
        /***************************************************************************/

        /***************************************************************************/
        /**********                 Calibration functions               ************/
        /***************************************************************************/

        self.startCalibration = function() {
            self.commandLock(true);
            self.operationLock(true);

            $.ajax({
                url: API_BASEURL + "maintenance/start_calibration",
                type: "POST",
                dataType: "json",
                success: function() {
                    self.nextStepCalibration1();

                    self.commandLock(false);
                    $('#reset-calibration').removeClass('hidden');
                },
                error: function() { self.commandLock(false); }
            });
        }

        self.upBigStep = function() {
            self._sendJogCommand('z', -1, 0.5);
        }

        self.upSmallStep = function() {
            self._sendJogCommand('z', -1, 0.05);
        }

        self.downBigStep = function() {
            self._sendJogCommand('z', 1, 0.5);
        }

        self.downSmallStep = function() {
            self._sendJogCommand('z', 1, 0.05);
        }

        self.calibrationStep0 = function() {

            $('#calibrationStep0').removeClass('hidden');
            $('#calibrationStep1').removeClass('hidden');
            $('#calibrationStep2').addClass('hidden');
            $('#calibrationStep3').addClass('hidden');
            $('#calibrationStep4').addClass('hidden');
            $('#calibrationStep5').addClass('hidden');

            $('#calibrationTest1').addClass('hidden');
            $('#calibrationTest2').addClass('hidden');

            self.operationLock(false);
            $('#reset-calibration').addClass('hidden');
        }

        self.nextStepCalibration1 = function() {
            $('#calibrationStep2').removeClass('hidden');
            $('#calibrationStep1').addClass('hidden');
        }

        self.nextStepCalibration2 = function() {

            // Sends the command to go to the next calibration point
            self._nextCalibrationStep();

            $('#calibrationStep3').removeClass('hidden');
            $('#calibrationStep1').addClass('hidden');
            $('#calibrationStep2').addClass('hidden');
            $('#calibrationStep0').addClass('hidden');

        }

        self.nextStepCalibration3 = function() {
            // Sends the command to go to the next calibration point
            self._nextCalibrationStep();

            $('#calibrationStep4').removeClass('hidden');
            $('#calibrationStep3').addClass('hidden');
            $('#calibrationStep1').addClass('hidden');
            $('#calibrationStep2').addClass('hidden');
            $('#calibrationStep0').addClass('hidden');
        }

        self.nextStepCalibration4 = function() {

            // Sends the command to go to the next calibration point
            self._nextCalibrationStep();

            $('#calibrationStep5').removeClass('hidden');
            $('#calibrationStep4').addClass('hidden');
            $('#calibrationStep3').addClass('hidden');
            $('#calibrationStep1').addClass('hidden');
            $('#calibrationStep2').addClass('hidden');
            $('#calibrationStep0').addClass('hidden');
        }

        self.finishCalibration = function() {

            self.calibrationStep0();

            // Sends the home to command to reset the position
            self._sendCustomCommand('G28');
        }

        self.calibrationTestStep1 = function() {

            self.commandLock(true);
            $('#calibrationStep5').addClass('hidden');
            $('#calibrationStep4').addClass('hidden');
            $('#calibrationStep3').addClass('hidden');
            $('#calibrationStep1').addClass('hidden');
            $('#calibrationStep2').addClass('hidden');
            $('#calibrationStep0').addClass('hidden');

            $('#calibrationTest1').removeClass('hidden');
            $('#reset-calibration').addClass('hidden');

            $.ajax({
                url: API_BASEURL + "maintenance/start_calibration_test",
                type: "POST",
                dataType: "json",
                success: function() {
                    self.commandLock(false);
                    self._isRunningCalibrationTest();
                },
                error: function() {
                    self.commandLock(false);
                }
            });
        }

        self.cancelCalibrationTest = function() {

            self.commandLock(true);

            $.ajax({
                url: API_BASEURL + "maintenance/cancel_calibration_test",
                type: "POST",
                dataType: "json",
                success: function() {
                    self.commandLock(false);

                    $('#calibrationStep5').removeClass('hidden');
                    $('#calibrationTest1').addClass('hidden');
                    $('#reset-calibration').removeClass('hidden');
                },
                error: function() {
                    self.commandLock(false);
                }
            });
        }

        self.repeatCalibration = function() {

            $('#calibrationTest2').addClass('hidden');
            $('#calibrationTest2').addClass('hidden');

            self.commandLock(true);

            $.ajax({
                url: API_BASEURL + "maintenance/repeat_calibration",
                type: "POST",
                dataType: "json",
                success: function() {
                    self.calibrationStep0();
                    self.nextStepCalibration1();

                    $('#reset-calibration').removeClass('hidden');

                    self.commandLock(false);
                },
                error: function() { self.commandLock(false); }
            });
        }

        self.calibrationTestStep2 = function() {

            $('#calibrationTest1').addClass('hidden');
            $('#calibrationTest2').removeClass('hidden');
        }

        self._isRunningCalibrationTest = function () {

            $.ajax({
                url: API_BASEURL + "maintenance/running_calibration_test",
                type: "GET",
                dataType: "json",
                success: function(data) {

                    var printing = data['response'];

                    if (printing == false) {
                        //If the test is finished goes to step2
                        self.calibrationTestStep2();
                        return;
                    }
                    setTimeout(function() { self._isRunningCalibrationTest(); }, 10000);

                },
                error: function() {
                    setTimeout(function() { self._isRunningCalibrationTest(); }, 10000);
                }
            });
        }


        self._sendJogCommand = function (axis, direction, distance) {
            self.commandLock(true);
            var data = {
                "command": "jog"
            };
            data[axis] = distance * direction;

            $.ajax({
                url: API_BASEURL + "printer/printhead",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function() {
                    self.commandLock(false);
                },
                error: function() { self.commandLock(false); }
            });
        };

        self._sendCustomCommand = function (command) {
            $.ajax({
                url: API_BASEURL + "printer/command",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({"command": command})
            });
        }

        self._nextCalibrationStep = function() {

            self.commandLock(true);

            $.ajax({
                url: API_BASEURL + "maintenance/calibration_next",
                type: "POST",
                dataType: "json",
                success: function() {
                    self.commandLock(false);
                },
                error: function() { self.commandLock(false); }
            });
        }

        /***************************************************************************/
        /**********             end Calibrations functions              ************/
        /***************************************************************************/

        /***************************************************************************/
        /**********            Extruder maintenance functions           ************/
        /***************************************************************************/

        self.restartExtMaint = function() {
            self.cancelHeatingExtMaint();

            self.extMaintStep0();
        }

        self.extMaintStep0 = function() {
            $('#extMaintStep2').addClass('hidden');
            $('#extMaintStep3').addClass('hidden');
            $('#extMaintStep4').addClass('hidden');
            $('#reset-extruder-maint').addClass('hidden');

            $('#extMaintStep1').removeClass('hidden');
            $('#start-heating-ext-mtn').removeClass('hidden');

        }

        self.nextStepExtMaintenance1 = function() {
            $('#extMaintStep2').removeClass('hidden');
            $('#extMaintStep1').addClass('hidden');
        }

        self.nextStepExtMaint2 = function() {
            $('#extMaintStep3').removeClass('hidden');
            $('#extMaintStep2').addClass('hidden');
            $('#extMaintStep1').addClass('hidden');
            $('#next-step-ext-mtn-3').addClass('hidden');
        }

        self.nextStepExtMaint3 = function() {
            $('#extMaintStep3').addClass('hidden');
            $('#extMaintStep2').addClass('hidden');
            $('#extMaintStep1').addClass('hidden');
            $('#extMaintStep4').removeClass('hidden');
        }

        self.startHeatingExtMaint = function() {
            cancelTemperatureUpdate = false;
            self.commandLock(true);
            self.operationLock(true);


            $.ajax({
                url: API_BASEURL + "maintenance/start_heating",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    $('#start-heating-ext-mtn').addClass('hidden');
                    $('#progress-bar-ext-mtn').removeClass('hidden');
                    $('#reset-extruder-maint').removeClass('hidden');

                    self._updateTempProgressExtMaint();

                    self.commandLock(false);

                    self.nextStepExtMaintenance1();
                },
                error: function() { self.commandLock(false);  }
            });
        }

        self.cancelHeatingExtMaint = function() {

            $.ajax({
                url: API_BASEURL + "maintenance/cancel_heating",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    $('#start-heating-ext-mtn').removeClass('hidden');
                    $('#progress-bar-ext-mtn').addClass('hidden');

                    self.commandLock(false);
                    self.operationLock(false);

                    var tempProgress = $("#temperature-progress-ext-mtn");
                    var tempProgressBar = $(".bar", tempProgress);
                    tempProgressBar.css('width', '0%');
                    tempProgressBar.text('0%');

                    self.extMaintStep0();
                },
                error: function() {
                    self.commandLock(false);
                    self.operationLock(false);
                }
            });

            cancelTemperatureUpdate = true;
        }

        self._updateTempProgressExtMaint = function() {
            fetchTemperatureRetries = 5;

            $.ajax({
                url: API_BASEURL + "maintenance/temperature",
                type: "GET",
                dataType: "json",
                success: function(data) {
                    if (!cancelTemperatureUpdate) {
                        var current_temp = data['temperature'];
                        var progress = ((current_temp / TARGET_TEMPERATURE) * 100).toFixed(0);

                        var tempProgress = $("#temperature-progress-ext-mtn");
                        var tempProgressBar = $(".bar", tempProgress);

                        var progressStr = progress + "%";
                        tempProgressBar.css('width', progressStr);
                        tempProgressBar.text(progressStr);

                        if (progress >= 100) {
                            // Heating is finished, let's move on
                            self._heatingDone();

                            $('#next-step-ext-mtn-3').removeClass('hidden');
                            $('#progress-bar-ext-mtn').addClass('hidden');
                        } else {

                            setTimeout(function() { self._updateTempProgressExtMaint() }, 2000);
                        }
                    }
                },
                error: function() {
                    while (fetchTemperatureRetries > 0)
                        setTimeout(function() { self._updateTempProgressExtMaint() }, 2000);
                        fetchTemperatureRetries -= 1;
                    }
            });
        }

        /***************************************************************************/
        /**********         end Extruder maintenance functions          ************/
        /***************************************************************************/

        /***************************************************************************/
        /**************            Replace nozzle functions           **************/
        /***************************************************************************/

        self.restartReplaceNozzle = function() {
            self.cancelHeatingReplaceNozzle();

            self.replaceNozzleStep0();
        }

        self.replaceNozzleStep0 = function() {
            $('#replaceNozzleStep2').addClass('hidden');
            $('#replaceNozzleStep3').addClass('hidden');
            $('#reset-replace-nozzle').addClass('hidden');

            $('#replaceNozzleStep1').removeClass('hidden');
            $('#start-heating-replace-nozzle').removeClass('hidden');
            $('#next-step-replace-nozzle-2').addClass('hidden');
        }

        self.nextStepReplaceNozzle1 = function() {
            $('#replaceNozzleStep2').removeClass('hidden');
            $('#replaceNozzleStep1').addClass('hidden');
            $('#next-step-replace-nozzle-2').addClass('hidden');
        }

        self.nextStepReplaceNozzle2 = function() {
            $('#replaceNozzleStep3').removeClass('hidden');
            $('#replaceNozzleStep1').addClass('hidden');
            $('#replaceNozzleStep2').addClass('hidden');
        }

        self.startHeatingReplaceNozzle = function() {
            cancelTemperatureUpdate = false;
            self.commandLock(true);
            self.operationLock(true);

            $.ajax({
                url: API_BASEURL + "maintenance/start_heating",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    $('#start-heating-replace-nozzle').addClass('hidden');
                    $('#progress-bar-replace-nozzle').removeClass('hidden');
                    $('#reset-replace-nozzle').removeClass('hidden');

                    self._updateTempProgressReplaceNozzle();

                    self.commandLock(false);

                },
                error: function() { self.commandLock(false);  }
            });
        }

        self.cancelHeatingReplaceNozzle = function() {

            $.ajax({
                url: API_BASEURL + "maintenance/cancel_heating",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    $('#start-heating-replace-nozzle').removeClass('hidden');
                    $('#progress-bar-replace-nozzle').addClass('hidden');

                    var tempProgress = $("#temperature-progress-replace-nozzle");
                    var tempProgressBar = $(".bar", tempProgress);
                    tempProgressBar.css('width', '0%');
                    tempProgressBar.text('0%');

                    self.commandLock(false);
                    self.operationLock(false);

                    self.replaceNozzleStep0();
                },
                error: function() {
                    self.commandLock(false);
                    self.operationLock(false);
                }
            });

            cancelTemperatureUpdate = true;
        }

        self._updateTempProgressReplaceNozzle = function() {
            fetchTemperatureRetries = 5;

            $.ajax({
                url: API_BASEURL + "maintenance/temperature",
                type: "GET",
                dataType: "json",
                success: function(data) {
                    if (!cancelTemperatureUpdate) {
                        var current_temp = data['temperature'];
                        var progress = ((current_temp / TARGET_TEMPERATURE) * 100).toFixed(0);

                        var tempProgress = $("#temperature-progress-replace-nozzle");
                        var tempProgressBar = $(".bar", tempProgress);

                        var progressStr = progress + "%";
                        tempProgressBar.css('width', progressStr);
                        tempProgressBar.text(progressStr);

                        if (progress >= 100) {
                            // Heating is finished, let's move on
                            self._heatingDone();

                            $('#progress-bar-replace-nozzle').addClass('hidden');
                            $('#next-step-replace-nozzle-2').removeClass('hidden');
                        } else {

                            setTimeout(function() { self._updateTempProgressReplaceNozzle() }, 2000);
                        }
                    }
                },
                error: function() {
                    while (fetchTemperatureRetries > 0)
                        setTimeout(function() { self._updateTempProgressReplaceNozzle() }, 2000);
                        fetchTemperatureRetries -= 1;
                    }
            });
        }

        /***************************************************************************/
        /*************          end Replace nozzle functions           *************/
        /***************************************************************************/
    }

    OCTOPRINT_VIEWMODELS.push([
        MaintenanceViewModel,
        ["loginStateViewModel", "usersViewModel", "printerProfilesViewModel", "printerStateViewModel"],
        ["#maintenance_dialog", "#navbar_maintenance"]
    ]);
});