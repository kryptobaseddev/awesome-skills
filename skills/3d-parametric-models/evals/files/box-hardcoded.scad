// box-hardcoded.scad — magic numbers everywhere; the lid never fits right.
difference() {
  cube([50, 30, 20]);
  translate([2, 2, 2]) cube([46, 26, 20]);
}
translate([60, 0, 0]) difference() {     // the "lid"
  cube([50, 30, 8]);
  translate([2, 2, -1]) cube([46, 26, 8]);
}
