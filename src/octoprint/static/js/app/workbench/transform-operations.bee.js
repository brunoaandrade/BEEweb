// global namespace
var BEEwb = BEEwb || {};

BEEwb.transformOps = {
    selectedMode: 'translate',
    initialSize: null,
    previousSize: null,
    previousSizePercentage: null
};

BEEwb.transformOps.resetObjectData = function() {
    this.initialSize = null;
    this.previousSize = null;
    this.previousSizePercentage = null;
};

/**
 * Moves the selected model to the input text boxes axis values
 *
 */
BEEwb.transformOps.move = function() {

    if (BEEwb.main.selectedObject !== null) {
        var x = parseFloat($('#x-axis').val().replace(",", "."));
        var y = parseFloat($('#y-axis').val().replace(",", "."));
        var z = parseFloat($('#z-axis').val().replace(",", "."));
        BEEwb.main.selectedObject.position.set( x, y, z );
        BEEwb.main.transformControls.update();

        // Checks if the selected object is out of bounds
        BEEwb.main.isSelectedObjectOutOfBounds();
    }
};

/**
 * Change metric values for scale
 *
 */
BEEwb.transformOps.toggleScaleType = function() {

    if ($('#scaleby-size').is(':checked')) {
        this.updateScaleSizeInputs();
    } else {
        this.updateScaleSizeInputsByPercentage();
    }
};

/**
 * Scales the selected model to the input text boxes axis values
 *
 */
BEEwb.transformOps.scale = function() {

    if (BEEwb.main.selectedObject !== null) {
        var x = parseFloat($('#scalex-axis').val().replace(",", "."));
        var y = parseFloat($('#scaley-axis').val().replace(",", "."));
        var z = parseFloat($('#scalez-axis').val().replace(",", "."));

        if ($('#scaleby-per').is(':checked')) {
            this.scaleByPercentage(x, y, z);

            this.updateScaleSizeInputsByPercentage();
        } else {
            this.scaleBySize(x ,y ,z);

            this.updateScaleSizeInputs();
        }

        BEEwb.main.transformControls.update();

        // Checks if the selected object is out of bounds
        BEEwb.main.isSelectedObjectOutOfBounds();
    }
};

/**
 * Rotates the selected model to the input text boxes axis values
 *
 */
BEEwb.transformOps.rotate = function() {

    if (BEEwb.main.selectedObject !== null) {
        var x = parseFloat($('#rotx-axis').val().replace(",", "."));
        var y = parseFloat($('#roty-axis').val().replace(",", "."));
        var z = parseFloat($('#rotz-axis').val().replace(",", "."));

        this._rotateByDegrees(x, y ,z);
        BEEwb.main.transformControls.update();

        // Checks if the selected object is out of bounds
        BEEwb.main.isSelectedObjectOutOfBounds();
    }
};

/**
 * Rotates the selected model 90 degrees to the left (counter clockwise)
 * in the selected axis in the radio input control
 *
 */
BEEwb.transformOps.rotateCCW = function() {

    if (BEEwb.main.selectedObject !== null) {
        this._rotateStep(-90);

        this.updateRotationInputs();
    }
};

/**
 * Rotates the selected model 90 degrees to the right (clockwise)
 * in the selected axis in the radio input control
 *
 */
BEEwb.transformOps.rotateCW = function() {

    if (BEEwb.main.selectedObject !== null) {
        this._rotateStep(90);

        this.updateRotationInputs();
    }
};

/**
 * Rotates the selected model 'n' degrees
 * in the selected axis in the radio input control
 *
 */
BEEwb.transformOps._rotateStep = function( degrees ) {

    var radStep = BEEwb.helpers.convertToRadians(degrees);
    var selAxis = $('input[name=rot-axis-sel]:checked').val();

    if (selAxis == 'x')
        BEEwb.main.selectedObject.rotation.set(
            BEEwb.main.selectedObject.rotation.x + radStep,
            BEEwb.main.selectedObject.rotation.y,
            BEEwb.main.selectedObject.rotation.z
        );
    else if (selAxis == 'y')
        BEEwb.main.selectedObject.rotation.set(
            BEEwb.main.selectedObject.rotation.x,
            BEEwb.main.selectedObject.rotation.y + radStep,
            BEEwb.main.selectedObject.rotation.z
        );
    else if (selAxis == 'z')
        BEEwb.main.selectedObject.rotation.set(
            BEEwb.main.selectedObject.rotation.x,
            BEEwb.main.selectedObject.rotation.y,
            BEEwb.main.selectedObject.rotation.z - radStep
        );
};

