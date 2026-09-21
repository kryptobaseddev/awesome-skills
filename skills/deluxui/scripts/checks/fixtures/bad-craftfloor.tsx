// Craft floor violations, one per detector.
export function Landing() {
  return (
    <div>
      <h1 style={{ fontSize: "clamp(3rem, 9vw, 9rem)" }}>Shouting</h1>
      <h2>Second</h2>
      <h3>Third</h3>
      <section className="bg-blue-600">
        <p className="text-gray-500">Washed out secondary copy on a chromatic surface.</p>
      </section>
      <span className="bg-gradient-to-r from-purple-500 to-blue-500 bg-clip-text text-transparent">
        Gradient headline
      </span>
      <div>
        <p>01</p><h3>Discover</h3>
        <p>02</p><h3>Design</h3>
        <p>03</p><h3>Deliver</h3>
      </div>
      <ul>
        <li><span className="rounded-xl bg-blue-50 p-3">icon</span>Fast</li>
        <li><span className="rounded-xl bg-blue-50 p-3">icon</span>Safe</li>
        <li><span className="rounded-xl bg-blue-50 p-3">icon</span>Simple</li>
      </ul>
      <div className="opacity-0" data-reveal="fade" ref={useInView()}>
        Revealed on scroll, blank until then
      </div>
      <div style={{ zIndex: 9999 }}>Overlay</div>
    </div>
  );
}
