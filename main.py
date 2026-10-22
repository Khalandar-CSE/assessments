import csv
import os
import re
import threading
import time

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ===================== LIBRARY CODE =====================
class Book:
    def __init__(self, title, author, isbn):
        self.title = title
        self.author = author
        self.isbn = isbn

    def __str__(self):
        return f"{self.title} by {self.author} (ISBN: {self.isbn})"


class Library:
    def __init__(self, name):
        self.name = name
        self.books = {}      # isbn -> total copies
        self.borrowed = {}   # isbn -> list of borrower names

    def add_book(self, book, copies=1):
        self.books[book.isbn] = self.books.get(book.isbn, 0) + copies
        self.borrowed.setdefault(book.isbn, [])
        print(f"[{self.name}] Added {copies} copy of {book.title}")

    def show_books(self):
        print(f"\nBooks in {self.name}:")
        for isbn, total in self.books.items():
            available = total - len(self.borrowed[isbn])
            print(f"  ISBN {isbn}: total={total}, available={available}")

    def borrow_book(self, isbn, borrower):
        try:
            if isbn not in self.books:
                print("This book is not in the library.")
                return
            if len(self.borrowed[isbn]) >= self.books[isbn]:
                print("No copies available right now.")
                return
            self.borrowed[isbn].append(borrower)
            print(f"{borrower} borrowed ISBN {isbn}")
        except Exception as e:
            print("Something went wrong while borrowing:", e)

    def return_book(self, isbn, borrower):
        try:
            self.borrowed[isbn].remove(borrower)
            print(f"{borrower} returned ISBN {isbn}")
        except Exception as e:
            print("Something went wrong while returning:", e)

    def save_to_csv(self, filename):
        try:
            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["isbn", "total_copies", "borrowed_by"])
                for isbn, total in self.books.items():
                    borrowed_names = ";".join(self.borrowed[isbn])
                    writer.writerow([isbn, total, borrowed_names])
            print(f"Saved to {filename}")
        except Exception as e:
            print("Could not save file:", e)

    def load_from_csv(self, filename):
        try:
            with open(filename, "r") as f:
                reader = csv.reader(f)
                next(reader)  # skip the header row
                for row in reader:
                    isbn, total, borrowed_names = row
                    self.books[isbn] = int(total)
                    self.borrowed[isbn] = borrowed_names.split(";") if borrowed_names else []
            print(f"Loaded from {filename}")
        except FileNotFoundError:
            print(f"File {filename} does not exist.")
        except Exception as e:
            print("Could not load file:", e)


# ===================== API =====================
app = FastAPI(title="Students + Library API")

# ---------- students ----------
students = {
    1: {"name": "Anu", "course": "Python"},
    2: {"name": "Rahul", "course": "Java"},
}


class Student(BaseModel):
    id: int
    name: str
    course: str


@app.get("/students/{student_id}")
def get_student(student_id: int):
    if student_id not in students:
        raise HTTPException(status_code=404, detail="Student not found")
    return students[student_id]


@app.get("/students")
def get_students():
    return students


@app.post("/students")
def add_student(student: Student):
    if student.id in students:
        raise HTTPException(status_code=400, detail="Student ID already exists")
    students[student.id] = {"name": student.name, "course": student.course}
    return student


# ---------- library ----------
libraries = {}   # library name -> Library object
catalog = {}     # isbn -> Book

_city = Library("City Library")
for _b, _copies in [(Book("Python 101", "Alice", "111"), 2),
                    (Book("Data Structures", "Bob", "222"), 1)]:
    catalog[_b.isbn] = _b
    _city.add_book(_b, copies=_copies)
libraries[_city.name] = _city


class LibraryIn(BaseModel):
    name: str


class BookIn(BaseModel):
    title: str
    author: str
    isbn: str
    copies: int = 1


class BorrowIn(BaseModel):
    isbn: str
    borrower: str


def find_library(name: str) -> Library:
    if name not in libraries:
        raise HTTPException(status_code=404, detail="Library not found")
    return libraries[name]


def csv_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", name) + ".csv"


@app.get("/libraries")
def get_libraries():
    return list(libraries.keys())


@app.post("/libraries")
def create_library(data: LibraryIn):
    if data.name in libraries:
        raise HTTPException(status_code=400, detail="Library already exists")
    libraries[data.name] = Library(data.name)
    return {"message": f"Library '{data.name}' created"}