/**
 * Scales the selected model on the platform the the maximum possible size
 *
 */
BEEwb.transformOps.scaleToMax = function() {

    if (BEEwb.main.selectedObject !== null) {
        BEEwb.main.selectedObject.position.set( 0, 0, 0 );

        var hLimit = BEEwb.main.bedHeight;// z
        var wLimit = BEEwb.main.bedWidth; // x
        var dLimit = BEEwb.main.bedDepth; // y

        var xScale = wLimit / this.initialSize['x'];
        var yScale = dLimit / this.initialSize['y'];
        var zScale = hLimit / this.initialSize['z'];

        var scale = Math.min(xScale, Math.min (yScale, zScale));
        // Small adjustment to avoid false positive out of bounds message due to precision errors
        scale -= 0.01;

        BEEwb.main.selectedObject.scale.set(scale, scale ,scale);
        BEEwb.main.transformControls.update();

        if ($('#scaleby-per').is(':checked')) {
            BEEwb.transformOps.updateScaleSizeInputsByPercentage();
        } else {
            BEEwb.transformOps.updateScaleSizeInputs();
        }
    }
};

/**
 * Centers the selected model on the platform
 *
 */
BEEwb.transformOps.centerModel = function() {

    if (BEEwb.main.selectedObject !== null) {
        BEEwb.main.selectedObject.position.setX( 0 );
        BEEwb.main.selectedObject.position.setY( 0 );
        this.placeOnBed();
    }
};


/**
 * Places the selected model on top of the platform
 *
 */
BEEwb.transformOps.placeOnBed = function() {

    if (BEEwb.main.selectedObject !== null) {

        // Computes the box after any transformations
        var bbox = new THREE.Box3().setFromObject( BEEwb.main.selectedObject );

        if (bbox.min.z != 0) {

            var zShift = BEEwb.main.selectedObject.position.z - bbox.min.z;

            BEEwb.main.selectedObject.position.setZ( zShift );
        }

        // Recomputes the bounding box to check for rounding errors
        bbox = new THREE.Box3().setFromObject( BEEwb.main.selectedObject );
        if (bbox.min.z < 0) {
            zShift += (-bbox.min.z + 0.0001); // Increment the shift by a small amount in case of the model being below the platform
            BEEwb.main.selectedObject.position.setZ( zShift );
        }

        BEEwb.main.transformControls.update();
        this.updatePositionInputs();
    }
};

/**
 * Resets the transformations of the selected object
 *
 */
BEEwb.transformOps.resetSelectedModel = function() {

    if (BEEwb.main.selectedObject !== null) {
        BEEwb.main.selectedObject.position.set( 0, 0, 0 );
		BEEwb.main.selectedObject.rotation.set( 0, 0, 0 );
		BEEwb.main.selectedObject.scale.set( 1, 1, 1 );

        BEEwb.main.transformControls.update();

        // Updates the size/scale/rotation input boxes
        this.updatePositionInputs();

        if ($('#scaleby-per').is(':checked')) {
            BEEwb.transformOps.updateScaleSizeInputsByPercentage();
        } else {
            BEEwb.transformOps.updateScaleSizeInputs();
        }

        this.updateRotationInputs();
    }
};

/**
 * Removes a model from the scene
 *
 */
BEEwb.transformOps.removeModel = function(modelObj) {

    if (null !== modelObj) {
        BEEwb.main.scene.remove(modelObj);
        BEEwb.main.objects.remove(modelObj);
        BEEwb.main.scene.remove(BEEwb.main.transformControls);

        BEEwb.main.toggleObjectOutOfBounds(BEEwb.main.selectedObject, false);
    }
};

/**
 * Removes the selected model from the scene
 *
 */
BEEwb.transformOps.removeSelected = function() {

    if (BEEwb.main.selectedObject != null) {
        this.removeModel(BEEwb.main.selectedObject);

        BEEwb.main.selectedObject = null;
        $('.model-selection').prop('disabled', true);

        // Hides the side panel and removes selections
        BEEwb.main.removeAllSelections();
    }
};


/**
 * Activates the rotate mode for the selected object
 *
 */
