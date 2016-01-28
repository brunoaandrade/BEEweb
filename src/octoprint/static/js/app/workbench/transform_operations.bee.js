// global namespace
var BEEwb = BEEwb || {};

BEEwb.transform_ops = {
    selectedMode: 'translate'
}

/**
 * Moves the selected model to the input text boxes axis values
 *
 */
BEEwb.transform_ops.move = function() {

    if (BEEwb.main.selectedObject !== null) {
        var x = $('#x-axis').val();
        var y = $('#y-axis').val();
        var z = $('#z-axis').val();
        BEEwb.main.selectedObject.position.set( x, y, z );
    }
}

/**
 * Centers the selected model on the platform
 *
 */
BEEwb.transform_ops.centerModel = function() {

    if (BEEwb.main.selectedObject !== null) {
        BEEwb.main.selectedObject.position.set( 0, 0, 0 );
    }
}

/**
 * Resets the transformations of the selected object
 *
 */
BEEwb.transform_ops.resetSelectedModel = function() {

    if (BEEwb.main.selectedObject !== null) {
        BEEwb.main.selectedObject.position.set( 0, 0, 0 );
		BEEwb.main.selectedObject.rotation.set( 0, 0, 0 );
		BEEwb.main.selectedObject.scale.set( 1, 1, 1 );

        this.updatePositionInputs();
    }
}

/**
 * Removes a model from the scene
 *
 */
BEEwb.transform_ops.removeModel = function(modelObj) {

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
BEEwb.transform_ops.removeSelected = function() {

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
BEEwb.transform_ops.activateRotate = function() {

    if (BEEwb.main.transformControls != null && BEEwb.main.selectedObject != null) {

        BEEwb.transform_ops.selectedMode = 'rotate';
        BEEwb.main.transformControls.setMode("rotate");

        $('#btn-move').removeClass('btn-primary');
        $('#btn-scale').removeClass('btn-primary');
        $('#btn-rotate').removeClass('btn-default');
        $('#btn-rotate').addClass('btn-primary');

        $('#move-axis-form').hide();
    }
}

/**
 * Activates the scale mode for the selected object
 *
 */
BEEwb.transform_ops.activateScale = function() {

    if (BEEwb.main.transformControls != null && BEEwb.main.selectedObject != null) {

        BEEwb.transform_ops.selectedMode = 'scale';
        BEEwb.main.transformControls.setMode("scale");

        $('#btn-move').removeClass('btn-primary');
        $('#btn-rotate').removeClass('btn-primary');
        $('#btn-scale').removeClass('btn-default');
        $('#btn-scale').addClass('btn-primary');

        $('#move-axis-form').hide();
    }
}

/**
 * Activates the translate (move) mode for the selected object
 *
 */
BEEwb.transform_ops.activateMove = function() {

    if (BEEwb.main.transformControls != null && BEEwb.main.selectedObject != null) {

        BEEwb.main.transformControls.setMode("translate");
        BEEwb.transform_ops.selectedMode = 'translate';

        $('#btn-scale').removeClass('btn-primary');
        $('#btn-rotate').removeClass('btn-primary');
        $('#btn-move').removeClass('btn-default');
        $('#btn-move').addClass('btn-primary');

        $('#move-axis-form').show();
    }
}

/**
 * Updates the selected object position input boxes
 *
 */
BEEwb.transform_ops.updatePositionInputs = function() {

    if (BEEwb.main.selectedObject != null) {
        $('#x-axis').val(BEEwb.main.selectedObject.position.x.toFixed(1));
        $('#y-axis').val(BEEwb.main.selectedObject.position.y.toFixed(1));
        $('#z-axis').val(BEEwb.main.selectedObject.position.z.toFixed(1));
    }
}
