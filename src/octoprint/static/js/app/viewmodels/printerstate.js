$(function() {
    function PrinterStateViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.printerProfiles = parameters[1];

        self.stateString = ko.observable(undefined);
        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isHeating = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);
        self.isSdReady = ko.observable(undefined);

        self.stateClass = ko.observable(undefined);
        self.isShutdown = ko.observable(undefined);

        self.insufficientFilament = ko.observable(false);
        self.ignoredInsufficientFilament = ko.observable(false);

        self.enablePrint = ko.pureComputed(function() {
            return self.isOperational() && self.isReady() && !self.isPrinting() && !self.isHeating()
            && self.loginState.isUser() && self.filename() != undefined;
        });
        self.enablePause = ko.pureComputed(function() {
            return self.isOperational() && (self.isPrinting() || self.isPaused() || self.isShutdown()) && self.loginState.isUser();
        });
        self.enableCancel = ko.pureComputed(function() {
            return (self.isOperational() || (self.isPrinting() || self.isPaused()))
            && self.loginState.isUser() && self.filename() != undefined;
        });

        self.filename = ko.observable(undefined);
        self.filepath = ko.observable(undefined);
        self.progress = ko.observable(undefined);
        self.filesize = ko.observable(undefined);
        self.filepos = ko.observable(undefined);
        self.printTime = ko.observable(undefined);
        self.printTimeLeft = ko.observable(undefined);
        self.printTimeLeftOrigin = ko.observable(undefined);
        self.sd = ko.observable(undefined);
        self.timelapse = ko.observable(undefined);

        self.busyFiles = ko.observableArray([]);

        self.filament = ko.observableArray([]);
        self.estimatedPrintTime = ko.observable(undefined);
        self.lastPrintTime = ko.observable(undefined);

        self.currentHeight = ko.observable(undefined);

        self.TITLE_PRINT_BUTTON_PAUSED = gettext("Restarts the print job from the beginning");
        self.TITLE_PRINT_BUTTON_UNPAUSED = gettext("Starts the print job");
        self.TITLE_PAUSE_BUTTON_PAUSED = gettext("Resumes the print job");
        self.TITLE_PAUSE_BUTTON_UNPAUSED = gettext("Pauses the print job");

        self.titlePrintButton = ko.observable(self.TITLE_PRINT_BUTTON_UNPAUSED);
        self.titlePauseButton = ko.observable(self.TITLE_PAUSE_BUTTON_UNPAUSED);

        self.printerLogo = ko.computed(function() {
            var logo = "";

            if (self.isErrorOrClosed() !== undefined && !self.isErrorOrClosed() && !self.isError()) {
                var profile = self.printerProfiles.currentProfileData().id();
                if (profile == "_default") {
                    profile = "beethefirst";
                }
                logo = "/static/img/logo_" + profile + ".png";
            }

            return logo;
        });

        self.estimatedPrintTimeString = ko.pureComputed(function() {
            if (self.lastPrintTime())
                return formatFuzzyPrintTime(self.lastPrintTime());
            if (self.estimatedPrintTime())
                return formatFuzzyPrintTime(self.estimatedPrintTime());
            return "-";
        });
        self.byteString = ko.pureComputed(function() {
            if (!self.filesize())
                return "-";
            var filepos = self.filepos() ? formatSize(self.filepos()) : "-";
            return filepos + " / " + formatSize(self.filesize());
        });
        self.heightString = ko.pureComputed(function() {
            if (!self.currentHeight())
                return "-";
            return _.sprintf("%.02fmm", self.currentHeight());
        });
        self.printTimeString = ko.pureComputed(function() {
            if (!self.printTime())
                return "-";
            return formatDuration(self.printTime());
        });
        self.printTimeLeftString = ko.pureComputed(function() {
            if (self.printTimeLeft() == undefined) {
                if (!self.printTime() || !(self.isPrinting() || self.isPaused())) {
                    return "-";
                } else {
                    return gettext("Still stabilizing...");
                }
            } else {
                return formatFuzzyPrintTime(self.printTimeLeft());
            }
        });
        self.printTimeLeftOriginString = ko.pureComputed(function() {
            var value = self.printTimeLeftOrigin();
            switch (value) {
                case "linear": {
                    return gettext("Based on a linear approximation (very low accuracy, especially at the beginning of the print)");
                }
                case "analysis": {
                    return gettext("Based on the estimate from analysis of file (medium accuracy)");
                }
                case "mixed-analysis": {
                    return gettext("Based on a mix of estimate from analysis and calculation (medium accuracy)");
                }
                case "average": {
                    return gettext("Based on the average total of past prints of this model with the same printer profile (usually good accuracy)");
                }
                case "mixed-average": {
                    return gettext("Based on a mix of average total from past prints and calculation (usually good accuracy)");
                }
                case "estimate": {
                    return gettext("Based on the calculated estimate (best accuracy)");
                }
                default: {
                    return "";
                }
            }
        });
        self.printTimeLeftOriginClass = ko.pureComputed(function() {
            var value = self.printTimeLeftOrigin();
            switch (value) {
                default:
                case "linear": {
                    return "text-error";
                }
                case "analysis":
                case "mixed-analysis": {
                    return "text-warning";
                }
                case "average":
                case "mixed-average":
                case "estimate": {
                    return "text-success";
                }
            }
        });
        self.progressString = ko.pureComputed(function() {
            if (!self.progress())
                return 0;
            return self.progress();
        });
        self.progressBarString = ko.pureComputed(function() {
            if (!self.progress()) {
                return "";
            }
            return _.sprintf("%d%%", self.progress());
        });
        self.pauseString = ko.pureComputed(function() {
            if (self.isPaused())
                return gettext("Continue");
            else
                return gettext("Pause");
        });

        self.timelapseString = ko.pureComputed(function() {
            var timelapse = self.timelapse();

            if (!timelapse || !timelapse.hasOwnProperty("type"))
                return "-";

            var type = timelapse["type"];
            if (type == "zchange") {
                return gettext("On Z Change");
            } else if (type == "timed") {
                return gettext("Timed") + " (" + timelapse["options"]["interval"] + " " + gettext("sec") + ")";
            } else {
                return "-";
            }
        });

        self.fromCurrentData = function(data) {
            self._fromData(data);
        };

        self.fromHistoryData = function(data) {
            self._fromData(data);
        };

        self.fromTimelapseData = function(data) {
            self.timelapse(data);
        };

        self._processStateClass = function() {
            self.stateClass("text-black");

            /*if (self.isOperational()) {
                self.stateClass("text-success");
            }
            if (self.isPaused()) {
                self.stateClass("text-black");
            }
            if (self.isHeating()) {
                self.stateClass("text-error");
            }
            if (self.isPrinting()) {
                self.stateClass("text-primary");
            }
            if (self.isShutdown()) {
                self.stateClass("text-black");
            }
            if (self.isErrorOrClosed()) {
                self.stateClass("text-warning");
            } */
        };

        self._fromData = function(data) {
            self._processStateData(data.state);
            self._processJobData(data.job);
            self._processProgressData(data.progress);
            self._processZData(data.currentZ);
            self._processBusyFiles(data.busyFiles);

            self._processStateClass();
        };

        self._processStateData = function(data) {
            var prevPaused = self.isPaused();

            self.stateString(gettext(data.text));
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isSdReady(data.flags.sdReady);
            self.isHeating(data.flags.heating);
            self.isShutdown(data.flags.shutdown);

            if (self.isPaused() != prevPaused) {
                if (self.isPaused()) {
                    self.titlePrintButton(self.TITLE_PRINT_BUTTON_PAUSED);
                    self.titlePauseButton(self.TITLE_PAUSE_BUTTON_PAUSED);
                } else {
                    self.titlePrintButton(self.TITLE_PRINT_BUTTON_UNPAUSED);
                    self.titlePauseButton(self.TITLE_PAUSE_BUTTON_UNPAUSED);
                }
            }

            // If the print job is running show the print panel (print or shutdown states)
            // This is used when the page is reloaded and the print info must be shown
            if (self.isPrinting() || self.isShutdown()) {
                if (!$("#state").hasClass('in')) {
                    $("#state").collapse("show");
                }
            }
        };

        self._processJobData = function(data) {
            if (data.file) {
                self.filename(data.file.name);
                self.filepath(data.file.path);
                self.filesize(data.file.size);
                self.sd(data.file.origin == "sdcard");
            } else {
                self.filename(undefined);
                self.filepath(undefined);
                self.filesize(undefined);
                self.sd(undefined);
            }

            self.estimatedPrintTime(data.estimatedPrintTime);
            self.lastPrintTime(data.lastPrintTime);

            var result = [];
            if (data.filament && typeof(data.filament) == "object" && _.keys(data.filament).length > 0) {
                for (var key in data.filament) {
                    if (!_.startsWith(key, "tool") || !data.filament[key] || !data.filament[key].hasOwnProperty("length") || data.filament[key].length <= 0) continue;

                    result.push({
                        name: ko.observable(gettext("Tool") + " " + key.substr("tool".length)),
                        data: ko.observable(data.filament[key])
                    });
                }
            }
            self.filament(result);

            // Signals that there is no filament available in the spool
            if (data.filament && data.filament['tool0']) {

                self.insufficientFilament(false);

                if (data.filament['tool0']['insufficient'] == true) {
                    self.insufficientFilament(true);
                }
            }
        };

        self._processProgressData = function(data) {
            if (data.completion) {
                self.progress(data.completion);

                if (data.completion == 100) {
                    // Empties the progress bar
                    self.progress(0);
                }
            } else {
                self.progress(undefined);
            }
            self.filepos(data.filepos);
            self.printTime(data.printTime);
            self.printTimeLeft(data.printTimeLeft);
            self.printTimeLeftOrigin(data.printTimeLeftOrigin);
        };

        self._processZData = function(data) {
            self.currentHeight(data);
        };

        self._processBusyFiles = function(data) {
            var busyFiles = [];
            _.each(data, function(entry) {
                if (entry.hasOwnProperty("name") && entry.hasOwnProperty("origin")) {
                    busyFiles.push(entry.origin + ":" + entry.name);
                }
            });
            self.busyFiles(busyFiles);
        };

        self.print = function() {
            if (self.isPaused()) {
                showConfirmationDialog({
                    message: gettext("This will restart the print job from the beginning."),
                    onproceed: function() {
                        OctoPrint.job.restart();
                    }
                });
            } else {
                OctoPrint.job.start();
            }

            // Forces the insufficient filament message to hide
            if (self.insufficientFilament() && self.ignoredInsufficientFilament() == false) {
                self.ignoredInsufficientFilament(true);
            }
        };

        self.shutdown = function() {
            $('#job_shutdown').prop('disabled', true);

            self._jobCommand("shutdown", function () {
                $('#shutdown_confirmation').removeClass('hidden');
                $('#shutdown_panel').addClass('hidden');
            });
        };

        self.pause = function(action) {
            action = action || "toggle";
            self._jobCommand("pause", {"action": action});

            self._restoreShutdown();
        };

        self.onlyPause = function() {
            OctoPrint.job.pause();
        };

        self.onlyResume = function() {
            OctoPrint.job.resume();
        };

        self.pause = function(action) {
            OctoPrint.job.togglePause();

            self._restoreShutdown();
        };

        self._restoreShutdown = function() {
            $('#job_shutdown').prop('disabled', false);
            $('#shutdown_confirmation').addClass('hidden');
            $('#shutdown_panel').removeClass('hidden');
        };

        self.cancel = function() {
            $('#job_cancel').prop('disabled', true);
            $('#job_pause').prop('disabled', true);

            self._restoreShutdown();
            self.insufficientFilament(false);
            self.ignoredInsufficientFilament(false);

            showConfirmationDialog({
                message: gettext("This will cancel your print."),
                onproceed: function() {
                    OctoPrint.job.cancel({
                        done: function () {
                            $('#job_cancel').prop('disabled', false);
                            $('#job_pause').prop('disabled', false);

                            // Hides the status panel
                            if ($("#state").hasClass('in')) {
                                $("#state").collapse("hide");
                            }
                        }
                    });
                }
            });
        };

        self._jobCommand = function(command, payload, callback) {
            if (arguments.length == 1) {
                payload = {};
                callback = undefined;
            } else if (arguments.length == 2 && typeof payload === "function") {
                callback = payload;
                payload = {};
            }

            var data = _.extend(payload, {});
            data.command = command;

            $.ajax({
                url: API_BASEURL + "job",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function(response) {
                    if (callback != undefined) {
                        callback();
                    }
                }
            });
        };

        /**
         * Returns true if a the Cancel button should be enabled
         *
         * @returns {boolean}
         */
        self.isCancelEnabled = function() {
            if (!self.loginState.isUser()) {
                return false;
            }

            if (self.filename() == undefined) {
                return false;
            }

            if (!self.isOperational()) {
                return false;
            }

            return true;
        };

        /**
         * This function shows the maintenance panel and
         * automatically displays the change filament dialog
         */
        self.showMaintenanceFilamentChange = function() {
            $('#navbar_show_maintenance').click();
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        PrinterStateViewModel,
        ["loginStateViewModel", "printerProfilesViewModel"],
        ["#state_wrapper", "#drop_overlay"]
    ]);
});