BEEwb.transformOps.activateRotate = function() {

    if (BEEwb.main.transformControls != null && BEEwb.main.selectedObject != null) {

        this.selectedMode = 'rotate';
        BEEwb.main.transformControls.setMode("rotate");

        $('#btn-move').removeClass('btn-primary');
        $('#btn-scale').removeClass('btn-primary');
        $('#btn-rotate').removeClass('btn-default');
        $('#btn-rotate').addClass('btn-primary');

        $('#move-axis-form').slideUp();
        $('#scale-values-form').slideUp();
        $('#rotate-values-form').slideDown();
    }
};

/**
 * Activates the scale mode for the selected object
 *
 */
BEEwb.transformOps.activateScale = function() {

    if (BEEwb.main.transformControls != null && BEEwb.main.selectedObject != null) {

        this.selectedMode = 'scale';
        BEEwb.main.transformControls.setMode("scale");

        $('#btn-move').removeClass('btn-primary');
        $('#btn-rotate').removeClass('btn-primary');
        $('#btn-scale').removeClass('btn-default');
        $('#btn-scale').addClass('btn-primary');

        $('#move-axis-form').slideUp();
        $('#scale-values-form').slideDown();
        $('#rotate-values-form').slideUp();

        if ($('#scaleby-per').is(':checked')) {
            BEEwb.transformOps.updateScaleSizeInputsByPercentage();
        } else {
            BEEwb.transformOps.updateScaleSizeInputs();
        }
    }
};

/**
 * Activates the translate (move) mode for the selected object
 *
 */
BEEwb.transformOps.activateMove = function() {

    if (BEEwb.main.transformControls != null && BEEwb.main.selectedObject != null) {

        BEEwb.main.transformControls.setMode("translate");
        this.selectedMode = 'translate';

        $('#btn-scale').removeClass('btn-primary');
        $('#btn-rotate').removeClass('btn-primary');
        $('#btn-move').removeClass('btn-default');
        $('#btn-move').addClass('btn-primary');

        $('#move-axis-form').slideDown();
        $('#scale-values-form').slideUp();
        $('#rotate-values-form').slideUp();
    }
};

/**
 * Updates the selected object position input boxes
 *
 */
BEEwb.transformOps.updatePositionInputs = function() {

    if (BEEwb.main.selectedObject != null) {
        $('#x-axis').val(BEEwb.main.selectedObject.position.x.toFixed(1));
        $('#y-axis').val(BEEwb.main.selectedObject.position.y.toFixed(1));
        $('#z-axis').val(BEEwb.main.selectedObject.position.z.toFixed(1));

        // Checks if the selected object is out of bounds
        BEEwb.main.isSelectedObjectOutOfBounds();
    }
};

/**
 * Updates the selected object scale/size input boxes
 *
 */
BEEwb.transformOps.updateScaleSizeInputs = function() {

    if (BEEwb.main.selectedObject != null) {
        if (this.initialSize == null) {
            this.initialSize = BEEwb.helpers.objectSize(BEEwb.main.selectedObject.geometry);
        }

        var newX = this.initialSize['x'] * BEEwb.main.selectedObject.scale.x;
        var newY = this.initialSize['y'] * BEEwb.main.selectedObject.scale.y;
        var newZ = this.initialSize['z'] * BEEwb.main.selectedObject.scale.z;

        $('#scalex-axis').val(newX.toFixed(2));
        $('#scaley-axis').val(newY.toFixed(2));
        $('#scalez-axis').val(newZ.toFixed(2));

        $('#scalex-axis-label').text("X (mm)");
        $('#scaley-axis-label').text("Y (mm)");
        $('#scalez-axis-label').text("Z (mm)");

        // Checks if the selected object is out of bounds
        BEEwb.main.isSelectedObjectOutOfBounds();
    }
};

/**
 * Updates the selected object scale/size input boxes
 *
 */
BEEwb.transformOps.updateScaleSizeInputsByPercentage = function() {

    if (BEEwb.main.selectedObject != null) {

        var newX = Math.round(BEEwb.main.selectedObject.scale.x * 100);
        var newY = Math.round(BEEwb.main.selectedObject.scale.y * 100);
        var newZ = Math.round(BEEwb.main.selectedObject.scale.z * 100);

        $('#scalex-axis').val(newX.toFixed(0));
        $('#scaley-axis').val(newY.toFixed(0));
        $('#scalez-axis').val(newZ.toFixed(0));

        $('#scalex-axis-label').text("X (%)");
        $('#scaley-axis-label').text("Y (%)");
        $('#scalez-axis-label').text("Z (%)");

        // Checks if the selected object is out of bounds
        BEEwb.main.isSelectedObjectOutOfBounds();
    }
};

/**
 * Updates the selected object rotation angles input boxes
 *
 */
