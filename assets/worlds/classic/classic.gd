extends Spatial

var colors: Array = Rhythia.selected_colorset.colors

var target_color: Color = colors[0] * 0.5

func hit(col: Color):
	target_color = col * 0.5


func _process(delta):
	delta *= 10
	delta = min(delta, 1)
	$WorldEnvironment.environment.fog_sun_color = (target_color * delta) + ($WorldEnvironment.environment.fog_sun_color * (1 - delta))

func _ready():
	$WorldEnvironment.environment = $WorldEnvironment.environment.duplicate()
	get_parent().get_node("Game").connect("hit", self, "hit")

	var env = get_node("WorldEnvironment").environment
	if Rhythia.glow > 0:
		env.glow_enabled = true
		env.glow_intensity = Rhythia.glow
		env.glow_strength = 1
		env.glow_bloom = Rhythia.bloom
		env.glow_blend_mode = 1
		env.glow_hdr_scale = 1.72
		env.glow_high_quality = true
		env.glow_bicubic_upscale = true
