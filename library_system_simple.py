"""
Simple Library System (OOP + CSV + try/except)
------------------------------------------------
Classes   : Book, Library
Features  : multiple libraries, multiple copies of a book, borrow, return,
            save data to a CSV file, load data back from a CSV file.
No input() is used - all data is written directly in the code below.
"""

import csv


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


# ---------------- sample data (no input needed) ----------------

if __name__ == "__main__":
    b1 = Book("Python 101", "Alice", "111")
    b2 = Book("Data Structures", "Bob", "222")

    lib1 = Library("City Library")
    lib1.add_book(b1, copies=2)
    lib1.add_book(b2, copies=1)
    lib1.show_books()

    print("\n--- Borrowing ---")
    lib1.borrow_book("111", "Rahul")
    lib1.borrow_book("999", "Sneha")   # ISBN does not exist -> handled safely
    lib1.show_books()

    print("\n--- Saving and Loading CSV ---")
    lib1.save_to_csv("library.csv")

    lib2 = Library("New Library")
    lib2.load_from_csv("missing.csv")   # on purpose, to show error handling
    lib2.load_from_csv("library.csv")
    lib2.show_books()
