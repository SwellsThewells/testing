# Recovery tools

Scripts used to rebuild this Godot 3.5 project from the `savia_web_export` HTML5 export (`index.pck`).
This folder has a `.gdignore`, so Godot skips it.

1. `unpck.py index.pck <dir>` unpacks the pck (format v1, Godot 3.5.3).
2. `build.py <pck_dir> <out_dir> <godot_3.5_binary> <work_dir>` does the following:
   - decompiles every `.gdc` (GDScript bytecode v13) back to `.gd` with `gdc2gd.py`
   - converts `project.binary` back to `project.godot`
   - decodes imported textures (`.stex`) back to PNG/JPG/WEBP with `stex.py`
   - runs `convert_assets.gd` in headless Godot to rebuild `.wav`, `.ogg`, `.mp3` and `.obj` sources
3. `cmpgdc.py <orig_pck_dir> <reexported_pck_dir>` checks that the recompiled scripts match the original bytecode.
