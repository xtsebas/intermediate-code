// Feature test: variable declaration and assignment
const LIMIT: integer = 100;
let alpha: integer = 5;
let beta: integer;
let message: string = "DeclAssign";
let flag: boolean = true;

beta = alpha * 3;
alpha = beta + LIMIT / 10;

print(message + " -> alpha=" + alpha + ", beta=" + beta);
if (flag) {
  print("DeclAssign -> flag true");
}
