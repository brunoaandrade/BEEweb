$(function() {
    function AppearanceViewModel(parameters) {
        var self = this;

        self.name = parameters[0].appearance_name;
        self.color = parameters[0].appearance_color;
        self.colorTransparent = parameters[0].appearance_colorTransparent;
        self.printerProfiles = parameters[1];

        self.brand = ko.pureComputed(function() {
            var brandText = gettext("BEEsoft");
            if (self.name())
                brandText = brandText + self.name();

            return brandText;
        });

        self.printerName = ko.computed(function() {
            var printer = ""
            var profileName = self.printerProfiles.currentProfileData().name();

            printer = "@ " + profileName;

            return printer;
        });

        self.title = ko.pureComputed(function() {
            if (self.name())
                return "[" + gettext("BEEsoft") + "]" + self.name();
            else
                return gettext("BEEsoft");
        });
    }

    OCTOPRINT_VIEWMODELS.push([
        AppearanceViewModel,
        ["settingsViewModel", "printerProfilesViewModel"],
        "head"
    ]);
});
