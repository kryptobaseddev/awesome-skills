# Three.js and React Three Fiber

A 3D canvas is one opaque element to everything except a sighted mouse user. It is
also the most expensive thing on the page. Both facts are rules, not opinions.

## It does not exist for assistive technology

`<canvas>` has no accessible content. Whatever the scene conveys must also exist as
text, or that information is simply absent for part of your audience — and for search
engines, and for anyone whose GPU gave up.

```jsx
<figure>
  <Canvas aria-label="Interactive 3D view of the chassis" dpr={[1, 2]} frameloop="demand">
    …
  </Canvas>
  <figcaption>
    The chassis, shown from the front three-quarter. Mounting points are at the four
    corners; the intake sits centre-left. <a href="/specs">Full specification</a>.
  </figcaption>
</figure>
```

`S-CANVAS-A11Y` flags a canvas with no accessible name and no fallback content, and a
React Three Fiber `<Canvas>` with no text equivalent nearby. If the scene carries
data, COMP-015 applies as well: provide the values, units and comparisons in an
accessible form, not only as geometry.

## It costs a battery

`S-3D-PERF` checks two things, because they are the two that get skipped:

- **`frameloop="demand"`** unless the scene animates continuously. The default renders
  every frame forever, pinning a GPU core on a static model.
- **A `dpr` cap**, usually `dpr={[1, 2]}`. A 3x phone otherwise renders nine times the
  pixels, and the phone's thermal throttling makes everything else on the page slow too.

Also: dispose geometries and materials when unmounting, lazy-load the canvas below the
fold, and keep draco/meshopt compression on your models. A 40MB glTF is a five-second
LCP.

## Motion is motion

`autoRotate`, a `useFrame` loop and `OrbitControls` damping are all animation, and
`prefers-reduced-motion` applies to all three. Continuous rotation is a classic
vestibular trigger. Offer a still frame and let the user start the motion.

```jsx
const reduced = useReducedMotion();
<OrbitControls autoRotate={!reduced} enableDamping={!reduced} />
```

## Interaction

Pointer events on meshes are mouse-only unless you build alternatives. If selecting an
object matters, provide a keyboard-reachable list of the same objects beside the canvas
(A11Y-002, A11Y-009). Raycasting is not an input method for everyone.

## When not to use 3D

If the scene is decorative, it is a very expensive decoration — and `VIS-006` asks what
it is for. If the information is a measurement or a comparison, a chart communicates it
better, faster and to more people.
