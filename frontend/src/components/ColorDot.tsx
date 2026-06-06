interface ColorDotProps {
  color: string;
  extraColor: string | null;
}

export default function ColorDot({ color, extraColor }: ColorDotProps) {
  const background = extraColor
    ? `linear-gradient(to right, ${color} 50%, ${extraColor} 50%)`
    : color;

  return (
    <span
      className="inline-block h-3 w-3 shrink-0 rounded-full"
      style={{ background }}
    />
  );
}
