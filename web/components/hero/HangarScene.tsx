"use client";

import { Html, Line, OrbitControls } from "@react-three/drei";
import { Canvas, invalidate, useFrame, useThree } from "@react-three/fiber";
import { animate, motionValue, useReducedMotion } from "motion/react";
import { useRouter } from "next/navigation";
import { Component, type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { useUiState } from "@/components/providers/UiState";
import { buildAirframe, zonePosition } from "@/components/hero/airframeGeometry";
import { ZONE_ANCHORS } from "@/lib/airframe";
import type { ScheduleRun, TailRow, WatchRow, Zone } from "@/lib/api";
import { severityToken, staggerDelay } from "@/lib/severity";

const DRAW_SECONDS = 0.9;
const TIMELINE_END = DRAW_SECONDS + 0.24 + 0.35;

type Palette = { surface0: string; surface1: string; surface2: string; hairline: string; ink: string; inkMuted: string; lamp: string; tagUs: string };

function readPalette(theme: string): Palette {
  void theme; // palette is re-read when the theme changes
  const cs = getComputedStyle(document.documentElement);
  const v = (n: string) => cs.getPropertyValue(n).trim();
  return { surface0: v("--surface-0"), surface1: v("--surface-1"), surface2: v("--surface-2"), hairline: v("--hairline"), ink: v("--ink"), inkMuted: v("--ink-muted"), lamp: v("--lamp"), tagUs: v("--tag-us") };
}

type Parked = { tail: TailRow; bayIndex: number; bayName: string };

function layoutBays(tails: TailRow[], schedule: ScheduleRun | null): { bays: { id: string; name: string }[]; parked: Parked[] } {
  const bays = schedule?.baseline.bays?.length ? schedule.baseline.bays : [1, 2, 3, 4].map((i) => ({ id: `B${i}`, name: `Bay ${i}` }));
  const parked: Parked[] = [];
  const used = new Set<number>();
  for (const t of tails) {
    if (!t.bay_id) continue;
    const idx = bays.findIndex((b) => b.id === t.bay_id);
    if (idx >= 0 && !used.has(idx)) {
      used.add(idx);
      parked.push({ tail: t, bayIndex: idx, bayName: bays[idx].name });
    }
  }
  const rest = [...tails].filter((t) => !parked.some((p) => p.tail.registration === t.registration)).sort((a, b) => b.max_severity_rank - a.max_severity_rank || b.open_defects - a.open_defects);
  for (let i = 0; i < bays.length && rest.length; i++) {
    if (used.has(i)) continue;
    used.add(i);
    parked.push({ tail: rest.shift()!, bayIndex: i, bayName: bays[i].name });
  }
  return { bays, parked };
}

const BAY_W = 19;
const BAY_D = 34;

function bayCenter(i: number, n: number): [number, number, number] {
  return [(i - (n - 1) / 2) * BAY_W, 0, 0];
}

function Airframe({ palette, t, tail, zones, watch, position, onZone }: { palette: Palette; t: ReturnType<typeof motionValue<number>>; tail: TailRow; zones: Zone[]; watch: WatchRow[]; position: [number, number, number]; onZone: (chapter: string) => void }) {
  const { skin, edges, edgeLength } = useMemo(() => buildAirframe(), []);
  const skinMat = useRef<THREE.MeshStandardMaterial>(null);
  const edgeMat = useRef<THREE.LineDashedMaterial>(null);
  const lineRef = useRef<THREE.LineSegments>(null);
  const zoneMats = useRef<Map<string, THREE.MeshStandardMaterial>>(new Map());
  const [hover, setHover] = useState<string | null>(null);

  useEffect(() => {
    lineRef.current?.computeLineDistances();
  }, [edges]);

  const zoneList = useMemo(() => {
    const byChapter = new Map(zones.map((z) => [z.chapter, z]));
    return tail.chapters
      .filter((ch) => ZONE_ANCHORS[ch] && byChapter.get(ch))
      .map((ch) => ({ chapter: ch, zone: byChapter.get(ch)!, pos: zonePosition(ZONE_ANCHORS[ch].x, ZONE_ANCHORS[ch].y, ch) }));
  }, [tail.chapters, zones]);

  useFrame(() => {
    const v = t.get();
    const draw = Math.min(1, v / DRAW_SECONDS);
    if (edgeMat.current) {
      edgeMat.current.dashSize = edgeLength * draw + 0.001;
      edgeMat.current.gapSize = edgeLength;
      edgeMat.current.opacity = 0.35 + 0.65 * draw;
    }
    if (skinMat.current) skinMat.current.opacity = Math.max(0, Math.min(1, (v - DRAW_SECONDS * 0.6) / (DRAW_SECONDS * 0.5)));
    for (const z of zoneList) {
      const m = zoneMats.current.get(z.chapter);
      if (!m) continue;
      const start = staggerDelay(z.zone.max_severity_rank, DRAW_SECONDS);
      const k = Math.max(0, Math.min(1, (v - start) / 0.3));
      m.opacity = 0.85 * k;
      m.emissiveIntensity = (hover === z.chapter ? 1.6 : 0.9) * k;
    }
  });

  const rul = watch.filter((w) => w.tail === tail.registration && w.band !== "healthy");

  return (
    <group position={position} rotation={[0, Math.PI, 0]}>
      <mesh geometry={skin} castShadow={false} receiveShadow={false}>
        <meshStandardMaterial ref={skinMat} color={palette.hairline} roughness={0.45} metalness={0.3} transparent opacity={0} />
      </mesh>
      <lineSegments ref={lineRef} geometry={edges}>
        <lineDashedMaterial ref={edgeMat} color={palette.inkMuted} dashSize={0.001} gapSize={edgeLength} transparent opacity={0.35} />
      </lineSegments>
      {zoneList.map(({ chapter, zone, pos }) => {
        const token = severityToken(zone.max_severity_rank);
        const colour = token === "tag-us" ? palette.tagUs : palette.lamp;
        const r = zone.open_count > 4 ? 0.7 : zone.open_count > 1 ? 0.55 : 0.42;
        return (
          <group key={chapter} position={pos}>
            <mesh
              onClick={(e) => {
                e.stopPropagation();
                onZone(chapter);
              }}
              onPointerOver={(e) => {
                e.stopPropagation();
                setHover(chapter);
                document.body.style.cursor = "pointer";
                invalidate();
              }}
              onPointerOut={() => {
                setHover(null);
                document.body.style.cursor = "";
                invalidate();
              }}
            >
              <sphereGeometry args={[r, 20, 16]} />
              <meshStandardMaterial
                ref={(m) => {
                  if (m) zoneMats.current.set(chapter, m);
                }}
                color={colour}
                emissive={colour}
                emissiveIntensity={0}
                transparent
                opacity={0}
                roughness={0.3}
              />
            </mesh>
            {hover === chapter && (
              <Html center distanceFactor={26} style={{ pointerEvents: "none" }}>
                <div className="code whitespace-nowrap rounded-[2px] border border-hairline bg-surface-1 px-1.5 py-0.5 text-[11px] text-ink">
                  ATA {chapter} · {zone.open_count} open
                </div>
              </Html>
            )}
          </group>
        );
      })}
      {rul.map((w) => {
        const pos = zonePosition(392, 210 + (w.engine_pos === 1 ? -86 : 86), "72");
        return (
          <Html key={`${w.tail}-${w.engine_pos}`} position={[pos[0], pos[1] - 1.2, pos[2]]} center distanceFactor={26} style={{ pointerEvents: "none" }}>
            <div className={`code whitespace-nowrap rounded-[2px] px-1.5 py-0.5 text-[11px] ${w.band === "critical" ? "bg-tag-us text-white" : "bg-lamp text-lamp-ink"}`}>
              ENG {w.engine_pos} · RUL {w.predicted_rul.toFixed(0)}
            </div>
          </Html>
        );
      })}
      <Html position={[0, 2.6, -15.5]} center distanceFactor={30} style={{ pointerEvents: "none" }}>
        <div className="placard whitespace-nowrap rounded-[2px] border border-hairline bg-surface-1 px-2 py-1 text-ink">
          <span className="code normal-case tracking-normal">{tail.registration}</span> · {tail.aircraft_type}
          {tail.status === "unserviceable" && <span className="tag tag-us ml-2">U/S</span>}
        </div>
      </Html>
    </group>
  );
}

function FitCamera({ bays, controls }: { bays: number; controls: React.RefObject<OrbitControlsImpl | null> }) {
  const { camera, size } = useThree();
  useEffect(() => {
    const cam = camera as THREE.PerspectiveCamera;
    const width = bays * BAY_W + 6;
    const vFov = (cam.fov * Math.PI) / 180;
    const hFov = 2 * Math.atan(Math.tan(vFov / 2) * (size.width / size.height));
    const dist = (width / 2) / Math.tan(hFov / 2) * 1.08;
    const elev = 0.5; // radians above the floor plane
    cam.position.set(0, Math.sin(elev) * dist + 2, Math.cos(elev) * dist + 4);
    cam.lookAt(0, 0, 0);
    if (controls.current) {
      controls.current.target.set(0, 0, 0);
      controls.current.update();
    }
    invalidate();
  }, [bays, camera, size.width, size.height, controls]);
  return null;
}

function CameraRig({ target, controls }: { target: [number, number, number] | null; controls: React.RefObject<OrbitControlsImpl | null> }) {
  const { camera } = useThree();
  const anim = useRef<{ from: THREE.Vector3; to: THREE.Vector3; camFrom: THREE.Vector3; camTo: THREE.Vector3; mv: ReturnType<typeof motionValue<number>> } | null>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    if (!controls.current) return;
    const to = target ? new THREE.Vector3(...target) : new THREE.Vector3(0, 0, 0);
    const camTo = target ? new THREE.Vector3(target[0], 13, target[2] + 24) : (() => { const cam = camera as THREE.PerspectiveCamera; const d = camera.position.length(); return new THREE.Vector3(0, Math.sin(0.5) * d + 2, Math.cos(0.5) * d + 4).multiplyScalar(cam ? 1 : 1); })();
    const mv = motionValue(0);
    anim.current = { from: controls.current.target.clone(), to, camFrom: camera.position.clone(), camTo, mv };
    const ctrl = animate(mv, 1, { duration: reduce ? 0 : 0.8, ease: [0.16, 1, 0.3, 1], onUpdate: () => invalidate() });
    return () => ctrl.stop();
  }, [target, camera, controls, reduce]);

  useFrame(() => {
    const a = anim.current;
    if (!a || !controls.current) return;
    const k = a.mv.get();
    controls.current.target.lerpVectors(a.from, a.to, k);
    camera.position.lerpVectors(a.camFrom, a.camTo, k);
    controls.current.update();
    if (k >= 1) anim.current = null;
  });
  return null;
}

