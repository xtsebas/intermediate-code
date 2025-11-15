function double(n: integer): integer {
  return n + n;
}

function mainValue(): integer {
  let base: integer = 7;
  return base;
}

let value: integer = double(3);
print("double(3) = " + value);

let baseValue: integer = mainValue();
print("mainValue returned: " + baseValue);