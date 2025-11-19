const PI: integer = 314;
let greeting: string = "Testing typed strings";
let inferredGreeting = "Inferred hello";
let featureFlag: boolean = true;

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

function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

let tripleValue: integer = triple(10);
print("triple(10) = " + tripleValue);
print("PI value = " + PI);
print(greeting + " / " + inferredGreeting);
if (featureFlag) {
  print("Feature flag is enabled");
}

let computed: integer = computeValues(7);
print("computeValues(7) = " + computed);
let factResult: integer = factorial(5);
print("factorial(5) = " + factResult);

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

switch (counter) {
  case 5:
    print("counter is five");
  case 6:
    print("counter is six");
  default:
    print("counter is something else");
}

class Animal {
  let name: string;

  function constructor(name: string) {
    this.name = name;
  }

  function speak(): string {
    return this.name + " makes a sound.";
  }
}

class Dog : Animal {
  function speak(): string {
    return this.name + " barks.";
  }
}

let dog: Dog = new Dog("Rex");
print("Dog says: " + dog.speak());
dog.name = "Buddy";
print("Dog renamed: " + dog.speak());

let baseAnimal: Animal = new Animal("Milo");
print("Animal says: " + baseAnimal.speak());

let poly: Animal = dog;
print("Polymorphic call: " + poly.speak());

function getMultiples(n: integer): integer[] {
  let result: integer[] = [n * 1, n * 2, n * 3];
  return result;
}

let first: integer = numbers[0];
let multiples: integer[] = getMultiples(4);
print("First: " + first);
print("Second multiple: " + multiples[1]);

foreach (value in numbers) {
  print("Foreach new -> " + value);
}
