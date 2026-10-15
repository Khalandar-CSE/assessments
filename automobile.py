class Automobile:
    def __init__(self, brand, speed):
        self.brand = brand
        self.speed = speed

    def accelerate(self):
        print(self.brand, "is accelerating")

    def brake(self):
        print(self.brand, "is braking")


class Car(Automobile):
    def __init__(self, brand, speed, model, owner):
        super().__init__(brand, speed)
        self.model = model
        self.owner = owner

    def display(self):
        print("Owner:", self.owner)
        print("Brand:", self.brand)
        print("Speed:", self.speed)
        print("Model:", self.model)


car = Car("Toyota", 120, "Innova", "Khalandar")

car.display()
car.accelerate()
car.brake()