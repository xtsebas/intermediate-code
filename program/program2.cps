function triple(n: integer): integer {
  let doubled: integer = n + n;
  let tripled: integer = doubled + n;
  return tripled;
}

function computeValues(x: integer): integer {
  let first: integer = x + x;
  let second: integer = first + 5;
  let third: integer = second + x;
  return third;
}

let tripleValue: integer = triple(10);
print("triple(10) = " + tripleValue);

let computed: integer = computeValues(7);
print("computeValues(7) = " + computed);

if (tripleValue > computed) {
  print("triple is larger");
} else {
  print("computeValues is larger");
}

let counter: integer = 0;
while (counter < 3) {
  print("counter = " + counter);
  counter = counter + 1;
}

do {
  print("do-while counter = " + counter);
  counter = counter + 1;
} while (counter < 5);

for (let i: integer = 0; i < 2; i = i + 1) {
  print("for loop i = " + i);
}

let numbers: integer[] = [1, 2, 3];
foreach (n in numbers) {
  print("foreach n = " + n);
}
