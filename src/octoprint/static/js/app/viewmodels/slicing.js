$(function() {
    function SlicingViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.printerProfiles = parameters[1];
        self.printerState = parameters[2];

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
        self.selResolution = ko.observable("Medium");
        self.raft = ko.observable(false);
        self.support = ko.observable(false);
        self.nozzleTypes = ko.observableArray();
        self.selNozzle = ko.observable();

        self.sliceButtonControl = true;

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

            self.requestData(self._nozzleFilamentUpdate);
            self.target = target;
            self.file = file;
            self.title(_.sprintf(gettext("Slicing %(filename)s"), {filename: self.file}));
            self.gcodeFilename(self.file.substr(0, self.file.lastIndexOf(".")));
            self.printerProfile(self.printerProfiles.currentProfile());
            self.afterSlicing("print");
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
                && self.slicer() != undefined
                && self.sliceButtonControl == true
                && (self.printerState.isOperational() ||
                    self.afterSlicing() == "none" && self.printerState.isErrorOrClosed() == true);
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

        self._nozzleFilamentUpdate = function() {
            $.ajax({
                url: API_BASEURL + "maintenance/get_nozzles_and_filament",
                type: "GET",
                dataType: "json",
                success: function(data) {
                    self.nozzleTypes.removeAll();
                    var nozzleList = data.nozzleList;

                    for (var key in nozzleList) {
                        self.nozzleTypes.push(nozzleList[key].value);
                    }

                    self.selNozzle(data.nozzle);

                    if (data.filament != null) {
                        self.colors().forEach(function(elem) {

                            if (elem == data.filament) {
                                self.selColor(elem);
                            }
                        });
                    } else {
                        // Selects the first color from the list by default
                        if (self.colors().length > 0) {
                            self.selColor(self.colors()[0]);
                        }
                    }
                }
            });
        };

        self.forPrint = function() {
            if (self.afterSlicing() != "none")
                return true;

            return false;
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
                    var color = profile_parts[0].trim();
                    if (!_.findWhere(self.colors(), color)) {
                        self.colors.push(color);
                    }
                }
            });

            if (selectedProfile != undefined) {
                self.profile(selectedProfile);
            }

            self.defaultProfile = selectedProfile;
        };

        self.prepareAndSlice = function() {
            self.sliceButtonControl = false; // Disables the slice button to avoid multiple clicks

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
                var nozzleSizeNorm = self.selNozzle() * 1000;
                var nozzleSizeStr = 'NZ' + nozzleSizeNorm;

                _.each(self.profiles(), function(profile) {
                    // checks if the profile contains the selected color and nozzle size
                    if (_.contains(profile.name, self.selColor())) {

                        if (_.contains(profile.name, self.selResolution())) {

                            if (_.contains(profile.name, nozzleSizeStr)) {
                                self.profile(profile.key);
                            }
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

            // Density support
            data['profile.fill_density'] = self.selDensity();

            // BVC Raft Support
            if (self.raft() == true) {
                data['profile.platform_adhesion'] = 'raft';
                data['profile.raft_airgap'] = 0.220;
                data['profile.raft_line_spacing'] = 3.0;
                data['profile.raft_base_linewidth'] = 1.000;
                data['profile.raft_surface_layers'] = 2;

                data['profile.raft_interface_linewidth'] = 0.4;
                data['profile.raft_interface_thickness'] = 0.270;

                data['profile.raft_margin'] = 5.000;
                data['profile.raft_base_thickness'] = 0.300;

                data['profile.bottom_layer_speed'] = 20; // used also for raftSurfaceSpeed
                data['profile.raft_fan_speed'] = 0; //?? 100 in profile
                //data['profile.raft_surface_thickness'] = 270; // used also for raftSurfaceSpeed
            } else {
                data['profile.platform_adhesion'] = 'none';
                data['profile.raft_base_thickness'] = 0;
                data['profile.raft_interface_thickness'] = 0.;
            }

            // BVC Support
            if (self.support() == true) {
                data['profile.support'] = 'everywhere';
                data['profile.support_angle'] = 60;
                data['profile.support_xy_distance'] = 0.7;
                data['profile.support_z_distance'] = 0.15;
                data['profile.support_type'] = 'lines';
                data['profile.support_dual_extrusion'] = 'both';
                data['profile.support_fill_rate'] = 15; // ?? supportLineDistance
            } else {
                data['profile.support_angle'] = -1;
                data['profile.support'] = 'none';
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

                    self.sliceButtonControl = true;
                },
                error: function ( response ) {
                    html = _.sprintf(gettext("Could not slice the selected file. Please make sure your printer is connected."));
                    new PNotify({title: gettext("Slicing failed"), text: html, type: "error", hide: false});

                    self.sliceButtonControl = true;
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
        ["loginStateViewModel", "printerProfilesViewModel", "printerStateViewModel"],
        "#slicing_configuration_dialog"
    ]);
});
