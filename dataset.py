# dataset.py
import random
import csv
import sys

def gen_name():
    first = random.choice(["Amit","Kavish","Vaidehi","Kriti","Agnijeet","Akanksha","Sanjay","Rina","Tara","Rohit"])
    last = random.choice(["Sharma","Raina","Kamble","Paraswar","Patel","Khatri","Jain","Desai"])
    return f"{first} {last}"

def generate_csv(path="employees_10k.csv", n=10000):
    depts = ["HR","Engineering","Sales","Marketing","Finance","Support"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["emp_id","name","age","department","salary"])
        for i in range(1, n+1):
            name = gen_name()
            age = random.randint(18, 65)
            dept = random.choice(depts)
            salary = round(random.uniform(20000, 200000), 2)
            w.writerow([i, name, age, dept, salary])
    print("Wrote", n, "rows to", path)
    return path

if __name__ == "__main__":
    # Usage: python dataset.py [path] [n]
    path = "employees_10k.csv"
    n = 10000
    if len(sys.argv) >= 2:
        path = sys.argv[1]
    if len(sys.argv) >= 3:
        try:
            n = int(sys.argv[2])
        except Exception:
            pass
    generate_csv(path=path, n=n)
