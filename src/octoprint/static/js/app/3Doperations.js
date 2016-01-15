/**
 * Global Variables declaration
 */
var transformControls, container, camera, cameraTarget,
    scene, renderer, trackballControls, objects, raycaster,
    mouseVector, containerWidthOffset, containerHeightOffset, bed, selectedObject;

var SELECT_COLOR = '#ECC459';
var DEFAULT_COLOR = '#8C8C8C';

/**
 * Main initialization function
 */
function init() {

    container = document.getElementById( 'stl_container' );
    var bondingOffset = container.getBoundingClientRect();

    containerWidthOffset = bondingOffset.left;
    containerHeightOffset = bondingOffset.top;

    // renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight / 1.5);
    container.appendChild( renderer.domElement );

    camera = new THREE.PerspectiveCamera( 45, renderer.domElement.clientWidth / renderer.domElement.clientHeight, 1, 3000 );
    camera.position.set( 0, 200, 100 );
    camera.up.set( 0, 0, 1 ); // Without this the model is seen upside down
    camera.lookAt( new THREE.Vector3( 0, 100, 0 ) );

    scene = new THREE.Scene();
    //scene.add( new THREE.GridHelper( 90, 30 ) );

    var light1 = new THREE.PointLight( 0xffffff, 0.5 );
    light1.position.set( 200, 200, 200 );
    var light2 = new THREE.PointLight( 0xffffff, 0.5 );
    light2.position.set( -200, 200, 200 );
    var light3 = new THREE.PointLight( 0xffffff, 0.5 );
    light3.position.set( 200, -200, 200 );
    var light4 = new THREE.PointLight( 0xffffff, 0.5 );
    light4.position.set( -200, -200, 200 );
    scene.add( light1 );
    scene.add( light2 );
    scene.add( light3 );
    scene.add( light4 );

    addBed(-95, -67.5, 0, 0, 0, 0, 1);

    objects = new THREE.Object3D();
    scene.add(objects);

    // Loads the model
    loadModel('3DBenchy.stl');

    trackballControls = new THREE.TrackballControls( camera, container );
    trackballControls.rotateSpeed = 1.0;
    trackballControls.zoomSpeed = 0.7;
    trackballControls.panSpeed = 0.8;

    trackballControls.noZoom = false;
    trackballControls.noPan = false;

    trackballControls.staticMoving = true;
    trackballControls.dynamicDampingFactor = 0.3;

    // Auxiliar objects for model selection
	raycaster = new THREE.Raycaster();
	mouseVector = new THREE.Vector3();

	selectedObject = null;

    window.addEventListener( 'resize', onWindowResize, false );
    //container.addEventListener( 'click', onMouseClick, false );
    container.addEventListener( 'mouseup', onMouseUp, false );
    container.addEventListener( 'mousedown', onMouseDown, false );
}

function render() {
    transformControls.update();
    renderer.render( scene, camera );
}

function animate() {
    requestAnimationFrame( animate );
    trackballControls.update();
    renderer.render( scene, camera );
}

/**
 * Loads an STL model into the canvas
 *
 */
function loadModel(modelName) {

    // Removes previous object
    scene.remove(transformControls);

    var loader = new THREE.STLLoader();

    transformControls = new THREE.TransformControls( camera, renderer.domElement );
    transformControls.addEventListener( 'change', render );

    // Colored binary STL
    loader.load('./stl/' + modelName, function ( geometry ) {
        var material = new THREE.MeshPhongMaterial( { color: 0x8C8C8C, specular: 0x111111, shininess: 200 } );

        var mesh = new THREE.Mesh( geometry, material );
        mesh.position.set( 0, 0, 0 );
        //mesh.rotation.set( - Math.PI , Math.PI , 0 );
        //mesh.scale.set( 1.5, 1.5, 1.5 );
        //mesh.castShadow = true;

        // Attach tranform controls to object
        transformControls.attach( mesh );

        scene.add( mesh );
        scene.add( transformControls );

        objects.add(mesh);

    });
}


/**
 * Saves the current scene
 *
 */
function saveScene() {
    var exporter = new THREE.STLExporter();

    // Removes bed from scene before parsing
    scene.remove( bed );
    debugger;
    var stlString = exporter.parse( scene );

    var blob = new Blob([stlString], {type: 'text/plain'});

    // Re-inserts the bed into the scene
    scene.add( bed );

    saveAs(blob, 'scene.stl');
}


/**
 * Removes a model from the scene
 *
 */
function removeModel(modelObj) {
    scene.remove(modelObj);
    objects.remove(modelObj);
    scene.remove(transformControls);
}

