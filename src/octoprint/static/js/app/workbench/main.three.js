var SELECT_COLOR = '#ECC459';
var DEFAULT_COLOR = '#8C8C8C';

// global namespace
var BEEwb = BEEwb || {};

/**
 * Global Variables declaration
 */
BEEwb.main = {
    transformControls: null,
    container: null,
    camera: null,
    scene: null,
    renderer: null,
    trackballControls: null,
    objects: null,
    raycaster: null,
    mouseVector: null,
    containerWidthOffset: 0,
    containerHeightOffset: 0,
    bed: 0,
    selectedObject: null,
    bedWidth: 190,
    bedHeight: 135,


    /**
     * Main initialization function
     */
    init: function() {

        this.container = document.getElementById( 'stl_container' );
        var bondingOffset = this.container.getBoundingClientRect();

        this.containerWidthOffset = bondingOffset.left;
        this.containerHeightOffset = bondingOffset.top;

        // renderer
        this.renderer = new THREE.WebGLRenderer({ alpha: true , antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight / 1.5);
        this.container.appendChild( this.renderer.domElement );

        this.camera = new THREE.PerspectiveCamera( 45, this.renderer.domElement.clientWidth / this.renderer.domElement.clientHeight, 1, 3000 );
        this.camera.position.set( 0, -200, 100 );
        this.camera.up.set( 0, 0, 1 ); // Without this the model is seen upside down
        this.camera.lookAt( new THREE.Vector3( 0, -100, 0 ) );

        this.scene = new THREE.Scene();
        //scene.add( new THREE.GridHelper( 90, 30 ) );

        var light1 = new THREE.PointLight( 0xffffff, 0.5 );
        light1.position.set( 200, 200, 200 );
        var light2 = new THREE.PointLight( 0xffffff, 0.5 );
        light2.position.set( -200, 200, 200 );
        var light3 = new THREE.PointLight( 0xffffff, 0.5 );
        light3.position.set( 200, -200, 200 );
        var light4 = new THREE.PointLight( 0xffffff, 0.5 );
        light4.position.set( -200, -200, 200 );

        this.scene.add( light1 );
        this.scene.add( light2 );
        this.scene.add( light3 );
        this.scene.add( light4 );

        this.objects = new THREE.Object3D();
        this.scene.add(this.objects);

        // Loads the model
        this.loadModel('BEE.stl');

        this.trackballControls = new THREE.TrackballControls( this.camera, this.container );
        this.trackballControls.rotateSpeed = 1.0;
        this.trackballControls.zoomSpeed = 0.7;
        this.trackballControls.panSpeed = 0.8;

        this.trackballControls.noZoom = false;
        this.trackballControls.noPan = false;

        this.trackballControls.staticMoving = true;
        this.trackballControls.dynamicDampingFactor = 0.3;

        // Auxiliar objects for model selection
        this.raycaster = new THREE.Raycaster();
        this.mouseVector = new THREE.Vector3();

        this.selectedObject = null;
        this.transformControls = null;

        // Adds the printer bed auxiliar object
        this._addBed(-95, -67.5, 0, 0, 0, 0, 1);

        window.addEventListener( 'resize', BEEwb.events.onWindowResize, false );
        //container.addEventListener( 'click', onMouseClick, false );
        this.container.addEventListener( 'mouseup', BEEwb.events.onMouseUp, false );
        this.container.addEventListener( 'mousedown', BEEwb.events.onMouseDown, false );

        this.container.addEventListener( 'mousemove', BEEwb.events.onMouseMove, false );
    },

    render: function () {

        if (this.transformControls != null) {
            this.transformControls.update();
        }
        this.renderer.render( this.scene, this.camera );
    },

    animate: function () {
        requestAnimationFrame( this.animate.bind(this) );
        this.trackballControls.update();
        this.renderer.render( this.scene, this.camera );
    },

    /**
     * Loads an STL model into the canvas
     *
     */
    loadModel: function (modelName) {

        // Removes previous object
        this.scene.remove(this.transformControls);

        var loader = new THREE.STLLoader();

        var that = this;
        // Colored binary STL
        loader.load('./stl/' + modelName, function ( geometry ) {
            var material = new THREE.MeshPhongMaterial( { color: 0x8C8C8C, specular: 0x111111, shininess: 200 } );

            var mesh = new THREE.Mesh( geometry, material );
            mesh.position.set( 0, 0, 0 );
            //mesh.rotation.set( - Math.PI , Math.PI , 0 );
            //mesh.scale.set( 1.5, 1.5, 1.5 );
            mesh.castShadow = true;

            that.scene.add( mesh );

            that.objects.add(mesh);

        });
    },

    /**
     * Starts the printing operation
     *
     */
    startPrint: function () {

    },

    /**
     * Saves the current scene
     *
     */
    saveScene: function () {

        var stlData = _generateSTLFromScene();

        var data = new FormData();
        data.append('file', stlData['stl'], stlData['sceneName']);

        $.ajax({
            url: API_BASEURL + "files/local",
            type: 'POST',
            data: data,
            contentType: false,
            processData: false,
            success: function(data) {

            },
            error: function() {

            }
        });
    },

    /**
     * Downloads the current scene in STL format
     *
     */
    downloadScene: function () {

        var stlData = BEEwb.helpers.generateSTLFromScene();

        saveAs(stlData['stl'], stlData['sceneName']);
    },

    /**
     * Selects a model in the canvas
     */
    selectModel: function ( model ) {

        // De-selects other objects
        this.objects.children.forEach(function( obj ) {

            //sets the default color in the object
            obj.material.color = new THREE.Color(DEFAULT_COLOR) ;
        });

        //sets the selected color in the object
        model.material.color = new THREE.Color(SELECT_COLOR);

        // Attaches the transform controls to the newly selected object
        if (this.selectedObject == null || this.selectedObject !== model) {
            this.scene.remove(this.transformControls);
            this.transformControls = new THREE.TransformControls( this.camera, this.renderer.domElement );
            this.transformControls.addEventListener( 'change', this.render.bind(this) );
            this.transformControls.attach( model );

            this.scene.add( this.transformControls );
        }

        // Sets the selected object to the first selected model
        this.selectedObject = model;

        // Activates the side buttons
        $('.model-selection').prop('disabled', false);

        // Shows the controls panel
        if ($('#workbench_ctrls_wrapper').css('display') == 'none') {
            $('#workbench_ctrls_wrapper').show();
        } else {
            if (!$('#workbench_ctrls').hasClass('in')) {
                $("#workbench_ctrls").collapse("show");
            }
        }

        // Activates the default transform operation
        BEEwb.transform_ops.activateMove();
    },

    /**
     * Removes all selections from the objects in the canvas
     */
     removeAllSelections: function() {

        this.objects.children.forEach(function( obj ) {

            //sets the default color in the object
            obj.material.color = new THREE.Color(DEFAULT_COLOR) ;
        });

        if (this.transformControls != null) {

            this.transformControls.detach();
            //transformControls.dispose();
        }

        this.selectedObject = null;

        $('.model-selection').prop('disabled', true);

        $('#btn-scale').removeClass('btn-primary');
        $('#btn-rotate').removeClass('btn-primary');
        $('#btn-move').removeClass('btn-primary');

        if ($('#workbench_ctrls_wrapper').css('display') != 'none') {
            if ($('#workbench_ctrls').hasClass('in')) {
                $("#workbench_ctrls").collapse('hide');
            }
        }
    },

    /**
     * Adds the printer bed to the canvas
     *
     */
     _addBed: function(x, y, z, rx, ry, rz, s ) {

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
        this.bed = mesh

        this.scene.add( this.bed );
    }

}
