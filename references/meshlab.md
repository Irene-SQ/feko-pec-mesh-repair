# MeshLab GUI sequence (safety-first)

Applicable to the Plane-3 / Plane-4 style of aircraft mesh, but do not assume every model must be closed. Make an immutable copy of the original OBJ before any operation.

## 1. Clean input

Open `File → Import Mesh`. `File → Export Mesh As` to `plane_step0.obj` to establish a backup. For OBJ export with vertex normals selected, remember normals are not a substitute for consistent triangle winding.

Run in `Filters → Cleaning and Repairing` (names can vary by MeshLab version):

1. `Remove Duplicate Vertices`
2. `Remove Duplicate Faces`
3. `Remove Zero Area Faces`
4. `Remove Unreferenced Vertices`

Save `plane_step1_clean.obj`. Check the number of affected vertices/faces after EACH filter. If an entire wing disappears, undo, reload the backup and inspect scene/object groups and back-face settings.

## 2. Visual and topological diagnosis

- In visualization panel, show face shading, back-face `Double`, and hide wireframe to inspect intact skins.
- `Ctrl + F`: `Select Border`, inspect free edges, especially leading/trailing edges and wing roots.
- `Select non Manifold Edges`: red selection typically includes incident triangles; do **not** delete all red faces.
- `Compute Topological Measures`: record boundary edges, non-two-manifold edges/vertices, number of connected components, genus if defined.
- For narrow seams, inspect from both sides and zoom in. Selected red faces ≠ all incorrect faces.

## 3. Near-seam weld (optional)

`Merge Close Vertices` shows `Merging distance (abs and %)`: first box is absolute in mesh units, second is a linked percentage of bounding-box diagonal. Example: **0.00001 m = 0.01 mm** when the OBJ is in metres. This is an example only; choose the threshold based on measured seam width and nearby thin structures. Zero merged vertices means the chosen tolerance did not match any points: do NOT increase blindly. Re-audit immediately after.

## 4. Select retained aircraft parts

`Split in Connected Components`, set `Delete source mesh = False`. Open Layers; hide all new CC layers then toggle each individually. Preserve fuselage, both wings, tail, nacelles, and any intentionally retained antennas or blades. Deleting a propeller changes the target's scattering response and must be documented as a new simplified target. Do not delete a large piece solely because it is disconnected.

`Filters → Mesh Layer → Flatten Visible Layers`:
- `Merge Only Visible Layers = True`
- `Delete Layers = False`
- Ensure original/source mesh layer is hidden, and no component appears twice.

Export as `plane_simplified.obj` and independently re-audit. Flattening layers by itself does not guarantee welded contact or manifold topology.

## 5. Caveats

`Close Holes` parameter `Max size to be closed` refers to **boundary edge count**, not millimetres. Only fill a boundary cycle after deciding it is a real hole. Long double-skin seam may need bridging or CAD repair, not a global fill. Never use global `Repair Non Manifold Edges → Remove Faces` without visual approval; it can strip thin wing skins.
