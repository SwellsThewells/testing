extends SpinBox

func upd():
	Rhythia.note_hitbox_size = float(str(value))


func _process(_d):
	if str(value) != str(Rhythia.note_hitbox_size): upd()

func _ready():
	value = Rhythia.note_hitbox_size
	connect("changed", self, "upd")
