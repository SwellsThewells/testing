extends OptionButton






var en = 1
var jp = 2
var fr = 3
var es = 4


func _ready():
	add_items()

func add_items():
	$ItemList.add_item(tr("English"))
	$ItemList.add_item(tr("Japanese"))
	$ItemList.add_item(tr("French"))
	$ItemList.add_item(tr("Spanish"))
