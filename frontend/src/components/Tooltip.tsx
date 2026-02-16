interface TooltipProps {
  text: string;
}

export default function Tooltip({ text }: TooltipProps) {
  return (
    <div 
      className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-50"
    >
      <div className="relative bg-slate-900 text-white px-3 py-1.5 rounded shadow-lg">
        <div className="text-xs whitespace-nowrap">
          {text}
        </div>
        {/* Arrow pointing down */}
        <div 
          className="absolute left-1/2 top-full -translate-x-1/2 w-0 h-0"
          style={{
            borderLeft: '6px solid transparent',
            borderRight: '6px solid transparent',
            borderTop: '6px solid rgb(15 23 42)',
            marginTop: '-1px'
          }}
        />
      </div>
    </div>
  );
}