@app.get("/libraries/{name}/books")
def get_books(name: str):
    lib = find_library(name)
    result = []
    for isbn, total in lib.books.items():
        book = catalog.get(isbn)
        result.append({
            "isbn": isbn,
            "title": book.title if book else None,
            "author": book.author if book else None,
            "total": total,
            "available": total - len(lib.borrowed[isbn]),
            "borrowed_by": lib.borrowed[isbn],
        })
    return result


@app.post("/libraries/{name}/books")
def add_book(name: str, data: BookIn):
    lib = find_library(name)
    if data.copies < 1:
        raise HTTPException(status_code=400, detail="copies must be at least 1")
    book = Book(data.title, data.author, data.isbn)
    catalog[book.isbn] = book
    lib.add_book(book, copies=data.copies)
    return {"message": f"Added {data.copies} copy of {data.title}"}


@app.post("/libraries/{name}/borrow")
def borrow_book(name: str, data: BorrowIn):
    lib = find_library(name)
    if data.isbn not in lib.books:
        raise HTTPException(status_code=404, detail="This book is not in the library")
    if len(lib.borrowed[data.isbn]) >= lib.books[data.isbn]:
        raise HTTPException(status_code=400, detail="No copies available right now")
    lib.borrow_book(data.isbn, data.borrower)
    return {"message": f"{data.borrower} borrowed ISBN {data.isbn}"}


@app.post("/libraries/{name}/return")
def return_book(name: str, data: BorrowIn):
    lib = find_library(name)
    if data.isbn not in lib.books or data.borrower not in lib.borrowed[data.isbn]:
        raise HTTPException(status_code=400, detail="This borrower does not have this book")
    lib.return_book(data.isbn, data.borrower)
    return {"message": f"{data.borrower} returned ISBN {data.isbn}"}


@app.post("/libraries/{name}/save")
def save_library(name: str):
    lib = find_library(name)
    filename = csv_name(name)
    lib.save_to_csv(filename)
    return {"message": f"Saved to {filename}"}


@app.post("/libraries/{name}/load")
def load_library(name: str):
    lib = find_library(name)
    filename = csv_name(name)
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail=f"{filename} does not exist")
    lib.load_from_csv(filename)
    return {"message": f"Loaded from {filename}"}


# ===================== CLIENT CODE =====================
BASE = "http://127.0.0.1:8000"


def show(title, r):
    print(f"{title}: {r.status_code} {r.json()}")


def run_client():
    LIB = "City Library"

    print("\n===== STUDENTS =====")
    show("All students", requests.get(f"{BASE}/students"))
    show("Student 1", requests.get(f"{BASE}/students/1"))
    show("Student 99", requests.get(f"{BASE}/students/99"))
    show("Add student", requests.post(f"{BASE}/students",
         json={"id": 3, "name": "Priya", "course": "C++"}))
    show("Duplicate student", requests.post(f"{BASE}/students",
         json={"id": 3, "name": "Priya", "course": "C++"}))

    print("\n===== LIBRARY =====")
    show("Libraries", requests.get(f"{BASE}/libraries"))
    show("Books", requests.get(f"{BASE}/libraries/{LIB}/books"))
    show("Add book", requests.post(f"{BASE}/libraries/{LIB}/books",
         json={"title": "Clean Code", "author": "Robert Martin", "isbn": "333", "copies": 2}))
    show("Borrow", requests.post(f"{BASE}/libraries/{LIB}/borrow",
         json={"isbn": "111", "borrower": "Rahul"}))
    show("Borrow unknown ISBN", requests.post(f"{BASE}/libraries/{LIB}/borrow",
         json={"isbn": "999", "borrower": "Sneha"}))
    show("Books after borrow", requests.get(f"{BASE}/libraries/{LIB}/books"))
    show("Return", requests.post(f"{BASE}/libraries/{LIB}/return",
         json={"isbn": "111", "borrower": "Rahul"}))
    show("Save CSV", requests.post(f"{BASE}/libraries/{LIB}/save"))
    show("Load CSV", requests.post(f"{BASE}/libraries/{LIB}/load"))
    show("New library", requests.post(f"{BASE}/libraries", json={"name": "New Library"}))
    show("Load missing CSV", requests.post(f"{BASE}/libraries/New Library/load"))


if __name__ == "__main__":
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.1)

    run_client()

    server.should_exit = True
    thread.join()