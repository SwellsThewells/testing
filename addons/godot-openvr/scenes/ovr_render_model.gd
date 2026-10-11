extends MeshInstance

var ovr_render_model
var ws = 0
var controller_is_loaded = false

func apply_world_scale():
	var new_ws = ARVRServer.world_scale
	if (ws != new_ws):
		ws = new_ws
		scale = Vector3(ws, ws, ws)

func _load_controller_mesh(controller_name):
	if ovr_render_model.load_model(controller_name.substr(0, controller_name.length() - 2)):
		return ovr_render_model

	if ovr_render_model.load_model("generic_controller"):
		return ovr_render_model

	return Mesh.new()


func _ready():

	ovr_render_model = preload("res://addons/godot-openvr/OpenVRRenderModel.gdns").new()


	controller_is_loaded = false

func _process(delta):
	var controller = get_parent();
	if not controller is ARVRController:
		return

	if not controller.get_is_active():
		if controller_is_loaded:
			mesh = Mesh.new()
			controller_is_loaded = false
		return


	apply_world_scale()

	if controller_is_loaded:
		return


	var controller_name = controller.get_controller_name()



	mesh = _load_controller_mesh(controller_name)
	controller_is_loaded = true