/**
 * Removes the selected model from the scene
 *
 */
function removeSelected() {
    if (selectedObject !== null) {
        removeModel(selectedObject);

        selectedObject = null;
        $('.model-selection').prop('disabled', true);
    }
}

/**
 * Activates the rotate mode for the selected object
 *
 */
function activateRotate() {
    if (transformControls !== null && selectedObject !== null) {
        transformControls.setMode("rotate");
    }
}

/**
 * Activates the scale mode for the selected object
 *
 */
function activateScale() {
    if (transformControls !== null && selectedObject !== null) {
        transformControls.setMode("scale");
    }
}

/**
 * Activates the translate (move) mode for the selected object
 *
 */
function activateMove() {
    if (transformControls !== null && selectedObject !== null) {
        transformControls.setMode("translate");
    }
}



/**
 * OnWindowResize event function
 */
function onWindowResize() {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();

    renderer.setSize( window.innerWidth, window.innerHeight / 1.5 );

    render();
}

/**
 * OnMouseDown event function
 */
function onMouseDown( e ) {

    // Records the first click position
    mouseVector.x = 2 * ( (e.clientX - containerWidthOffset) / renderer.domElement.clientWidth) - 1;
    mouseVector.y = 1 - 2 * ( (e.clientY - containerHeightOffset) / renderer.domElement.clientHeight );
    mouseVector.z = 0.5;
}

/**
 * OnMouseUp event function
 */
function onMouseUp( e ) {

    var prevMouseVector = mouseVector.clone();

    mouseVector.x = 2 * ( (e.clientX - containerWidthOffset) / renderer.domElement.clientWidth) - 1;
    mouseVector.y = 1 - 2 * ( (e.clientY - containerHeightOffset) / renderer.domElement.clientHeight );
    mouseVector.z = 0.5;

    raycaster.setFromCamera( mouseVector, camera );

    var intersects = raycaster.intersectObjects( objects.children );

    // Selects the first found intersection
    if (intersects.length > 0) {

        var intersection = intersects[ 0 ];
        var model = intersection.object;

        // De-selects other objects
        objects.children.forEach(function( obj ) {

            // create color gray
            var colorObject = new THREE.Color(DEFAULT_COLOR) ;
            //set the color in the object
            obj.material.color = colorObject;
        });

        if (selectedObject !== model) {
            // Attaches the transform controls to the newly selected object
            transformControls.attach( model );
        }

        //obj.material.color.setRGB( 236, 196, 89 ); // Sets color to yellow 0xECC459
        // create color gray
        var colorObject = new THREE.Color(SELECT_COLOR) ;
        //set the color in the object
        model.material.color = colorObject;

        selectedObject = model;
        $('.model-selection').prop('disabled', false);

    } else if (prevMouseVector.x == mouseVector.x
        && prevMouseVector.y == mouseVector.y
        && prevMouseVector.z == mouseVector.z) { // It means the scene wasn't dragged and so we should remove all selections

        objects.children.forEach(function( obj ) {

            // create color gray
            var colorObject = new THREE.Color(DEFAULT_COLOR) ;
            //set the color in the object
            obj.material.color = colorObject;
        });

        selectedObject = null;
        $('.model-selection').prop('disabled', true);
    }
}

/**
 * Adds the printer bed to the canvas
 *
 */
function addBed(x, y, z, rx, ry, rz, s ) {

    var color = 0x3BADE6;
    var extrudeSettings = { amount: 1, bevelEnabled: false};

    // Rectangle
    var rectLength = 190, rectWidth = 135;

    var rectShape = new THREE.Shape();
    rectShape.moveTo( 0,0 );
    rectShape.lineTo( 0, rectWidth );
    rectShape.lineTo( rectLength, rectWidth );
    rectShape.lineTo( rectLength, 0 );
    rectShape.lineTo( 0, 0 );

    // 3D shape
    var geometry = new THREE.ExtrudeGeometry( rectShape, extrudeSettings );

    var mesh = new THREE.Mesh( geometry, new THREE.MeshPhongMaterial( { color: color } ) );
    mesh.position.set( x, y, z-1 );
    mesh.rotation.set( rx, ry, rz );
    mesh.scale.set( s, s, s );

    // flat shape
    /*
    var geometry = new THREE.ShapeGeometry( rectShape );

    var mesh = new THREE.Mesh( geometry, new THREE.MeshPhongMaterial( { color: color, side: THREE.DoubleSide } ) );
    mesh.position.set( x, y, z );
    mesh.rotation.set( rx, ry, rz );
    mesh.scale.set( s, s, s );
    */

    // Sets the global bed var
    bed = mesh

    scene.add( bed );
}
