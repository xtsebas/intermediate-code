// Program 3: exhaustive feature tests for the new backend

// ----- Globals -----
const LIMIT: integer = 42;
let greeting: string = "Welcome to Program3";
let numbers: integer[] = [1, 2, 3, 4, 5, 6];
let matrix: integer[][] = [[1, 2, 3], [4, 5, 6]];
let flips: boolean = true;

// ----- Functions -----
function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

function fibonacci(n: integer): integer {
  if (n <= 1) {
    return n;
  }
  return fibonacci(n - 1) + fibonacci(n - 2);
}

function sumNumbers(): integer {
  let total: integer = 0;
  foreach (item in numbers) {
    total = total + item;
  }
  return total;
}

function buildSeries(size: integer): integer[] {
  if (size <= 3) {
    let seriesShort: integer[] = [7, 14, 21, 0, 0];
    return seriesShort;
  }
  let seriesFull: integer[] = [7, 14, 21, 28, 35];
  return seriesFull;
}

// ----- Classes -----
class Counter {
  let value: integer;

  function constructor(start: integer) {
    this.value = start;
  }

  function tick(): integer {
    this.value = this.value + 1;
    return this.value;
  }

  function current(): integer {
    return this.value;
  }

  function label(): string {
    return "BaseCounter";
  }
}

class FancyCounter : Counter {
  function tick(): integer {
    this.value = this.value + 2;
    return this.value;
  }

  function label(): string {
    return "FancyCounter";
  }

  function flair(): string {
    return "Fancy ready";
  }
}

// ----- Main script -----
print(greeting + ", LIMIT = " + LIMIT);

let factSix: integer = factorial(6);
print("factorial(6) = " + factSix);

let fibSeven: integer = fibonacci(7);
print("fibonacci(7) = " + fibSeven);

// While & do-while combo exercising continue/break
let probe: integer = 0;
while (probe < 6) {
  probe = probe + 1;
  if (probe == 2) {
    continue;
  }
  if (probe > 4) {
    break;
  }
  print("While probe = " + probe);
}

do {
  print("Do-while probe = " + probe);
  probe = probe - 1;
} while (probe > 1);

// For loop
for (let i: integer = 0; i < 4; i = i + 1) {
  print("For index = " + i);
}

// Foreach with break/continue
let foreachSum: integer = 0;
foreach (value in numbers) {
  if (value == 3) {
    continue;
  }
  foreachSum = foreachSum + value;
  print("Foreach value = " + value);
  if (foreachSum > 12) {
    break;
  }
}

print("Foreach sum = " + foreachSum);

// Switch cases
switch (foreachSum) {
  case 6:
    print("Sum is six");
  case 15:
    print("Sum reached fifteen");
  default:
    print("Sum default hit");
}

// Try / Catch with bounds error
try {
  let risky: integer = numbers[10];
  print("Risky value = " + risky);
} catch (err) {
  print("Caught error message: " + err);
}

// Matrix indexing
let firstRow: integer = matrix[0][0];
let lastRow: integer = matrix[1][2];
print("Matrix corners: " + firstRow + " & " + lastRow);

// Arrays returned from functions
let series: integer[] = buildSeries(5);
print("Series[0] = " + series[0]);
print("Series[4] = " + series[4]);

// Classes & polymorphism
let baseCounter: Counter = new Counter(5);
let fancy: FancyCounter = new FancyCounter(10);
print("Base label: " + baseCounter.label());
print("Base tick value = " + baseCounter.tick());
print("Fancy label: " + fancy.label());
print("Fancy tick value = " + fancy.tick());
baseCounter.value = 99;
print("Updated base current = " + baseCounter.current());
let poly: Counter = fancy;
print("Poly label: " + poly.label());
print("Fancy flair: " + fancy.flair());

// Sum test
let numbersSum: integer = sumNumbers();
print("numbers sum = " + numbersSum);

// Final message
print("Program3 finished.");
