# CADFEKO 2026 acceptance and solver preparation

## Model geometry gate

1. In CADFEKO import accepted STL/OBJ. STL has **no unit metadata**; set the correct units before validation. Compare X/Y/Z bounding extents and aircraft orientation against source OBJ.
2. Use the `Mesh` tab → `Find` → `Intersecting Triangles` → `Entire model` and record the exact message (`No intersecting mesh elements found ...` or count). Many intersecting faces mean the geometry/contact requires further work. FEKO flags intersections which may not be electrically connected; a count of 0 is a mesh check, not a full physics guarantee.
3. In `Display Options` → `Connectivity`, inspect whether open/unconnected edges are intentional PEC boundaries, or failed seams. Do not treat ordinary blue grid/outline lines as proof of a defect. To distinguish display artefacts from real ripples, toggle triangle `Edges/Outline` and show only `Faces`, and inspect independent cross-sections.
4. Review current parts' electrical connection (mesh facets should share compatible edges/nodes where continuity is intended). Merging render layers is not enough. If geometry needs joining, prefer a CAD-level union/stitch/imprint or a correctly conforming mesh. Document the connection assumption.
5. Save an FEKO project version whose file basename includes model revision and mesh settings. Never overwrite an already published/run reference baseline.

## Electromagnetic gate

1. Treat imported mesh as geometric **Model Mesh**; simulation mesh and solver basis resolution are a separate concern.
2. Set PEC, frequency and plane-wave/Tx illumination, polarization, phase origin, and near-field Rx requests. For your FSR baseline, save Tx/Rx geometry and the complex-field convention (time dependence, incident/scattered selection, global phase).
3. Check mesh size relative to the wavelength and curvature; 12.5 mm at 3 GHz (~λ/8) is a starting configuration, not a proof of convergence. Thin trailing edges and nacelle joints may need local refinement.
4. Run at least two mesh densities with identical geometry and a fixed representative Tx/Rx. Compare **complex** electric-field components or aligned RHS without post-hoc fitted gain/phase:

   `NRMSE = ||s_fine - s_coarse||_2 / ||s_fine||_2`.

5. Then generate all baselines and record source phase reference. A FEKO-to-FK comparison must reuse one approved geometry for FEKO, FK projection and DDRI ground truth, and consistent coordinate frames/units. Maintain untouched Ex/Ey/Ez and processed complex RHS.

## Recorded checkpoints

- `feko_geometry_check.json`: file name/version, FEKO version, units, extents, count of intersecting triangles, connectivity note, screenshot paths, accepted/rejected.
- `em_convergence.json`: mesh settings, triangle counts, convergence thresholds, complex NRMSE, solver residue, memory/runtime, accepted/rejected.

Official references:

- [FEKO intersection search](https://help.altair.com/feko/topics/feko/user_guide/cadfeko/search_mesh_intersecting_elements_feko_t-cadfeko.htm)
- [Electrical connectivity](https://2022.help.altair.com/2022/feko/topics/feko/user_guide/cadfeko/electrical_connectivity_feko_c-cadfeko.htm)
- [Feko 2026 User Guide](https://help.altair.com/feko/pdf/Altair_Feko_User_Guide.pdf)
