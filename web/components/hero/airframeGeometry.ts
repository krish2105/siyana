import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { planTo3D } from "@/lib/airframe";

/**
 * Procedural narrow-body built from primitives. Units: 1 = 22 px of the plan view, fuselage
 * along z with the nose at -z. No external model, so the asset weight is zero.
 */

function fuselage(): THREE.BufferGeometry {
  const pts: THREE.Vector2[] = [
    new THREE.Vector2(0.001, -14.55),
    new THREE.Vector2(0.45, -13.8),
    new THREE.Vector2(0.85, -12.6),
    new THREE.Vector2(1.09, -10.8),
    new THREE.Vector2(1.09, 7.5),
    new THREE.Vector2(0.95, 10.5),
    new THREE.Vector2(0.62, 13.2),
    new THREE.Vector2(0.28, 14.5),
    new THREE.Vector2(0.001, 14.55),
  ];
  const g = new THREE.LatheGeometry(pts, 40);
  g.rotateX(Math.PI / 2); // lathe axis Y -> Z
  return g;
}

function plate(points: [number, number][], y: number, thickness: number): THREE.BufferGeometry {
  // points are plan-view (x, y) pixels; extrude in the lateral/z plane and lay flat.
  const shape = new THREE.Shape();
  points.forEach(([px, py], i) => {
    const [lat, , z] = planTo3D(px, py);
    if (i === 0) shape.moveTo(lat, z);
    else shape.lineTo(lat, z);
  });
  shape.closePath();
  const g = new THREE.ExtrudeGeometry(shape, { depth: thickness, bevelEnabled: false });
  g.rotateX(-Math.PI / 2); // shape (x, y) -> (x, z), extrusion along +y
  g.translate(0, y, 0);
  return g;
}

function engine(side: -1 | 1): THREE.BufferGeometry {
  const [lat, , z] = planTo3D(392, 210 + side * 86);
  const nacelle = new THREE.CylinderGeometry(0.62, 0.58, 2.8, 24, 1, true);
  nacelle.rotateX(Math.PI / 2);
  nacelle.translate(lat, -0.55, z);
  const core = new THREE.CylinderGeometry(0.28, 0.2, 3.2, 16);
  core.rotateX(Math.PI / 2);
  core.translate(lat, -0.55, z + 0.1);
  const pylon = new THREE.BoxGeometry(0.16, 0.7, 1.4);
  pylon.translate(lat, -0.05, z + 0.2);
  return mergeGeometries([nacelle, core, pylon], false)!;
}

function fin(): THREE.BufferGeometry {
  const shape = new THREE.Shape();
  shape.moveTo(10.3, 0.6);
  shape.lineTo(13.3, 4.4);
  shape.lineTo(14.4, 4.4);
  shape.lineTo(14.5, 0.3);
  shape.closePath();
  const g = new THREE.ExtrudeGeometry(shape, { depth: 0.14, bevelEnabled: false });
  g.rotateY(-Math.PI / 2); // (x,y) -> (z,y)
  g.translate(0.07, 0, 0);
  return g;
}

export type AirframeParts = { skin: THREE.BufferGeometry; edges: THREE.BufferGeometry; edgeLength: number };

let cached: AirframeParts | null = null;

export function buildAirframe(): AirframeParts {
  if (cached) return cached;
  const parts = [
    fuselage(),
    plate([[330, 188], [462, 42], [486, 46], [505, 188]], -0.25, 0.18),
    plate([[330, 232], [462, 378], [486, 374], [505, 232]], -0.25, 0.18),
    plate([[660, 192], [712, 130], [724, 132], [732, 192]], 0.25, 0.12),
    plate([[660, 228], [712, 290], [724, 288], [732, 228]], 0.25, 0.12),
    engine(-1),
    engine(1),
    fin(),
  ];
  const nonIndexed = parts.map((p) => (p.index ? p.toNonIndexed() : p));
  nonIndexed.forEach((p) => {
    for (const k of Object.keys(p.attributes)) if (k !== "position" && k !== "normal") p.deleteAttribute(k);
    if (!p.attributes.normal) p.computeVertexNormals();
  });
  const skin = mergeGeometries(nonIndexed, false)!;
  const edges = new THREE.EdgesGeometry(skin, 24);
  const pos = edges.attributes.position;
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  let edgeLength = 0;
  for (let i = 0; i < pos.count; i += 2) {
    a.fromBufferAttribute(pos, i);
    b.fromBufferAttribute(pos, i + 1);
    edgeLength += a.distanceTo(b);
  }
  cached = { skin, edges, edgeLength };
  return cached;
}

/** Zone glow position in 3D for a chapter anchor. Engines sit below the wing, everything else on the crown. */
export function zonePosition(x: number, y: number, chapter: string): [number, number, number] {
  const [lat, , z] = planTo3D(x, y);
  const engineChapters = new Set(["71", "72", "73", "74", "75", "76", "77", "78", "79", "80", "54"]);
  const wingChapters = new Set(["27", "28", "30", "33", "57", "36"]);
  const yPos = engineChapters.has(chapter) ? -0.55 : wingChapters.has(chapter) ? 0.05 : 1.15;
  return [lat, yPos, z];
}
