// cable-clip.scad — snap clip, hardcoded-ish; cable_d is the key knob
cable_d = 6;
wall = 2;
depth = 12;
$fn = 64;
eps = 0.01;
opening = cable_d * 0.8;
difference() {
  cylinder(h = depth, d = cable_d + 2 * wall);
  translate([0,0,-eps]) cylinder(h = depth + 2*eps, d = cable_d);
  translate([-opening/2, 0, -eps]) cube([opening, cable_d, depth + 2*eps]);
}
