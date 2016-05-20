// global namespace
var BEEwb = BEEwb || {};

BEEwb.helpers = {};

/**
 * Auxiliar function to generate the STL file and Scene name from the current canvas scene.
 *
 * param objects: Array of objects from a Threejs scene
 *
 * Return dictionary with 'stl' -> File and 'sceneName' -> File name
 */
BEEwb.helpers.generateSTLFromScene = function( objects ) {

    var exporter = new THREE.STLBinaryExporter();

    var stlData = exporter.parse( objects );

    // plain text ascii
    //var blob = new Blob([stlData], {type: 'text/plain'});
    // binary
    return new Blob([stlData], {type: 'application/octet-binary'});
};

/**
 * Generates the workbench scene name based on current date/time
 *
 * Return string with the generated name
 */
BEEwb.helpers.generateSceneName = function( ) {
    var now = new Date();
    var prefix = 'bee_';
    if (BEEwb.main.lastLoadedModel != null) {
        prefix = BEEwb.main.lastLoadedModel + '_';
    }
    var sceneName = prefix + now.getDate() + '_' + (now.getMonth()+1) + '_' + now.getFullYear()
    + '-' + now.getHours() + '_' + now.getMinutes() + '_' + now.getSeconds() + '.stl';

    return sceneName;
};

/**
 * Calculates Geometry object size
 *
 * param geometry: THREEJS.Geometry object
 *
 * Returns dictionary with size { 'x': ..., 'y': ..., 'z': ...}
 */
BEEwb.helpers.objectSize = function( geometry ) {

    if ( geometry == null) {
        return { 'x': 0, 'y': 0, 'z': 0};
    }

    geometry.computeBoundingBox();
    var bbox = geometry.boundingBox;
    var xSize = 0;
    var ySize = 0;
    var zSize = 0;

    // X size
    if (bbox.max.x < 0) {
        xSize -= bbox.max.x;
    } else {
        xSize += bbox.max.x;
    }

    if (bbox.min.x < 0) {
        xSize -= bbox.min.x
    } else {
        xSize += bbox.min.x;
    }

    // Y size
    if (bbox.max.y < 0) {
        ySize -= bbox.max.y;
    } else {
        ySize += bbox.max.y;
    }

    if (bbox.min.y < 0) {
        ySize -= bbox.min.y
    } else {
        ySize += bbox.min.y;
    }

    // Z size
    if (bbox.max.z < 0) {
        zSize -= bbox.max.z;
    } else {
        zSize += bbox.max.z;
    }

    if (bbox.min.z < 0) {
        zSize -= bbox.min.z
    } else {
        zSize += bbox.min.z;
    }

    return { 'x': xSize, 'y': ySize, 'z': zSize};
};

/**
 * Checks if the object is out of bounds
 *
 * param obj: THREEJS.Object3D object
 * param bboxSize: array { x, y, z } with bounding box size
 *
 * Returns true if the object is out of bounds
 */
BEEwb.helpers.objectOutOfBounds = function( obj, bboxSize ) {
    if ( obj == null) {
        return false;
    }

    // Computes the box after any transformations
    var bbox = new THREE.Box3().setFromObject( obj );
    if ( bbox.max.x > (bboxSize[0] / 2) || bbox.max.y > (bboxSize[1] / 2) || bbox.max.z > bboxSize[2]) {
        return true;
    }

    if ( bbox.min.x < -(bboxSize[0] / 2) || bbox.min.y < -(bboxSize[1] / 2) || bbox.min.z < 0) {
        return true;
    }

    return false;
};

/**
 * Converts radians to degrees
 *
 * param radians: Angle in radians value
 *
 * Returns value in degrees
 */
BEEwb.helpers.convertToDegrees = function( radians ) {
    if (radians != null) {
        return radians * (180/3.1416);
    } else {
        return 0;
    }
};

/**
 * Converts degress to radians
 *
 * param degrees: Angle in degrees value
 *
 * Returns value in degrees
 */
BEEwb.helpers.convertToRadians = function( degrees ) {
    if (degrees != null) {
        return degrees * (3.1416/180);
    } else {
        return 0;
    }
};