function Scene({ zones, tails, watchlist, schedule, palette }: { zones: Zone[]; tails: TailRow[]; watchlist: WatchRow[]; schedule: ScheduleRun | null; palette: Palette }) {
  const router = useRouter();
  const reduce = useReducedMotion();
  const { focusedTail, setFocusedTail } = useUiState();
  const controls = useRef<OrbitControlsImpl | null>(null);
  const { bays, parked } = useMemo(() => layoutBays(tails, schedule), [tails, schedule]);
  const t = useMemo(() => motionValue(0), []);

  useEffect(() => {
    // The one non-user-triggered motion: outline draws (900ms), then zones by severity.
    const ctrl = animate(t, TIMELINE_END, { duration: reduce ? 0 : TIMELINE_END, ease: "linear", onUpdate: () => invalidate() });
    return () => ctrl.stop();
  }, [t, reduce]);

  const focus = parked.find((p) => p.tail.registration === focusedTail);
  const target = focus ? bayCenter(focus.bayIndex, bays.length) : null;

  return (
    <>
      <ambientLight intensity={1.1} />
      <directionalLight position={[20, 40, 30]} intensity={1.6} />
      <directionalLight position={[-30, 20, -20]} intensity={0.5} />
      <FitCamera bays={bays.length} controls={controls} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.9, 0]}>
        <planeGeometry args={[bays.length * BAY_W + 30, BAY_D + 24]} />
        <meshStandardMaterial color={palette.surface1} roughness={0.95} />
      </mesh>
      {bays.map((b, i) => {
        const [x, , z] = bayCenter(i, bays.length);
        const p = parked.find((q) => q.bayIndex === i);
        const pts: [number, number, number][] = [
          [x - BAY_W / 2 + 0.6, -0.88, z - BAY_D / 2],
          [x + BAY_W / 2 - 0.6, -0.88, z - BAY_D / 2],
          [x + BAY_W / 2 - 0.6, -0.88, z + BAY_D / 2],
          [x - BAY_W / 2 + 0.6, -0.88, z + BAY_D / 2],
          [x - BAY_W / 2 + 0.6, -0.88, z - BAY_D / 2],
        ];
        return (
          <group key={b.id}>
            <Line points={pts} color={palette.hairline} lineWidth={1} />
            <Line points={[[x, -0.88, z - BAY_D / 2 + 1], [x, -0.88, z - BAY_D / 2 + 4]]} color={palette.hairline} lineWidth={1} />
            <Html position={[x, -0.6, z + BAY_D / 2 + 1.5]} center distanceFactor={34} style={{ pointerEvents: "auto" }}>
              <button
                type="button"
                onClick={() => p && setFocusedTail(focusedTail === p.tail.registration ? null : p.tail.registration)}
                className="placard whitespace-nowrap rounded-[2px] border border-hairline bg-surface-1 px-2 py-1 text-ink-muted hover:text-ink"
                aria-label={p ? `Focus ${p.tail.registration} in ${b.name}` : `${b.name} empty`}
              >
                {b.name}{p ? "" : " · empty"}
              </button>
            </Html>
            {p && (
              <Airframe palette={palette} t={t} tail={p.tail} zones={zones} watch={watchlist} position={bayCenter(i, bays.length)} onZone={(ch) => router.push(`/?ata=${ch}`, { scroll: false })} />
            )}
          </group>
        );
      })}
      <OrbitControls
        ref={controls}
        enablePan={false}
        enableZoom={false}
        minPolarAngle={0.42}
        maxPolarAngle={1.02}
        minAzimuthAngle={-0.6}
        maxAzimuthAngle={0.6}
        enableDamping
        dampingFactor={0.12}
        target={[0, 0, 0]}
      />
      <CameraRig target={target} controls={controls} />
    </>
  );
}

