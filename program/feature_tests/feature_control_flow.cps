// Feature test: control statements
let x: integer = 0;
while (x < 3) {
  print("Control -> while=" + x);
  x = x + 1;
}

do {
  x = x - 1;
  print("Control -> doWhile=" + x);
} while (x > 0);

for (let i: integer = 0; i < 2; i = i + 1) {
  if (i == 1) {
    print("Control -> if/else branch B");
  } else {
    print("Control -> if/else branch A");
  }
}

let tempArr: integer[] = [1, 2, 3];
let total: integer = 0;
foreach (value in tempArr) {
  total = total + value;
}

switch (total) {
  case 6:
    print("Control -> switch total 6");
  default:
    print("Control -> switch default");
}
