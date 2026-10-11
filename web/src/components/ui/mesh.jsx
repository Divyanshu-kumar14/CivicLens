// MeshBackground (ReactBits Silk/Iridescence-inspired, zero WebGL cost):
// layered radial gradients + grid + noise via CSS. Static paint, no JS,
// no per-frame cost — the living-gradient depth without the shader bill.
export function MeshBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0">
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(900px 420px at 12% -8%, rgba(58,226,255,0.13), transparent 60%),' +
            'radial-gradient(760px 380px at 88% 4%, rgba(52,211,153,0.09), transparent 60%),' +
            'radial-gradient(680px 520px at 55% 110%, rgba(255,82,82,0.07), transparent 62%),' +
            'radial-gradient(520px 340px at 78% 78%, rgba(255,176,32,0.05), transparent 60%)',
        }}
      />
      <div
        className="absolute inset-0 opacity-[0.5]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),' +
            'linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)',
          backgroundSize: '44px 44px',
          maskImage: 'radial-gradient(ellipse 90% 70% at 50% 0%, black 30%, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse 90% 70% at 50% 0%, black 30%, transparent 75%)',
        }}
      />
    </div>
  );
}
