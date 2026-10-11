extends Node

onready var rootg = get_tree().root
onready var real_console = $ConsoleWindow





func ensure_console_is_in_world(_n):
	if get_parent().get_child(0) != self: raise()


func clear():
	real_console.clear(true)

func close():
	real_console.close(true)



func _ready():
	get_tree().connect("node_added", self, "ensure_console_is_in_world")
	call_deferred("raise")
