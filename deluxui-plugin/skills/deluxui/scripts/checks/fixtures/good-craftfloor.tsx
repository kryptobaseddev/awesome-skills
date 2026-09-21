export function Landing() {
  return (
    <div>
      <h1 className="text-balance" style={{ fontSize: "clamp(2.5rem, 6vw, 4.5rem)" }}>Leading</h1>
      <h2 className="text-balance">Second</h2>
      <h3 className="text-balance">Third</h3>
      <section className="bg-blue-600">
        <p className="text-blue-100">Secondary copy tinted from the surface hue.</p>
      </section>
      <div style={{ zIndex: 40 }}>Overlay</div>
      <div className="motion-safe:animate-in">Visible by default, animates up.</div>
    </div>
  );
}
