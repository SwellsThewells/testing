extends ARVROrigin

export(String) var default_action_set = "/actions/godot"


export(NodePath) var viewport = null


export var physics_factor = 2

var arvr_interface: ARVRInterface = null
var openvr_config = null

func get_openvr_config():
	return openvr_config

func _ready():

	openvr_config = preload("res://addons/godot-openvr/OpenVRConfig.gdns");
	if openvr_config:

		openvr_config = openvr_config.new()

		openvr_config.default_action_set = default_action_set

	arvr_interface = ARVRServer.find_interface("OpenVR")
	if arvr_interface and arvr_interface.initialize():
		var refresh_rate = 90


		var vp: Viewport = null
		if viewport:
			vp = get_node(viewport)
			if vp:
				vp.size = arvr_interface.get_render_targetsize()


		if not vp:
			vp = get_viewport()

		vp.arvr = true

		vp.keep_3d_linear = true

		OS.vsync_enabled = false

		if physics_factor > 0:
			Engine.iterations_per_second = refresh_rate * physics_factor
