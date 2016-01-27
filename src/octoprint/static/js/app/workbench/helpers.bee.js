// global namespace
var BEEwb = BEEwb || {};

BEEwb.helpers = {}

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
    var blob = new Blob([stlData], {type: 'application/octet-binary'});

    var now = new Date();
    var sceneName = 'bee_' + now.getFullYear() + '_' + (now.getMonth()+1) + '_' + now.getDate()
    + '_' + now.getHours() + '_' + now.getMinutes() + '_' + now.getSeconds() + '.stl';

    return {'stl': blob, 'sceneName': sceneName};
}
