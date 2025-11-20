// Feature test: inheritance
class Animal {
  let name: string;

  function constructor(name: string) {
    this.name = name;
  }

  function speak(): string {
    return this.name + " generic";
  }
}

class Dog : Animal {
  function speak(): string {
    return this.name + " barks";
  }
}

let dog: Dog = new Dog("Spot");
let poly: Animal = dog;
print("Inheritance -> " + dog.speak());
print("Inheritance poly -> " + poly.speak());