class GlBoundary extends Component<{ onFail: () => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onFail();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

export function HangarScene({ zones, tails, watchlist, schedule, onUnavailable }: { zones: Zone[]; tails: TailRow[]; watchlist: WatchRow[]; schedule: ScheduleRun | null; onUnavailable: () => void }) {
  const { theme } = useUiState();
  const palette = useMemo(() => readPalette(theme), [theme]);
  useEffect(() => {
    invalidate();
  }, [palette]);
  return (
    <div className="relative aspect-[2/1] w-full min-h-[320px] max-h-[520px]" role="img" aria-label="Three-dimensional hangar view: aircraft parked in bays with defect zones glowing by severity. The table below lists the same data.">
      <GlBoundary onFail={onUnavailable}>
        <Canvas
          dpr={[1, 1.75]}
          frameloop="demand"
          camera={{ position: [0, 30, 58], fov: 38, near: 0.5, far: 300 }}
          gl={{ antialias: true, alpha: true, powerPreference: "high-performance", failIfMajorPerformanceCaveat: true }}
          onCreated={({ gl }) => {
            gl.setClearColor(0x000000, 0);
          }}
          style={{ touchAction: "pan-y" }}
        >
          <Scene zones={zones} tails={tails} watchlist={watchlist} schedule={schedule} palette={palette} />
        </Canvas>
      </GlBoundary>
    </div>
  );
}
