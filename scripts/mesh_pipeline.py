#!/usr/bin/env python3
"""Auditable, conservative helpers for preparing PEC triangle meshes for Feko.

No mesh produced by this utility is automatically declared solver-ready.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from pathlib import Path
import json
import math
import sys

import numpy as np
import trimesh


def load_mesh(path: str | Path) -> trimesh.Trimesh:
    path = Path(path)
    obj = trimesh.load(path, process=False)
    if isinstance(obj, trimesh.Scene):
        obj = obj.to_geometry()
    if not isinstance(obj, trimesh.Trimesh):
        raise ValueError(f"Expected a triangle mesh: {path}")
    if obj.faces.shape[1] != 3 or len(obj.faces) == 0:
        raise ValueError("Input has no usable triangular faces")
    if not np.isfinite(obj.vertices).all():
        raise ValueError("Nonfinite vertex coordinates")
    return obj


def edge_incidence(faces: np.ndarray):
    directed = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]), axis=0)
    sorted_edges = np.sort(directed, axis=1)
    uniq, inverse, counts = np.unique(sorted_edges, axis=0, return_inverse=True, return_counts=True)
    faceids = np.tile(np.arange(len(faces), dtype=np.int64), 3)
    signs = np.where(directed[:, 0] < directed[:, 1], 1, -1)
    return uniq, inverse, counts, faceids, signs


def edge_components(n_faces: int, edge_keys: np.ndarray, face_ids: np.ndarray, counts: np.ndarray):
    """Edge-connected surface pieces; shared vertices alone do not connect pieces."""
    parent = np.arange(n_faces)
    sizes = np.ones(n_faces, dtype=np.int32)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def join(a, b):
        a, b = find(a), find(b)
        if a == b:
            return
        if sizes[a] < sizes[b]:
            a, b = b, a
        parent[b] = a
        sizes[a] += sizes[b]

    # Sort by edge identifier so each incident-face group is contiguous.
    order = np.argsort(edge_keys, kind="stable")
    ptr = 0
    for count in counts:
        if count > 1:
            faces = face_ids[order[ptr : ptr + count]]
            for f in faces[1:]:
                join(int(faces[0]), int(f))
        ptr += int(count)
    roots = [find(i) for i in range(n_faces)]
    _, component_sizes = np.unique(roots, return_counts=True)
    return sorted((int(c) for c in component_sizes), reverse=True)


def metrics(mesh: trimesh.Trimesh, *, components: bool = True) -> dict:
    vertices, faces = mesh.vertices, mesh.faces
    edges, keys, counts, faceids, signs = edge_incidence(faces)
    area_twice = np.linalg.norm(np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]],
                                         vertices[faces[:, 2]] - vertices[faces[:, 0]]), axis=1)
    face_keys = np.sort(faces, axis=1)
    duplicate_count = int(len(faces) - len(np.unique(face_keys, axis=0)))
    inconsistent = 0
    order = np.argsort(keys, kind="stable")
    ptr = 0
    for c in counts:
        if c == 2 and signs[order[ptr]] == signs[order[ptr + 1]]:
            inconsistent += 1
        ptr += int(c)
    diag = float(np.linalg.norm(np.ptp(vertices, axis=0)))
    tri_edges = np.linalg.norm(vertices[faces[:, [1, 2, 0]]] - vertices[faces[:, [0, 1, 2]]], axis=-1)
    extents = np.ptp(vertices, axis=0)
    result = {
        "vertex_count": int(len(vertices)), "face_count": int(len(faces)),
        "unique_edge_count": int(len(edges)),
        "boundary_edge_count": int(np.count_nonzero(counts == 1)),
        "nonmanifold_edge_count": int(np.count_nonzero(counts > 2)),
        "double_incident_inconsistent_winding_edges": inconsistent,
        "duplicate_face_count": duplicate_count,
        "exact_zero_area_faces": int(np.count_nonzero(area_twice == 0)),
        "bbox_min": vertices.min(axis=0).tolist(),
        "bbox_max": vertices.max(axis=0).tolist(),
        "bbox_extent": extents.tolist(), "bbox_diagonal": diag,
        "max_triangle_edge": float(tri_edges.max()),
        "area_sum": float(0.5 * area_twice.sum()),
        "euler_characteristic": int(len(vertices) - len(edges) + len(faces)),
        "watertight_edge_test": bool(np.all(counts == 2)),
        "units": "input model units (not automatically metres)",
    }
    if components:
        component_sizes = edge_components(len(faces), keys, faceids, counts)
        result["edge_connected_component_count"] = len(component_sizes)
        result["largest_components_faces"] = component_sizes[:12]
        closed = result["watertight_edge_test"] and duplicate_count == 0 and result["exact_zero_area_faces"] == 0
        if closed and inconsistent == 0:
            g = (2 * len(component_sizes) - result["euler_characteristic"]) / 2
            result["genus_candidate"] = int(g) if g >= 0 and float(g).is_integer() else None
            result["genus_note"] = "Euler-based; valid only for closed orientable vertex-manifold components. Verify in MeshLab."
        else:
            result["genus_candidate"] = None
    return result


def export(mesh: trimesh.Trimesh, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError(f"Refusing to overwrite: {dest}")
    mesh.export(str(dest))


def save_json(data, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError(f"Refusing to overwrite: {dest}")
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cleanup(mesh: trimesh.Trimesh, merge_exact: bool = False):
    v = mesh.vertices.copy()
    f = mesh.faces.copy()
    before = len(f)
    # Drop degenerate triangles, including triangles with duplicated indices.
    a2 = np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)
    f = f[a2 > 0]
    zero = before - len(f)
    # Remove duplicate triangles regardless of winding.
    key = np.sort(f, axis=1)
    _, unique_ids = np.unique(key, axis=0, return_index=True)
    f = f[np.sort(unique_ids)]
    duplicated = before - zero - len(f)
    merged = 0
    if merge_exact:
        unique_vertices, inverse = np.unique(v, axis=0, return_inverse=True)
        merged = len(v) - len(unique_vertices)
        v = unique_vertices
        f = inverse[f]
        # Welding may create zero-area or duplicate faces.
        a2 = np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)
        f = f[a2 > 0]
        key = np.sort(f, axis=1)
        _, ids = np.unique(key, axis=0, return_index=True)
        f = f[np.sort(ids)]
    used, new_ids = np.unique(f.ravel(), return_inverse=True)
    result = trimesh.Trimesh(vertices=v[used], faces=new_ids.reshape((-1, 3)), process=False)
    return result, {"zero_area_removed": int(zero), "duplicate_faces_removed": int(duplicated),
                    "exact_duplicate_vertices_merged": int(merged), "coordinate_displacement": 0.0}


def orient_on_two_face_edges(mesh: trimesh.Trimesh):
    f = mesh.faces.copy()
    _, keys, counts, faceids, signs = edge_incidence(f)
    order = np.argsort(keys, kind="stable")
    neighbors = defaultdict(list)
    ptr = 0
    for c in counts:
        if c == 2:
            p, q = order[ptr:ptr+2]
            a, b = int(faceids[p]), int(faceids[q])
            # If both edges run in the same direction, adjacent faces must have opposite flip parity.
            needs_xor = int(signs[p] == signs[q])
            neighbors[a].append((b, needs_xor))
            neighbors[b].append((a, needs_xor))
        ptr += int(c)
    flip = np.full(len(f), -1, dtype=np.int8)
    inconsistent_components = 0
    for start in range(len(f)):
        if flip[start] != -1:
            continue
        flip[start] = 0
        touched = [start]
        q = deque([start])
        bad = False
        while q:
            x = q.popleft()
            for y, xor in neighbors[x]:
                val = int(flip[x]) ^ xor
                if flip[y] == -1:
                    flip[y] = val
                    touched.append(y)
                    q.append(y)
                elif flip[y] != val:
                    bad = True
        if bad:
            inconsistent_components += 1
            flip[touched] = 0  # Preserve this entire conflicting region; needs manual work.
    f[flip == 1] = f[flip == 1][:, [0, 2, 1]]
    out = trimesh.Trimesh(vertices=mesh.vertices.copy(), faces=f, process=False)
    return out, {"faces_flipped": int(np.count_nonzero(flip == 1)),
                 "contradictory_components_left_unchanged": inconsistent_components}


def silhouettes(mesh1, mesh2, out: Path, resolution=512):
    try:
        import cv2
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install opencv-python and matplotlib for silhouette overlays") from exc
    coords = np.vstack([mesh1.vertices, mesh2.vertices])
    fig, axes = plt.subplots(3, 3, figsize=(10, 9), constrained_layout=True)
    metrics_by_view = {}
    for row, (k, axes_names) in enumerate((("XY", (0, 1)), ("XZ", (0, 2)), ("YZ", (1, 2)))):
        a, b = axes_names
        mn = coords[:, [a, b]].min(axis=0)
        mx = coords[:, [a, b]].max(axis=0)
        ext = max(mx - mn)
        if ext <= 0:
            raise ValueError("Degenerate projection")
        origin = (mn + mx) / 2 - 0.53 * ext
        scale = (resolution - 1) / (1.06 * ext)
        masks = []
        for mesh in (mesh1, mesh2):
            pts = np.rint((mesh.vertices[:, [a, b]] - origin) * scale).astype(np.int32)
            pts = np.clip(pts, 0, resolution-1)
            bitmap = np.zeros((resolution, resolution), dtype=np.uint8)
            for face in mesh.faces:
                triangle = pts[face]
                if len(np.unique(triangle, axis=0)) >= 3:
                    cv2.fillConvexPoly(bitmap, triangle, 255)
            masks.append(bitmap)
        a_mask, b_mask = masks
        union = np.count_nonzero(a_mask | b_mask)
        iou = float(np.count_nonzero(a_mask & b_mask) / union) if union else None
        metrics_by_view[k] = iou
        for col, arr in enumerate((a_mask, b_mask, cv2.addWeighted(a_mask, 0.5, b_mask, 0.5, 0))):
            axes[row, col].imshow(arr, origin="lower", cmap="gray", vmin=0, vmax=255)
            axes[row, col].axis("off")
        axes[row, 0].set_title(f"Source {k}")
        axes[row, 1].set_title(f"Candidate {k}")
        axes[row, 2].set_title(f"Overlay | IoU={iou:.3f}" if iou is not None else "Overlay")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite: {out}")
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return metrics_by_view


def reconstruct(mesh: trimesh.Trimesh, pitch: float, close_voxels: int, max_voxels: int,
                keep_components: int, smooth_iters: int):
    """Explicitly lossy candidate generation. Do not use as a one-click solver-ready repair."""
    from scipy import ndimage
    from skimage import measure
    if pitch <= 0 or close_voxels < 0:
        raise ValueError("pitch must be >0 and close-voxels must be >=0")
    estimate = np.ceil(np.ptp(mesh.vertices, axis=0) / pitch + 10).astype(np.int64)
    product = int(np.prod(estimate))
    if product > max_voxels:
        raise ValueError(f"Estimated voxel grid {estimate.tolist()} = {product:,} cells, exceeds --max-voxels={max_voxels:,}. Increase pitch.")
    # Voxelize triangle surfaces. This may alter thin sheets and merge tight gaps.
    vox = mesh.voxelized(pitch, method="subdivide")
    matrix = vox.matrix.copy()
    if matrix.size > max_voxels:
        raise ValueError(f"Actual voxel grid {matrix.shape} exceeds the memory cap")
    padding = max(3, close_voxels + 3)
    volume = np.pad(matrix, padding)
    if close_voxels:
        # close 3-D narrow channels/holes at the specified scale
        rad = close_voxels
        xx, yy, zz = np.ogrid[-rad:rad+1, -rad:rad+1, -rad:rad+1]
        ball = (xx*xx + yy*yy + zz*zz) <= rad*rad
        volume = ndimage.binary_closing(volume, structure=ball)
    volume = ndimage.binary_fill_holes(volume)
    labels, cc = ndimage.label(volume)
    if cc:
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        keep = np.argsort(sizes)[-keep_components:]
        volume = np.isin(labels, keep) & (labels > 0)
    if not volume.any():
        raise ValueError("Empty reconstruction after voxel processing")
    # Marching cubes indices are aligned with voxel-center transform. Avoid the
    # common bug of setting origin to original mesh bounds rather than voxel bounds.
    verts, faces, _, _ = measure.marching_cubes(volume.astype(np.uint8), level=0.5, spacing=(pitch, pitch, pitch))
    grid_origin = np.array(vox.transform[:3, 3], dtype=float)
    verts += grid_origin - pitch * padding
    out = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    if smooth_iters:
        trimesh.smoothing.filter_taubin(out, lamb=0.5, nu=0.53, iterations=smooth_iters)
    out.remove_unreferenced_vertices()
    return out, {"pitch_input_units": pitch, "close_voxels": close_voxels,
                 "largest_components_retained": keep_components,
                 "taubin_iterations": smooth_iters, "voxel_grid_shape": list(volume.shape),
                 "caution": "Geometry-changing reconstruction; requires MeshLab + FEKO inspection and field convergence."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("audit", help="Non-destructive topology report")
    a.add_argument("input")
    a.add_argument("--json", required=True)
    c = sp.add_parser("clean", help="Only proven-safe triangle cleanup; original not overwritten")
    c.add_argument("input")
    c.add_argument("--output", required=True)
    c.add_argument("--json", required=True)
    c.add_argument("--merge-exact-vertices", action="store_true", help="Explicit opt-in: may create electrical connections")
    c.add_argument("--orient-two-face-edges", action="store_true")
    r = sp.add_parser("reconstruct", help="LOSSY, opt-in watertight candidate via voxel surface reconstruction")
    r.add_argument("input")
    r.add_argument("--output", required=True)
    r.add_argument("--json", required=True)
    r.add_argument("--pitch", type=float, required=True, help="Voxel size in OBJ units (typically metres)")
    r.add_argument("--close-voxels", type=int, default=1)
    r.add_argument("--smooth-iters", type=int, default=4)
    r.add_argument("--keep-components", type=int, default=1)
    r.add_argument("--max-voxels", type=int, default=30_000_000)
    p = sp.add_parser("compare", help="Inspect bounding boxes + orthographic silhouette overlap")
    p.add_argument("source")
    p.add_argument("candidate")
    p.add_argument("--json", required=True)
    p.add_argument("--png", required=True)
    p.add_argument("--resolution", type=int, default=512)
    args = ap.parse_args()
    if args.cmd == "audit":
        data = metrics(load_mesh(args.input))
        save_json(data, Path(args.json))
    elif args.cmd == "clean":
        source = load_mesh(args.input)
        out, operations = cleanup(source, args.merge_exact_vertices)
        if args.orient_two_face_edges:
            out, winding = orient_on_two_face_edges(out)
            operations.update(winding)
        result = {"actions": operations, "before": metrics(source), "after": metrics(out)}
        export(out, Path(args.output))
        save_json(result, Path(args.json))
        data = result
    elif args.cmd == "reconstruct":
        source = load_mesh(args.input)
        out, params = reconstruct(source, args.pitch, args.close_voxels,
                                  args.max_voxels, args.keep_components, args.smooth_iters)
        result = {"settings": params, "before": metrics(source), "after": metrics(out)}
        export(out, Path(args.output))
        save_json(result, Path(args.json))
        data = result
    elif args.cmd == "compare":
        original, candidate = load_mesh(args.source), load_mesh(args.candidate)
        iou = silhouettes(original, candidate, Path(args.png), args.resolution)
        data = {"source": metrics(original), "candidate": metrics(candidate),
                "silhouette_iou": iou,
                "warning": "Orthographic silhouettes do not measure surface thickness, electrical connectivity, or scattering accuracy."}
        save_json(data, Path(args.json))
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
