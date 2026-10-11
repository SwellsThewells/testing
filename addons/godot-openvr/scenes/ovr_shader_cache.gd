extends Spatial

var countdown = 2


func _process(delta):
	countdown = countdown - 1
	if countdown == 0:
		visible = false
		set_process(false)
