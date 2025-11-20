// Feature test: try / catch
let data: integer[] = [1, 2, 3];

try {
  let value: integer = data[5];
  print("TryCatch -> value=" + value);
} catch (err) {
  print("TryCatch -> caught=" + err);
}
