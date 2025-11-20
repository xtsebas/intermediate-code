// Feature test: classes and objects
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
}

let counter: Counter = new Counter(10);
print("Classes -> start=" + counter.current());
print("Classes -> tick result=" + counter.tick());
