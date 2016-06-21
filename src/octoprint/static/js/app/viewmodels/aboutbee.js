$(function() {
    function AboutBeeViewModel(parameters) {
        var self = this;
        self.aboutDialog = $('#aboutbee_dialog');
        self.currentFirmware = ko.observable('Undefined');

        self.show = function() {

            // show settings, ensure centered position
            self.aboutDialog.modal({
                minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 500, 250); }
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });

            $.ajax({
                url: "bee/api/firmware/current/version",
                type: "GET",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                success: function(data) {
                    self.currentFirmware(data.version);
                }
            });

            return false;
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        AboutBeeViewModel,
        [],
        ["#navbar_help","#aboutbee_body"]
    ]);
});
