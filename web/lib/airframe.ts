/**
 * Narrow-body airframe, plan view, nose to the left. viewBox 0 0 800 420, centreline y = 210.
 * Shared by the SVG plan view and the 3D scene (which maps x -> fuselage axis, y -> lateral).
 */
export const VIEWBOX = { w: 800, h: 420, cy: 210 };

export const FUSELAGE_PATH =
  "M 90 210 C 90 196 110 186 150 186 L 600 186 C 650 186 690 190 730 200 L 730 220 C 690 230 650 234 600 234 L 150 234 C 110 234 90 224 90 210 Z";

export const WING_UPPER = "M 330 188 L 462 42 L 486 46 L 505 188 Z";
export const WING_LOWER = "M 330 232 L 462 378 L 486 374 L 505 232 Z";
export const STAB_UPPER = "M 660 192 L 712 130 L 724 132 L 732 192 Z";
export const STAB_LOWER = "M 660 228 L 712 290 L 724 288 L 732 228 Z";
export const FIN_SPINE = "M 640 210 L 736 210";
export const ENGINE_UPPER = "M 362 124 a 30 13 0 1 0 60 0 a 30 13 0 1 0 -60 0 Z M 392 137 L 392 158";
export const ENGINE_LOWER = "M 362 296 a 30 13 0 1 0 60 0 a 30 13 0 1 0 -60 0 Z M 392 283 L 392 262";

/** One combined path so pathLength animates the whole outline as a single stroke. */
export const AIRFRAME_OUTLINE = [FUSELAGE_PATH, WING_UPPER, WING_LOWER, STAB_UPPER, STAB_LOWER, FIN_SPINE, ENGINE_UPPER, ENGINE_LOWER].join(" ");

export type ZoneAnchor = { x: number; y: number; label: string };

/** Where each ATA chapter lives on the airframe. Chapters sharing a system are offset so glows never overlap. */
export const ZONE_ANCHORS: Record<string, ZoneAnchor> = {
  "21": { x: 380, y: 222, label: "Air conditioning, belly packs" },
  "22": { x: 155, y: 196, label: "Auto flight, flight deck" },
  "23": { x: 240, y: 196, label: "Communications, crown antennas" },
  "24": { x: 205, y: 226, label: "Electrical power, E/E bay" },
  "25": { x: 300, y: 210, label: "Equipment and furnishings, cabin" },
  "26": { x: 440, y: 240, label: "Fire protection, cargo and engines" },
  "27": { x: 478, y: 118, label: "Flight controls, wing trailing edge" },
  "28": { x: 405, y: 318, label: "Fuel, wing tanks" },
  "29": { x: 428, y: 224, label: "Hydraulic power, wheel well" },
  "30": { x: 370, y: 104, label: "Ice and rain protection, leading edge" },
  "31": { x: 175, y: 224, label: "Indicating and recording, flight deck" },
  "32": { x: 455, y: 208, label: "Landing gear, main gear bay" },
  "33": { x: 470, y: 58, label: "Lights, wing tip" },
  "34": { x: 106, y: 210, label: "Navigation, radome" },
  "35": { x: 335, y: 196, label: "Oxygen, cabin overhead" },
  "36": { x: 360, y: 250, label: "Pneumatic, wing root" },
  "38": { x: 560, y: 222, label: "Water and waste, aft lavatory" },
  "49": { x: 716, y: 210, label: "APU, tail cone" },
  "52": { x: 220, y: 188, label: "Doors, forward entry" },
  "53": { x: 520, y: 208, label: "Fuselage, aft skin and frames" },
  "54": { x: 392, y: 150, label: "Nacelles and pylons" },
  "55": { x: 700, y: 148, label: "Stabilizers" },
  "56": { x: 138, y: 200, label: "Windows, flight deck" },
  "57": { x: 432, y: 342, label: "Wings, outer wing" },
  "71": { x: 375, y: 124, label: "Power plant, engine 1" },
  "72": { x: 392, y: 296, label: "Engine, engine 2" },
  "73": { x: 412, y: 306, label: "Engine fuel and control" },
  "74": { x: 372, y: 306, label: "Ignition" },
  "75": { x: 372, y: 286, label: "Engine air" },
  "76": { x: 412, y: 286, label: "Engine controls" },
  "77": { x: 412, y: 114, label: "Engine indicating" },
  "78": { x: 430, y: 124, label: "Exhaust, thrust reverser" },
  "79": { x: 372, y: 114, label: "Oil" },
  "80": { x: 354, y: 124, label: "Starting" },
};

export const RAIL_CHAPTERS: { chapter: string; title: string }[] = [
  { chapter: "21", title: "Air conditioning" },
  { chapter: "22", title: "Auto flight" },
  { chapter: "23", title: "Communications" },
  { chapter: "24", title: "Electrical power" },
  { chapter: "25", title: "Equipment" },
  { chapter: "26", title: "Fire protection" },
  { chapter: "27", title: "Flight controls" },
  { chapter: "28", title: "Fuel" },
  { chapter: "29", title: "Hydraulic power" },
  { chapter: "30", title: "Ice and rain" },
  { chapter: "31", title: "Indicating" },
  { chapter: "32", title: "Landing gear" },
  { chapter: "33", title: "Lights" },
  { chapter: "34", title: "Navigation" },
  { chapter: "35", title: "Oxygen" },
  { chapter: "36", title: "Pneumatic" },
  { chapter: "38", title: "Water and waste" },
  { chapter: "49", title: "APU" },
  { chapter: "52", title: "Doors" },
  { chapter: "53", title: "Fuselage" },
  { chapter: "54", title: "Nacelles and pylons" },
  { chapter: "55", title: "Stabilizers" },
  { chapter: "56", title: "Windows" },
  { chapter: "57", title: "Wings" },
  { chapter: "71", title: "Power plant" },
  { chapter: "72", title: "Engine" },
  { chapter: "73", title: "Engine fuel" },
  { chapter: "74", title: "Ignition" },
  { chapter: "75", title: "Engine air" },
  { chapter: "76", title: "Engine controls" },
  { chapter: "77", title: "Engine indicating" },
  { chapter: "78", title: "Exhaust" },
  { chapter: "79", title: "Oil" },
  { chapter: "80", title: "Starting" },
];

/** 2D plan coordinates -> 3D scene coordinates (metres, fuselage along z, nose at -z). */
export function planTo3D(x: number, y: number): [number, number, number] {
  const z = (x - 410) / 22;
  const lateral = (y - VIEWBOX.cy) / 22;
  return [lateral, 0, z];
}
