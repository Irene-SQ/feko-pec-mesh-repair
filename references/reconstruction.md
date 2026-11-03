# Reconstruction decision rules

Use only when preserving source geometry with conservative repair fails AND the user consents to geometry-changing reconstruction.

## Choose method by defect

- **A few holes:** reconstruct local boundary loops with CAD/Blender bridge or patch; compare patches to wing thickness/true geometry.
- **Multiple overlapping shells/self-intersections:** investigate connected components and physical electrical contacts; boolean union on clean solids when possible, conforming imprint/stitch across intended PEC contact.
- **Many tiny cracks with good silhouette:** voxel shell + small closing radius is a candidate; tune at **physical** scales, not visually pleasing smoothing alone.
- **Thin delta wing with broad, flat skins:** reconstruct upper and lower skin surfaces from surviving large triangles/section curves, then stitch through a physically justified leading/trailing-edge profile. Do not automatically project the whole wing to one plane.
- **Intentional open PEC sheet:** retain open sheet if solver supports it; don't force a fictitious solid thickness.

## Parameter sweeps

Work in model units. Typical sweep concept: choose a voxel pitch small compared with the narrowest **important** feature; explore several pitches and closing radii. Cap memory before allocating dense grids. Compare three-view outlines AND sectional wing thickness, wing-root continuity and both nacelles. Explicitly record lost/moved components. A genus of 0 can be produced by incorrectly deleting a real component: evaluate geometry before accepting.

## Reject conditions

- Wing tip/trailing edge flattened, or wrong thickness;
- Any named nacelle/tail/antenna missing;
- FEKO detects intersecting triangles or incorrect electrical contact;
- Large unexplained projection/volume changes;
- Result derived from an automatically pruned component whose physical identity is unknown;
- Missing evidence of EM mesh/complex echo convergence where 'simulation-ready' is claimed.
