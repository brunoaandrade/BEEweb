$(function () {
	function WorkbenchViewModel(parameters) {
		var self = this;

		self.files = parameters[0].listHelper;
		self.loginState = parameters[1];
		self.connection = parameters[2];

		self.FileList = ko.observableArray();

		self.models = document.getElementById('workbench_file_list');

		self.loadModel = function () {
			var hash = self.models[self.models.selectedIndex].value;
			if (hash != "") {
				var model = self.findModel(hash);
				self.viewer.replaceSceneFromUrl(model.refs.download);
				self.viewer.setRenderMode(self.modes[self.modes.selectedIndex].value);
				self.viewer.update();
			}
		};

		// find model by hash
		self.findModel = function(hash) {
			var model = self.files.getItem(function(item){return item.hash == hash});
			return model;
		}

		// This will get called before the workbenchViewModel gets bound to the DOM, but after its depedencies have
		// already been initialized. It is especially guaranteed that this method gets called _after_ the settings
		// have been retrieved from the OctoPrint backend and thus the SettingsViewModel been properly populated.
		self.onBeforeBinding = function () {
			self.FileList(_.filter(self.files.allItems, self.files.supportedFilters["model"]));
		};

		//resize canvas after Workbench tab is made active.
		self.onAfterTabChange = function (current, previous) {
			if (current == "#workbench") {
				self.updateFileList();
			}
		};

		//append file list with newly updated stl file.
		self.onEventUpload = function (file) {
			if (file.file.substr(file.file.length - 3).toLowerCase() == "stl") {
				self.FileList.push({
					name : file.file
				});

				loadModel(file.file);
			}
		};

		self.updateFileList = function () {
			self.FileList(_.filter(self.files.allItems, self.files.supportedFilters["model"]));
		};

	}

	// This is how our plugin registers itself with the application, by adding some configuration information to
	// the global variable ADDITIONAL_VIEWMODELS
	ADDITIONAL_VIEWMODELS.push([
			// This is the constructor to call for instantiating the plugin
			WorkbenchViewModel,

			// This is a list of dependencies to inject into the plugin, the order which you request here is the order
			// in which the dependencies will be injected into your view model upon instantiation via the parameters
			// argument
			["gcodeFilesViewModel", "loginStateViewModel", "connectionViewModel"],

			// Finally, this is the list of all elements we want this view model to be bound to.
			[("#workbench", "#workbench-controls-container")]
		]);
});
