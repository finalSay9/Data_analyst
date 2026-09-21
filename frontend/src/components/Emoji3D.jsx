import { useState } from "react";

// Renders Microsoft's Fluent Emoji "3D" style icons -- glossy, dimensional
// icons (MIT licensed: https://github.com/microsoft/fluentui-emoji),
// as opposed to lucide-react's thin outlines still used for small
// functional UI chrome (menu/close/back buttons, spinners) where
// detailed 3D art doesn't read well under ~16px and a spinner needs to
// actually spin.
//
// Served via jsdelivr's GitHub CDN (built for hotlinking, cached) rather
// than raw.githubusercontent.com (not designed as a CDN -- no caching
// guarantees under real traffic). Every path below was verified to
// return 200 before being added here.
const CDN_BASE = "https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets";

// name -> { path: folder/file within the Fluent Emoji repo, fallback: a
// real unicode emoji shown if the image fails to load (offline, CDN
// hiccup, ad blocker), so the UI never shows a broken-image icon.
const EMOJI_MAP = {
  barChart: { path: "Bar chart/3D/bar_chart_3d.png", fallback: "📊" },
  chartIncreasing: { path: "Chart increasing/3D/chart_increasing_3d.png", fallback: "📈" },
  chartDecreasing: { path: "Chart decreasing/3D/chart_decreasing_3d.png", fallback: "📉" },
  warning: { path: "Warning/3D/warning_3d.png", fallback: "⚠️" },
  information: { path: "Information/3D/information_3d.png", fallback: "ℹ️" },
  calendar: { path: "Spiral calendar/3D/spiral_calendar_3d.png", fallback: "🗓️" },
  inputNumbers: { path: "Input numbers/3D/input_numbers_3d.png", fallback: "🔢" },
  inputLatinLetters: {
    path: "Input latin letters/3D/input_latin_letters_3d.png",
    fallback: "🔤",
  },
  lightBulb: { path: "Light bulb/3D/light_bulb_3d.png", fallback: "💡" },
  outboxTray: { path: "Outbox tray/3D/outbox_tray_3d.png", fallback: "📤" },
  pageFacingUp: { path: "Page facing up/3D/page_facing_up_3d.png", fallback: "📄" },
  openFolder: { path: "Open file folder/3D/open_file_folder_3d.png", fallback: "📂" },
  ledger: { path: "Ledger/3D/ledger_3d.png", fallback: "📒" },
  abacus: { path: "Abacus/3D/abacus_3d.png", fallback: "🧮" },
  floppyDisk: { path: "Floppy disk/3D/floppy_disk_3d.png", fallback: "💾" },
  checkMarkButton: { path: "Check mark button/3D/check_mark_button_3d.png", fallback: "✅" },
  crossMark: { path: "Cross mark/3D/cross_mark_3d.png", fallback: "❌" },
  hourglass: { path: "Hourglass not done/3D/hourglass_not_done_3d.png", fallback: "⏳" },
  plus: { path: "Plus/3D/plus_3d.png", fallback: "➕" },
};

export default function Emoji3D({ name, size = 24, className = "" }) {
  const [errored, setErrored] = useState(false);
  const entry = EMOJI_MAP[name];

  if (!entry) return null;

  if (errored) {
    return (
      <span
        role="img"
        aria-hidden="true"
        style={{ fontSize: size * 0.85, lineHeight: 1 }}
        className={`inline-block ${className}`}
      >
        {entry.fallback}
      </span>
    );
  }

  return (
    <img
      src={`${CDN_BASE}/${encodeURI(entry.path)}`}
      alt=""
      loading="lazy"
      onError={() => setErrored(true)}
      className={`inline-block object-contain ${className}`}
      style={{ width: size, height: size }}
    />
  );
}
