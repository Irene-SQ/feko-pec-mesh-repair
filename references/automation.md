# Python pipeline and report interpretation

Install: `python -m pip install -r requirements.txt`. Run `python scripts/mesh_pipeline.py --help`.

Use `audit` first. It reports raw vertex/face counts, open edge count (= edges used by only one face), nonmanifold edge count (= edges used by more than two faces), edges with inconsistent adjacent directed winding, exact face duplicates, zero-area faces, bounding box, max edge length and edge-connected components. Genus is only an **Euler-based candidate** on a closed consistently oriented input. MeshLab must independently verify vertex manifoldness/genus.

`clean`: default changes only zero-area faces, duplicate faces, unused vertices. With `--orient-two-face-edges` it propagates winding through ordinary two-face shared edges. Contradictory components stay unchanged. With `--merge-exact-vertices` it can weld geometrically coincident points and thereby modify electrical connectivity; only run after physical contact review.

`compare`: creates XY/XZ/YZ silhouettes and IoU with common axes, but no point-to-surface distance. Pixel IoU is not an assurance of physical fidelity, particularly for 3 GHz thin wings. The script records all changes in JSON, refuses to overwrite outputs and never deletes the source.

`reconstruct`: **explicitly lossy**, using a voxel shell, finite closing, hole fill, component filtering and marching cubes. The grid size is capped; the reconstructed surface can acquire thickness not present in the OBJ, merge distinct nacelles into wings or smooth small wing features. Never use `--keep-components 1` when a distinct PEC part needs to remain separate. Review multiple candidates and require explicit human acceptance. For high-accuracy wing geometry, prefer CAD-based surface reconstruction from original wing section data.

Example (with all coordinates confirmed in metres):

```powershell
python scripts/mesh_pipeline.py audit .\plane4_simplified.obj --json .\out\00_raw.json
python scripts/mesh_pipeline.py clean .\plane4_simplified.obj --output .\out\01_safe.obj --json .\out\01_safe.json --orient-two-face-edges
python scripts/mesh_pipeline.py reconstruct .\out\01_safe.obj --pitch 0.03 --close-voxels 1 --smooth-iters 4 --output .\out\02_candidate.obj --json .\out\02_candidate.json
python scripts/mesh_pipeline.py compare .\out\01_safe.obj .\out\02_candidate.obj --json .\out\03_compare.json --png .\out\03_compare.png
```

If the same artifact name already exists, generate a revision-specific filename instead of overwriting. STL can be exported from a reviewed OBJ with `trimesh.load(...).export('accepted.stl')`, then verify units in Feko.
