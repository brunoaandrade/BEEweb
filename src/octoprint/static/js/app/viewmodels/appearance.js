$(function() {
    function AppearanceViewModel(parameters) {
        var self = this;

        self.name = parameters[0].appearance_name;
        self.color = parameters[0].appearance_color;
        self.colorTransparent = parameters[0].appearance_colorTransparent;
        self.printerProfiles = parameters[1];

        self.brand = ko.computed(function() {
            var brandText = gettext("BEE.web")
            if (self.name())
                brandText = brandText + ":" + self.name();

            return brandText;
        });

        self.printerName = ko.computed(function() {
            var printer = ""
            var profileName = self.printerProfiles.currentProfileData().name();
            if (self.printerProfiles.currentProfile() != '_default')
                printer = "@ " + profileName;

            return printer;
        });

        self.title = ko.computed(function() {
            if (self.name())
                return "[" + gettext("BEE.web") + "]:" + self.name();
            else
                return gettext("BEE.web");
        });
    }

    OCTOPRINT_VIEWMODELS.push([
        AppearanceViewModel,
        ["settingsViewModel", "printerProfilesViewModel"],
        "head"
    ]);
});
