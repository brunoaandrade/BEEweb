$(function() {
    function SlicingViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.printerProfiles = parameters[1];

        self.target = undefined;
        self.file = undefined;
        self.data = undefined;

        self.defaultSlicer = undefined;
        self.defaultProfile = undefined;

        self.gcodeFilename = ko.observable();

        self.title = ko.observable();
        self.slicer = ko.observable();
        self.slicers = ko.observableArray();
        self.profile = ko.observable();
        self.profiles = ko.observableArray();
        self.printerProfile = ko.observable();

        self.colors = ko.observableArray();
        self.selColor = ko.observable();
        self.selDensity = ko.observable(5);
        self.selResolution = ko.observable("med");

        self.configured_slicers = ko.pureComputed(function() {
            return _.filter(self.slicers(), function(slicer) {
                return slicer.configured;
            });
        });

        self.afterSlicingOptions = [
            {"value": "none", "text": gettext("Do nothing")},
            {"value": "select", "text": gettext("Select for printing")},
            {"value": "print", "text": gettext("Start printing")}
        ];
        self.afterSlicing = ko.observable("none");

        self.show = function(target, file, force) {
            if (!self.enableSlicingDialog() && !force) {
                return;
            }

            self.requestData();
            self.target = target;
            self.file = file;
            self.title(_.sprintf(gettext("Slicing %(filename)s"), {filename: self.file}));
            self.gcodeFilename(self.file.substr(0, self.file.lastIndexOf(".")));
            self.printerProfile(self.printerProfiles.currentProfile());
            self.afterSlicing("select");
            $("#slicing_configuration_dialog").modal("show");
        };

        self.slicer.subscribe(function(newValue) {
            self.profilesForSlicer(newValue);
        });

        self.enableSlicingDialog = ko.pureComputed(function() {
            return self.configured_slicers().length > 0;
        });

        self.enableSliceButton = ko.pureComputed(function() {
            return self.gcodeFilename() != undefined
                && self.gcodeFilename().trim() != ""
                && self.slicer() != undefined;
                //&& self.profile() != undefined;
        });

        self.requestData = function(callback) {
            $.ajax({
                url: API_BASEURL + "slicing",
                type: "GET",
                dataType: "json",
                success: function(data) {
                    self.fromResponse(data);
                    if (callback !== undefined) {
                        callback();
                    }
                }
            });
        };

        self.fromResponse = function(data) {
            self.data = data;

            var selectedSlicer = undefined;
            self.slicers.removeAll();
            _.each(_.values(data), function(slicer) {
                var name = slicer.displayName;
                if (name == undefined) {
                    name = slicer.key;
                }

                if (slicer.default && slicer.configured) {
                    selectedSlicer = slicer.key;
                }

                self.slicers.push({
                    key: slicer.key,
                    name: name,
                    configured: slicer.configured
                });
            });

            if (selectedSlicer != undefined) {
                self.slicer(selectedSlicer);
            }

            self.defaultSlicer = selectedSlicer;
        };

        self.profilesForSlicer = function(key) {
            if (key == undefined) {
                key = self.slicer();
            }
            if (key == undefined || !self.data.hasOwnProperty(key)) {
                return;
            }
            var slicer = self.data[key];

            var selectedProfile = undefined;
            self.profiles.removeAll();
            self.colors.removeAll();

            _.each(_.values(slicer.profiles), function(profile) {
                var name = profile.displayName;
                if (name == undefined) {
                    name = profile.key;
                }

                if (profile.default) {
                    selectedProfile = profile.key;
                }

                self.profiles.push({
                    key: profile.key,
                    name: name
                })

                // Parses the list and filters for BVC colors
                // Assumes the '_' nomenclature separation for the profile names

                var profile_parts = name.split('_');
                if (profile_parts[0] != null) {
                    var color = profile_parts[0];
                    if (!_.findWhere(self.colors(), color)) {
                        self.colors.push(color);
                    }
                }

                // Selects the first color from the list by default
                if (self.colors().length > 0) {
                    self.selColor(self.colors()[0]);
                }
            });

            if (selectedProfile != undefined) {
                self.profile(selectedProfile);
            }

            self.defaultProfile = selectedProfile;
        };

        self.prepareAndSlice = function() {
            // Checks if the slicing was called on a workbench scene and finally saves it
            if (self.file.indexOf('bee_') != -1 ) {
                var saveCall = BEEwb.main.saveScene(self.file);

                // waits for the save operation
                saveCall.done( function () {

                    self.slice();
                });

            } else {
                self.slice();
            }

        };

        self.slice = function() {

            // Selects the slicing profile based on the color and resolution
            if (self.selColor() != null && self.selResolution() != null) {
                _.each(self.profiles(), function(profile) {
                    // checks if the profile contains the selected color
                    if (_.contains(profile.name, self.selColor())) {
                        if (self.selResolution() == 'med'
                            && (_.contains(profile.name, 'MED') || _.contains(profile.name, 'MEDIUM'))) {
                                self.profile(profile.key);
                        }

                        if (self.selResolution() == 'low' && _.contains(profile.name, 'LOW')) {
                            self.profile(profile.key);
                        }

                        if (self.selResolution() == 'high' && _.contains(profile.name, 'HIGH')) {
                            self.profile(profile.key);
                        }

                        if (self.selResolution() == 'high_plus' && _.contains(profile.name, 'HIGHPLUS')) {
                            self.profile(profile.key);
                        }
                    }
                });
            }

            var gcodeFilename = self._sanitize(self.gcodeFilename());
            if (!_.endsWith(gcodeFilename.toLowerCase(), ".gco")
                && !_.endsWith(gcodeFilename.toLowerCase(), ".gcode")
                && !_.endsWith(gcodeFilename.toLowerCase(), ".g")) {
                gcodeFilename = gcodeFilename + ".gco";
            }

            var data = {
                command: "slice",
                slicer: self.slicer(),
                profile: self.profile(),
                printerProfile: self.printerProfile(),
                gcode: gcodeFilename
            };

            if (self.afterSlicing() == "print") {
                data["print"] = true;
            } else if (self.afterSlicing() == "select") {
                data["select"] = true;
            }

            $.ajax({
                url: API_BASEURL + "files/" + self.target + "/" + self.file,
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function ( response ) {
                    // Shows the status panel
                    if (data["select"] || data["print"])
                        $("#state").collapse("show");
                },
                error: function ( response ) {
                    html = _.sprintf(gettext("Could not slice the selected file. Please make sure your printer is connected."));
                    new PNotify({title: gettext("Slicing failed"), text: html, type: "error", hide: false});
                }
            });

            $("#slicing_configuration_dialog").modal("hide");

            self.gcodeFilename(undefined);
            self.slicer(self.defaultSlicer);
            self.profile(self.defaultProfile);
        };

        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        self.onStartup = function() {
            self.requestData();
        };

        self.onEventSettingsUpdated = function(payload) {
            self.requestData();
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        SlicingViewModel,
        ["loginStateViewModel", "printerProfilesViewModel"],
        "#slicing_configuration_dialog"
    ]);
});
