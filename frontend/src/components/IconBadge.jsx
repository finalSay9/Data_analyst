// Instagram/Facebook-style app icon: a solid-color rounded shape with a
// simple white glyph on top. Flat, single accent color -- no gradients,
// no photorealism. This is the visual language used everywhere in the
// app that wants a "real icon" feel rather than a plain inline glyph.
const COLOR_CLASSES = {
  brand: "bg-brand-600",
  slate: "bg-slate-500",
  emerald: "bg-emerald-500",
  red: "bg-red-500",
  amber: "bg-amber-500",
  rose: "bg-rose-500",
  purple: "bg-purple-500",
  orange: "bg-orange-500",
  cyan: "bg-cyan-500",
};

const SIZE_CLASSES = {
  sm: "h-6 w-6 rounded-lg",
  md: "h-8 w-8 rounded-lg",
  lg: "h-11 w-11 rounded-xl",
  xl: "h-14 w-14 rounded-2xl",
};

const ICON_SIZE = {
  sm: 13,
  md: 16,
  lg: 22,
  xl: 28,
};

export default function IconBadge({
  icon: Icon,
  color = "brand",
  size = "md",
  shape = "square", // "square" | "circle"
  className = "",
}) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center ${SIZE_CLASSES[size]} ${
        COLOR_CLASSES[color]
      } ${shape === "circle" ? "rounded-full" : ""} ${className}`}
    >
      <Icon size={ICON_SIZE[size]} className="text-white" strokeWidth={2.25} />
    </div>
  );
}
