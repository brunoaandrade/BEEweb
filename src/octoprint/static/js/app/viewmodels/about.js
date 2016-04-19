$(function() {
    function AboutViewModel(parameters) {
        var self = this;
        self.aboutDialog = $('#about_dialog');

        self.show = function() {

            // show settings, ensure centered position
            self.aboutDialog.modal({
                minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 500, 250); }
            }).css({
                width: '30%',
                'margin-left': function() { return -($(this).width() /2); }
            });

            return false;
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        AboutViewModel,
        [],
        "#navbar_help", "#about_dialog"
    ]);
});
