// global namespace
var BEEwb = BEEwb || {};

BEEwb.events = {}

/**
 * OnWindowResize event function
 */
BEEwb.events.onWindowResize = function() {
    BEEwb.main.camera.aspect = BEEwb.main.container.clientWidth / BEEwb.main.container.clientHeight;
    BEEwb.main.camera.updateProjectionMatrix();

    BEEwb.main.renderer.setSize( window.innerWidth, window.innerHeight / 1.5 );

    BEEwb.main.render();
}

/**
 * OnMouseDown event function
 */
BEEwb.events.onMouseDown = function( e ) {

    // Records the first click position
    BEEwb.main.mouseVector.x = 2 * ( (e.clientX - BEEwb.main.containerWidthOffset) /
        BEEwb.main.renderer.domElement.clientWidth) - 1;

    BEEwb.main.mouseVector.y = 1 - 2 * ( (e.clientY - BEEwb.main.containerHeightOffset) /
        BEEwb.main.renderer.domElement.clientHeight );

    BEEwb.main.mouseVector.z = 0.5;
}

/**
 * OnMouseUp event function
 */
BEEwb.events.onMouseUp = function( e ) {

    var prevMouseVector = BEEwb.main.mouseVector.clone();

    BEEwb.main.mouseVector.x = 2 * ( (e.clientX - BEEwb.main.containerWidthOffset) /
        BEEwb.main.renderer.domElement.clientWidth) - 1;

    BEEwb.main.mouseVector.y = 1 - 2 * ( (e.clientY - BEEwb.main.containerHeightOffset) /
        BEEwb.main.renderer.domElement.clientHeight );

    BEEwb.main.mouseVector.z = 0.5;

    BEEwb.main.raycaster.setFromCamera( BEEwb.main.mouseVector, BEEwb.main.camera );

    var intersects = BEEwb.main.raycaster.intersectObjects( BEEwb.main.objects.children );

    // Selects the first found intersection
    if (intersects.length > 0) {

        var intersection = intersects[ 0 ];
        var model = intersection.object;

        if (BEEwb.main.selectedObject !== model)
            BEEwb.main.selectModel(model);

    } else if (prevMouseVector.x == BEEwb.main.mouseVector.x
        && prevMouseVector.y == BEEwb.main.mouseVector.y
        && prevMouseVector.z == BEEwb.main.mouseVector.z) { // It means the scene wasn't dragged and so we should remove all selections

        BEEwb.main.removeAllSelections();
    }

    // Updates the size/scale/rotation input boxes
    if (BEEwb.transformOps.selectedMode == 'translate') {
        BEEwb.transformOps.updatePositionInputs();
    }

    if (BEEwb.transformOps.selectedMode == 'scale') {
        BEEwb.transformOps.updateScaleSizeInputs();
    }

     if (BEEwb.transformOps.selectedMode == 'rotate') {
         BEEwb.transformOps.updateRotationInputs();
     }
}
