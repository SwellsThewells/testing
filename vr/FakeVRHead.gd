extends Camera

var yaw = 0
var pitch = 0

var active = false

func _input(event):

	if active:
		if (event is InputEventMouseMotion) or (event is InputEventScreenDrag):
			yaw = fmod(yaw - event.relative.x * Rhythia.sensitivity * 0.2, 360)
			pitch = clamp(
				pitch - event.relative.y * Rhythia.sensitivity * 0.2,
				-59,
				119
			)

			get_parent().rotation = Vector3(
				deg2rad(pitch - 30),
				deg2rad(yaw),
				0
			)

func _process(delta):

	if not current:
		make_current()

	if Input.is_action_just_pressed("fc_trigger"):
		active = not active
		if active:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
		else:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

func _ready():
	set_process(Rhythia.fake_vr)
	set_process_input(Rhythia.fake_vr)
