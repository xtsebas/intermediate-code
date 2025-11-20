// Feature test: logical expressions
let a: integer = 10;
let b: integer = 20;
let c: integer = 5;

let cond1: boolean = a < b;
let cond2: boolean = b == 20;
if (cond1) {
  if (cond2) {
    print("Logic -> branch1");
  }
}

let cond3: boolean = a > b;
let cond4: boolean = c <= 5;
if (cond3) {
  print("Logic -> branch2-or-left");
} else {
  if (cond4) {
    print("Logic -> branch2-or-right");
  }
}

let flag: boolean = (a != c);
if (flag) {
  if (b > a) {
    print("Logic -> flag true");
  }
}
