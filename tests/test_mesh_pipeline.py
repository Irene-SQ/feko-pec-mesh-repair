from pathlib import Path
import sys
import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mesh_pipeline import metrics, cleanup, orient_on_two_face_edges, reconstruct


def test_cube_topology():
    m = trimesh.creation.box(extents=[2, 1, 3])
    report = metrics(m)
    assert report['boundary_edge_count'] == 0
    assert report['nonmanifold_edge_count'] == 0
    assert report['genus_candidate'] == 0
    assert report['edge_connected_component_count'] == 1


def test_duplicate_and_degenerate_cleanup():
    m = trimesh.creation.box()
    f = np.vstack([m.faces, m.faces[0], [0, 0, 1]])
    damaged = trimesh.Trimesh(vertices=m.vertices, faces=f, process=False)
    assert metrics(damaged)['duplicate_face_count'] == 1
    clean, changes = cleanup(damaged)
    assert changes['duplicate_faces_removed'] == 1
    assert changes['zero_area_removed'] == 1
    assert metrics(clean)['boundary_edge_count'] == 0
    assert metrics(clean)['nonmanifold_edge_count'] == 0


def test_winding_safe_corrects_flip():
    m = trimesh.creation.box()
    flipped = m.faces.copy()
    flipped[0] = flipped[0, [0, 2, 1]]
    broken = trimesh.Trimesh(vertices=m.vertices, faces=flipped, process=False)
    assert metrics(broken)['double_incident_inconsistent_winding_edges'] > 0
    fixed, details = orient_on_two_face_edges(broken)
    assert details['faces_flipped'] >= 1
    assert metrics(fixed)['double_incident_inconsistent_winding_edges'] == 0


def test_reconstruction_preserves_bbox_location():
    m = trimesh.creation.box(extents=[0.8, 0.6, 0.6])
    m.apply_translation([3.1, -2.0, 1.5])
    out, _ = reconstruct(m, pitch=0.1, close_voxels=0, max_voxels=200_000,
                         keep_components=1, smooth_iters=0)
    assert abs(out.vertices.mean(axis=0)[0] - 3.1) < 0.15
    assert np.all(np.abs(out.bounds.mean(axis=0) - m.bounds.mean(axis=0)) < 0.15)
    assert metrics(out)['boundary_edge_count'] == 0
