// global namespace
var BEEwb = BEEwb || {};

BEEwb.transformOps = {
    selectedMode: 'translate',
    initialSize: null
}

BEEwb.transformOps.resetObjectData = function() {
    this.initialSize = null;
}

/**
 * Moves the selected model to the input text boxes axis values
 *
 */
BEEwb.transformOps.move = function() {

    if (BEEwb.main.selectedObject !== null) {
        var x = $('#x-axis').val();
        var y = $('#y-axis').val();
        var z = $('#z-axis').val();
        BEEwb.main.selectedObject.position.set( x, y, z );
    }
}

/**
 * Scales the selected model to the input text boxes axis values
 *
 */
BEEwb.transformOps.scale = function() {

    if (BEEwb.main.selectedObject !== null) {
        var x = $('#scalex-axis').val();
        var y = $('#scaley-axis').val();
        var z = $('#scalez-axis').val();

        this.scaleBySize(x, y ,z);
    }
}

/**
 * Centers the selected model on the platform
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

        BEEwb.main.selectedObject.scale.set(scale, scale ,scale);
    }
}

/**
 * Centers the selected model on the platform
 *
 */
BEEwb.transformOps.centerModel = function() {

    if (BEEwb.main.selectedObject !== null) {
        BEEwb.main.selectedObject.position.set( 0, 0, 0 );
    }
}

/**
 * Resets the transformations of the selected object
 *
 */
BEEwb.transformOps.resetSelectedModel = function() {

    if (BEEwb.main.selectedObject !== null) {
        BEEwb.main.selectedObject.position.set( 0, 0, 0 );
		BEEwb.main.selectedObject.rotation.set( 0, 0, 0 );
		BEEwb.main.selectedObject.scale.set( 1, 1, 1 );

        // Updates the size/scale/rotation input boxes
        this.updatePositionInputs();

        this.updateScaleSizeInputs();
    }
}

/**
 * Removes a model from the scene
 *
 */
BEEwb.transformOps.removeModel = function(modelObj) {

    if (null !== modelObj) {
        BEEwb.main.scene.remove(modelObj);
        BEEwb.main.objects.remove(modelObj);
        BEEwb.main.scene.remove(BEEwb.main.transformControls);
    }
}

/**
 * Removes the selected model from the scene
 *
 */
BEEwb.transformOps.removeSelected = function() {

    if (BEEwb.main.selectedObject != null) {
        this.removeModel(BEEwb.main.selectedObject);

        BEEwb.main.selectedObject = null;
        $('.model-selection').prop('disabled', true);
    }
}


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
    }
}

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

        this.updateScaleSizeInputs();
    }
}

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
    }
}

/**
 * Updates the selected object position input boxes
 *
 */
BEEwb.transformOps.updatePositionInputs = function() {

    if (BEEwb.main.selectedObject != null) {
        $('#x-axis').val(BEEwb.main.selectedObject.position.x.toFixed(1));
        $('#y-axis').val(BEEwb.main.selectedObject.position.y.toFixed(1));
        $('#z-axis').val(BEEwb.main.selectedObject.position.z.toFixed(1));
    }
}

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
    }
}

/**
 * Scales the selected object converting size passed in the parameters to the appropriate scale
 *
 */
BEEwb.transformOps.scaleBySize = function(x, y, z) {

    if (BEEwb.main.selectedObject != null) {
        var xScale = x / this.initialSize['x'];
        var yScale = y / this.initialSize['y'];
        var zScale = z / this.initialSize['z'];

        BEEwb.main.selectedObject.scale.set( xScale, yScale, zScale );
    }
}

/**
 * Sets the initial size for the transform operations
 *
 */
BEEwb.transformOps.setInitialSize = function() {

    if (BEEwb.main.selectedObject != null) {
        this.initialSize = BEEwb.helpers.objectSize(BEEwb.main.selectedObject.geometry);
    }
}
