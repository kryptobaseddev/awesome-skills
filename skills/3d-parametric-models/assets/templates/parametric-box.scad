// parametric-box.scad — a print-ready parametric box with a friction-fit lid.
//
// A reference for GOOD parametric OpenSCAD:
//   * every dimension is a named, Customizer-annotated parameter (top of file)
//   * a single `clearance` variable drives every mating fit (tune once, per printer)
//   * geometry is built from small, reusable modules
//   * walls/floor respect the 0.4 mm-nozzle minimums (>= 0.8 mm)
//   * units are millimeters; Z is up; the part sits on the bed (z = 0)
//
// Render:  openscad -o box.stl -D 'part="box"'  parametric-box.scad
//          openscad -o lid.stl -D 'part="lid"'  parametric-box.scad
//   or use the bundled render.sh / scad_params.py batch tool.

/* [What to render] */
// Which piece to export
part = "box";          // [box, lid, both]

/* [Outer size (mm)] */
width  = 60;           // [20:200]   outer X
depth  = 40;           // [20:200]   outer Y
height = 25;           // [10:150]   outer Z (box body, excluding lid)

/* [Walls & fit] */
wall   = 2.0;          // [0.8:0.2:4]  side wall thickness (>= 2x nozzle)
floor  = 1.6;          // [0.8:0.2:4]  floor/ceiling thickness
// Per-side gap between lid and box. 0.15-0.25 snug, 0.3-0.4 loose. Print a test!
clearance = 0.2;       // [0.05:0.05:0.6]
lid_height = 8;        // [4:40]     how deep the lid skirt is
round_r = 2;           // [0:0.5:10]  corner rounding radius (0 = sharp)

/* [Quality] */
// Facets per circle. 32 fast/draft, 64 good, 128 smooth. Higher = slower + bigger.
fn = 64;               // [16:8:160]

/* [Hidden] */
$fn = fn;
eps = 0.01;            // tiny overlap to keep booleans manifold

// ---- reusable geometry --------------------------------------------------------
// A rounded rectangular prism sitting on the bed (min z = 0).
module rbox(x, y, z, r) {
    if (r <= 0) {
        translate([-x/2, -y/2, 0]) cube([x, y, z]);
    } else {
        linear_extrude(z)
            offset(r) offset(-r)         // round outer corners
                square([x, y], center=true);
    }
}

// Hollow shell: outer rbox minus an inner cavity, leaving `wall` sides + `floor` base.
module box_body() {
    difference() {
        rbox(width, depth, height, round_r);
        translate([0, 0, floor])
            rbox(width - 2*wall, depth - 2*wall, height, max(0, round_r - wall));
    }
}

// Lid: a cap whose inner skirt slips over the box outer wall with `clearance` per side.
module lid() {
    skirt_in  = width  + 2*clearance;          // inner span hugs the box outside
    skirt_in2 = depth  + 2*clearance;
    difference() {
        rbox(skirt_in + 2*wall, skirt_in2 + 2*wall, lid_height + floor, round_r);
        translate([0, 0, floor])
            rbox(skirt_in, skirt_in2, lid_height + eps, max(0, round_r - wall));
    }
}

// ---- output -------------------------------------------------------------------
if (part == "box") box_body();
else if (part == "lid") lid();
else {                                          // both, side by side on the plate
    translate([-(width/2 + 5), 0, 0]) box_body();
    translate([ (width/2 + 5 + wall + clearance), 0, 0]) lid();
}
