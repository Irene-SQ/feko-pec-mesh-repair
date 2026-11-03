---
name: feko-pec-mesh-repair
description: Repair and validate OBJ/STL aircraft or other PEC surface meshes for Altair CADFEKO/Feko MoM-MLFMM simulation. Use when a user needs MeshLab cleanup, mesh connectivity diagnosis, watertight surface candidates, geometry-preserving remeshing, or FEKO intersection/electrical-continuity checks. Produces auditable candidate models and reports; never assumes watertight alone means electromagnetically valid.
---

# FEKO PEC mesh repair / OBJ → audited STL

Treat geometry repair as **physical-model preparation**. Preserve the intended aircraft, thin structures, electrical contact, scale and pose. A numerically watertight surface with wrong engine/wing geometry is unacceptable. Obtain the user's approval before intentionally removing or merging aircraft parts.

## Required inputs

1. Input OBJ/STL and unit convention (e.g. metres). Identify its coordinate frame and intended PEC parts.
2. What must remain: fuselage, wings, tail, nacelles, blade-like parts, intentional slots, apertures, disconnected conductors.
3. Intended solver and conditions, especially Feko version, frequency and polarization; clarify whether zero-thickness PEC sheets are physically intended. **Closed watertight topology is not always necessary for valid FEKO open PEC sheets.**
4. Reference geometry if available. For scientific comparisons use the SAME accepted mesh for FEKO, FK/PO projections, and ground-truth evaluation, and log any changes.

## Workflow and decision gates

**A. Backup and inspect with MeshLab** — follow [references/meshlab.md](references/meshlab.md).
- Import the OBJ, save a separate backup.
- `Filters → Cleaning and Repairing`: Remove Duplicate Vertices, Remove Duplicate Faces, Remove Zero Area Faces, Remove Unreferenced Vertices (check units and damage after each).
- Display `Shading: Face`, `Back-Face: Double`, solid faces without wireframe; run `Select Border`, `Select non Manifold Edges`, `Compute Topological Measures`.
- Run `Merge Close Vertices` ONLY if a measured, very small distance threshold matches real duplicated seam vertices; never scale an assumed 0.01 mm to unknown units. Document vertex count change.
- `Split in Connected Components`; preserve source layer. Toggle CC visibility individually. Identify intentional small parts before any deletion. Use `Flatten Visible Layers` with **Merge Only Visible Layers** and **Delete Layers OFF**; ensure source is hidden, avoid double inclusion.
- Export `*_simplified.obj` without overwriting the original.

**B. Non-destructive Python audit and conservative cleanup** — use `scripts/mesh_pipeline.py` (see [references/automation.md](references/automation.md)).

```powershell
python scripts/mesh_pipeline.py audit "plane_simplified.obj" --json "out/01_audit.json"
python scripts/mesh_pipeline.py clean "plane_simplified.obj" --output "out/02_safe.obj" --json "out/02_safe.json" --orient-two-face-edges
```

`clean` removes degenerate and duplicate triangles and unused vertices; it only repairs winding across edges shared by exactly two faces. It **does not invent missing surfaces, bridge electrically disconnected parts, or resolve mesh intersections**. It will not overwrite outputs. Do not turn on `--merge-exact-vertices` until it is confirmed the surfaces should be electrically connected.

**C. Classify defects before deciding on a repair algorithm.**
- Duplicates, zero-area faces, inconsistent face winding: safely reversible cleanup, compare before and after.
- Unwelded near-coincident seams: measured weld with geometry/PEC contact review.
- Large holes, intersecting internal skins, wings penetrating fuselage, thin/open sheet surfaces: require local inspection and/or CAD remodeling. Do not indiscriminately run `Remove Faces`, `Close Holes`, or stitch every component.
- If truly closed geometry is required and conservative repair cannot do it, propose a **lossy** reconstruction candidate and obtain explicit approval for a geometry-changing operation.

**D. Optional explicitly lossy watertight candidate** (do not auto-select as accepted model):

```powershell
python scripts/mesh_pipeline.py reconstruct "out/02_safe.obj" --output "out/03_wrapped_candidate.obj" --json "out/03_wrapped.json" --pitch 0.02 --close-voxels 1 --smooth-iters 4
python scripts/mesh_pipeline.py compare "out/02_safe.obj" "out/03_wrapped_candidate.obj" --json "out/04_compare.json" --png "out/04_silhouettes.png"
```

**`--pitch` is in input geometry units**, `0.02` means 20 mm only if units are metres. The CLI enforces a voxel-memory cap and does not hide reconstruction changes. Voxel reconstruction can thicken wings, erase nacelles, create handles, or close physical gaps. Sweep pitch/closing parameters under explicit review, use multiple views and cross-sections, and compare both nacelles, wing tips and tail. Do not delete components solely to make genus zero. See [references/reconstruction.md](references/reconstruction.md).

**E. Geometry acceptance is a separate gate.**
- Audit candidate; verify boundary/nonmanifold counts, face orientation, components, (when defined) genus and mesh extent.
- Compare original versus candidate in XY/XZ/YZ silhouettes; ALSO inspect thin-wing thickness, wing-root joints, nacelle completeness, unwanted filled cavities and every intentionally separated part. Projection IoU alone cannot certify thickness accuracy.
- Require a human-approved, named canonical `*_accepted.obj`. Archive intermediate candidates and `repair_log.json`. If geometry changes cannot be justified, stop and request CAD-level work.

**F. FEKO validation is mandatory** — follow [references/feko.md](references/feko.md).
- Import canonical OBJ/STL in CADFEKO; check **units, bounding box, orientation and actual geometry**.
- `Mesh → Find → Intersecting Triangles → Entire model`: record exact FEKO message; **zero is required for the closed-mesh workflow**, but even zero does not prove correct electrical contact.
- `Display Options → Connectivity`: inspect red unconnected-edge indications and explain intentional PEC sheet boundaries; blue grid/outline lines alone are not a defect.
- Check that metal-to-metal contacts are meshed with appropriate compatible shared connectivity, not mere visual overlap.
- Verify no missing nacelle/wing after any connected-component pruning.
- Only then set PEC, frequency, MoM/MLFMM settings. Create an EM mesh and run **field convergence** (e.g., compare complex received echo between mesh refinements) to choose mesh size. Do not claim 12.5 mm is universally sufficient at 3 GHz.

## Output contract

Deliver: accepted OBJ + STL, audit JSONs, before/after image, change log (units, parameters, faces deleted, welded regions, parts retained/removed), CADFEKO check record, and solver-mesh convergence record. Label one of:

- `TOPOLOGY_CANDIDATE`: passed automated topology only;
- `GEOMETRY_ACCEPTED`: human visual/CAD geometry comparison passed;
- `FEKO_MODEL_CHECKED`: FEKO intersections, contacts and scale checked;
- `EM_VALIDATED`: FEKO MoM/MLFMM solve and complex-field grid-convergence verified.

**Never call a model FEKO-ready based only on watertight, genus 0, or a clean-looking screenshot.** If direct FEKO access is unavailable, state which manual FEKO checks remain outstanding and provide the candidate files.
