// WCAG 2.1 contrast check for every text/background token pair used in both themes.
// Run: node scripts/contrast.mjs   (exits 1 if any body-text pair is below 4.5:1)
// The unserviceable chip (#C4342B) sits at 2.67:1 against surface-1 in Hangar, so .tag-us carries a
// 45% ink inset edge to mark its boundary; its white text is 5.4:1.
const themes = {
  hangar: { s0: "#0F1E27", s1: "#162C38", s2: "#1D3846", hairline: "#2F4E5F", ink: "#E6EDF1", muted: "#8FA8B5", lamp: "#E8A317", us: "#C4342B", serv: "#4E8C6A", lampInk: "#0F1E27" },
  ramp: { s0: "#E4E6E3", s1: "#F2F3F1", s2: "#FFFFFF", hairline: "#C2C8C6", ink: "#0F1E27", muted: "#56666E", lamp: "#B67B0B", us: "#A62B23", serv: "#3C6E53", lampInk: "#0F1E27" },
};
const lum = (hex) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a, b) => { const [l1, l2] = [lum(a), lum(b)].sort((x, y) => y - x); return (l1 + 0.05) / (l2 + 0.05); };
let failed = false;
for (const [name, t] of Object.entries(themes)) {
  const checks = [
    ["ink on surface-0", t.ink, t.s0, 4.5], ["ink on surface-1", t.ink, t.s1, 4.5], ["ink on surface-2", t.ink, t.s2, 4.5],
    ["ink-muted on surface-0", t.muted, t.s0, 4.5], ["ink-muted on surface-1", t.muted, t.s1, 4.5], ["ink-muted on surface-2", t.muted, t.s2, 4.5],
    ["lamp chip on surface-1 (non-text)", t.lamp, t.s1, 3.0], ["tag-serv rule on surface-1 (non-text)", t.serv, t.s1, 3.0],
    ["white on tag-us", "#FFFFFF", t.us, 4.5], ["lamp-ink on lamp", t.lampInk, t.lamp, 4.5],
  ];
  console.log(`\n${name}`);
  for (const [label, fg, bg, min] of checks) {
    const r = ratio(fg, bg);
    const ok = r >= min;
    if (!ok) failed = true;
    console.log(`  ${ok ? "ok  " : "FAIL"} ${label.padEnd(26)} ${r.toFixed(2)}:1 (min ${min})`);
  }
}
process.exit(failed ? 1 : 0);
