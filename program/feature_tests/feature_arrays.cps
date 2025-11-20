// Feature test: arrays and matrices
let numbers: integer[] = [1, 2, 3, 4];
let matrix: integer[][] = [[1, 2], [3, 4]];

let acc: integer = 0;
foreach (value in numbers) {
  acc = acc + value;
}

let first: integer = numbers[0];
let last: integer = numbers[3];
let corner: integer = matrix[1][1];

print("Arrays -> first=" + first + ", last=" + last + ", corner=" + corner + ", sum=" + acc);