BEEwb.transformOps.updateRotationInputs = function() {

    if (BEEwb.main.selectedObject != null) {

        var newX = BEEwb.helpers.convertToDegrees(BEEwb.main.selectedObject.rotation.x);
        var newY = BEEwb.helpers.convertToDegrees(BEEwb.main.selectedObject.rotation.y);
        var newZ = BEEwb.helpers.convertToDegrees(BEEwb.main.selectedObject.rotation.z);

        $('#rotx-axis').val(newX.toFixed(2));
        $('#roty-axis').val(newY.toFixed(2));
        $('#rotz-axis').val(newZ.toFixed(2));

        // Checks if the selected object is out of bounds
        BEEwb.main.isSelectedObjectOutOfBounds();
    }
};

/**
 * Scales the selected object converting percentage size passed in the parameters to the appropriate scale
 *
 */
BEEwb.transformOps.scaleByPercentage = function(x, y, z) {

    if (x < 0 || y < 0 || z < 0)
        return null;

    if (BEEwb.main.selectedObject != null) {

        var xScale = x / 100;
        var yScale = y / 100;
        var zScale = z / 100;

        // Checks which axis was changed
        if (x != this.previousSizePercentage['x']) {

            if ($('#lock-y').is(':checked')) {
                yScale = xScale;
            }

            if ($('#lock-z').is(':checked')) {
                zScale = xScale;
            }
        }

        if (y != this.previousSizePercentage['y']) {

            if ($('#lock-x').is(':checked')) {
                xScale = yScale;
            }

            if ($('#lock-z').is(':checked')) {
                zScale = yScale;
            }
        }

        if (z != this.previousSizePercentage['z']) {

            if ($('#lock-y').is(':checked')) {
                yScale = zScale;
            }

            if ($('#lock-x').is(':checked')) {
                xScale = zScale;
            }
        }

        BEEwb.main.selectedObject.scale.set( xScale, yScale, zScale );

        this.previousSizePercentage = { 'x': xScale * 100, 'y': yScale * 100, 'z': zScale * 100};
    }
};


/**
 * Scales the selected object converting size passed in the parameters to the appropriate scale
 *
 */
BEEwb.transformOps.scaleBySize = function(x, y, z) {

    if (x < 0 || y < 0 || z < 0)
        return null;

    if (BEEwb.main.selectedObject != null) {

        var xScale = x / this.initialSize['x'];
        var yScale = y / this.initialSize['y'];
        var zScale = z / this.initialSize['z'];

        // Checks which axis was changed
        if (x != this.previousSize['x']) {

            if ($('#lock-y').is(':checked')) {
                yScale = xScale;
            }

            if ($('#lock-z').is(':checked')) {
                zScale = xScale;
            }
        }

        if (y != this.previousSize['y']) {

            if ($('#lock-x').is(':checked')) {
                xScale = yScale;
            }

            if ($('#lock-z').is(':checked')) {
                zScale = yScale;
            }
        }

        if (z != this.previousSize['z']) {

            if ($('#lock-y').is(':checked')) {
                yScale = zScale;
            }

            if ($('#lock-x').is(':checked')) {
                xScale = zScale;
            }
        }

        BEEwb.main.selectedObject.scale.set( xScale, yScale, zScale );

        this.previousSize = { 'x': x, 'y': y, 'z': z};
    }
};

/**
 * Rotates the selected object converting size passed in the parameters to the appropriate scale
 *
 */
BEEwb.transformOps._rotateByDegrees = function(x, y, z) {

    if (BEEwb.main.selectedObject != null) {
        var xRotation = BEEwb.helpers.convertToRadians(x);
        var yRotation = BEEwb.helpers.convertToRadians(y);
        var zRotation = BEEwb.helpers.convertToRadians(z);

        BEEwb.main.selectedObject.rotation.set( xRotation, yRotation, zRotation );
    }
};


/**
 * Sets the initial size for the transform operations
 *
 */
BEEwb.transformOps.setInitialSize = function() {

    if (BEEwb.main.selectedObject != null) {
        this.initialSize = BEEwb.helpers.objectSize(BEEwb.main.selectedObject.geometry);
        this.previousSize = {
            'x': this.initialSize['x'].toFixed(2),
            'y': this.initialSize['y'].toFixed(2),
            'z': this.initialSize['z'].toFixed(2)
        };
        this.previousSizePercentage = {
            'x': 100,
            'y': 100,
            'z': 100
        };
    }
};
