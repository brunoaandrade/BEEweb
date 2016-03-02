var SELECT_COLOR = '#ECC459';
var DEFAULT_COLOR = '#8C8C8C';
var OUT_BOUNDS_COLOR = '#BD362F';

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
    bedHeight: 0,
    bedWidth: 0,
    bedDepth: 0,
    savedScenesFiles: [],

    /**
     * Main initialization function
     */
    init: function() {

        var that = this;
        // Loads the printer profile
        $.ajax({
            url: "bee/api/printer",
            type: 'GET',
            success: function(data) {

                that.bedDepth = data.profile.volume.depth;
                that.bedWidth = data.profile.volume.width;
                that.bedHeight = data.profile.volume.height;

            },
            error: function() {


            },
            complete: function() {
                that._initializeGraphics();
                that.render();
                that.animate();
            }
        });
    },

    /**
     * Initialization function callback
     */
    _initializeGraphics: function() {

        this.container = document.getElementById( 'stl_container' );
        var bondingOffset = this.container.getBoundingClientRect();

        this.containerWidthOffset = bondingOffset.left;
        this.containerHeightOffset = bondingOffset.top;

        // renderer
        this.renderer = new THREE.WebGLRenderer({ alpha: true , antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight / 1.5);
        this.container.appendChild( this.renderer.domElement );

        this.camera = new THREE.PerspectiveCamera(
         45, this.renderer.domElement.clientWidth / this.renderer.domElement.clientHeight, 1, 3000
        );
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
        this.loadModel('BEE.stl', true);

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
        this._addBed();

        window.addEventListener( 'resize', BEEwb.events.onWindowResize, false );
        window.addEventListener( 'keydown', BEEwb.events.onKeyDown);
        //container.addEventListener( 'click', onMouseClick, false );
        this.container.addEventListener( 'mouseup', BEEwb.events.onMouseUp, false );
        this.container.addEventListener( 'mousedown', BEEwb.events.onMouseDown, false );
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
    loadModel: function (modelName, systemFile) {

        // Workaround to prevent the "double" loading of a saved scene
        if (this.savedScenesFiles.indexOf(modelName) > -1) {
            return null;
        }

        var folder = './downloads/files/local/';
        if (systemFile === true) {
            folder = './stl/';
        } else {
            // Only shows the loading modal if it's model loaded by the user
            $('#loadingDialog').modal('show');
        }

        // Removes previous object
        this.scene.remove(this.transformControls);

        var loader = new THREE.STLLoader();

        var that = this;
        // Colored binary STL
        loader.load(folder + modelName, function ( geometry ) {
            var material = new THREE.MeshPhongMaterial( { color: 0x8C8C8C, specular: 0x111111, shininess: 200 } );

            // Updates the bounding box for the next calculations
            geometry.computeBoundingBox();
            var bbox = geometry.boundingBox;

            var xShift = 0;
            var yShift = 0;
            var zShift = 0;

            // Checks if the object is out of center in any axis
            if ( bbox.min.x > 0 ) {
                var centerX = 0.5 * ( bbox.max.x - bbox.min.x );
                xShift = bbox.min.x + centerX;
            }

            if ( bbox.min.y > 0 ) {
                var centerY = 0.5 * ( bbox.max.y - bbox.min.y );
                yShift = bbox.min.y + centerY;
            }

            if ( bbox.min.z > 0 ) {
                var centerZ = 0.5 * ( bbox.max.z - bbox.min.z );
                zShift = bbox.min.z + centerZ;
            }

            // Applies the transformation matrix for any necessary shift in position
            geometry.applyMatrix( new THREE.Matrix4().makeTranslation( -xShift, -yShift, -zShift ) );

            // Calculates any possible translation in the X axis due to the previously loaded model
            xShift = 0;
            if (that.objects.children.length > 0) {
                var lastObj = that.objects.children[that.objects.children.length-1];

                if (lastObj.geometry != null) {
                    var objBox = new THREE.Box3().setFromObject( lastObj );

                    xShift = objBox.max.x;
                }

                // Final shift calculation with the "left" side of the new object
                xShift = xShift - bbox.min.x + 1; // +1 for a small padding between the objects
            }

            var mesh = new THREE.Mesh( geometry, material );
            mesh.position.set( xShift, 0, 0 );

            //mesh.rotation.set( - Math.PI , Math.PI , 0 );
            //mesh.scale.set( 1.5, 1.5, 1.5 );
            mesh.castShadow = true;

            that.scene.add( mesh );

            that.objects.add(mesh);

            $('#loadingDialog').modal('hide');
        });
    },

    /**
     * Saves the current scene
     *
     * Returns the name of the generated scene STL file
     */
    saveScene: function ( filename ) {
        var scope = this;
        var stlData = BEEwb.helpers.generateSTLFromScene( this.objects );

        if (filename === undefined) {
            filename = BEEwb.helpers.generateSceneName();
        }

        var data = new FormData();
        data.append('file', stlData, filename);

        $.ajax({
            url: API_BASEURL + "files/local",
            type: 'POST',
            data: data,
            contentType: false,
            processData: false,
            success: function(data) {

                scope.savedScenesFiles.push(data.files.local.name);

                return true;
            },
            error: function() {

                return false;
            }
        });
    },

    /**
     * Downloads the current scene in STL format
     *
     */
    downloadScene: function () {

        var stlData = BEEwb.helpers.generateSTLFromScene( this.objects );

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
            $('#workbench_ctrls_wrapper').slideDown();
        } else {
            if (!$('#workbench_ctrls').hasClass('in')) {
                $("#workbench_ctrls").collapse("show");
            }
        }

        // Activates the default transform operation
        BEEwb.transformOps.activateMove();

        // Sets the initial size for the transform operations
        BEEwb.transformOps.setInitialSize();
    },

    /**
     * Checks if the selected object is out of the printing area
     */
    isSelectedObjectOutOfBounds: function () {

        if (BEEwb.helpers.objectOutOfBounds(BEEwb.main.selectedObject, [BEEwb.main.bedWidth, BEEwb.main.bedDepth, BEEwb.main.bedHeight])) {
            BEEwb.main.toggleObjectOutOfBounds(BEEwb.main.selectedObject, true);
        } else {
            BEEwb.main.toggleObjectOutOfBounds(BEEwb.main.selectedObject, false);
        }
    },

    /**
     * Toogles the out of bounds state for a model in the scene
     */
    toggleObjectOutOfBounds: function ( model, toogle ) {
        //sets the out of bounds color in the object
        if (model != null) {
            if (toogle) {
                model.material.color = new THREE.Color(OUT_BOUNDS_COLOR);
                $('#out-bound-msg').show();
            } else {
                model.material.color = new THREE.Color(SELECT_COLOR);
                $('#out-bound-msg').hide();
            }
        }
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
     _addBed: function( ) {

        // Rectangle
        var rectHeight = this.bedDepth;
        var rectWidth = this.bedWidth;

        // Loads bed support stl
        var that = this;
        var loader = new THREE.STLLoader();
        loader.load('./stl/btf_bed.stl', function ( geometry ) {
            var material = new THREE.MeshPhongMaterial( { color: 0x8C8C8C, specular: 0x111111, shininess: 200 } );

            var mesh = new THREE.Mesh( geometry, material );
            mesh.position.set( 0, 0, -0.1 );
            mesh.castShadow = false;

            that.scene.add( mesh );

        });

        var color = 0x468AC7;
        var extrudeSettings = { amount: 0.0, bevelEnabled: false}; //amount = thickness

        var rectShape = new THREE.Shape();
        rectShape.moveTo( 0,0 );
        rectShape.lineTo( 0, rectHeight );
        rectShape.lineTo( rectWidth, rectHeight );
        rectShape.lineTo( rectWidth, 0 );
        rectShape.lineTo( 0, 0 );

        // 3D shape
        var geometry = new THREE.ExtrudeGeometry( rectShape, extrudeSettings );

        var mesh = new THREE.Mesh( geometry, new THREE.MeshPhongMaterial( { color: color } ) );
        mesh.position.set( -(rectWidth / 2), -(rectHeight / 2), 0 );
        mesh.rotation.set( 0, 0, 0 );
        mesh.scale.set( 1, 1, 1 );

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
