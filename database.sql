-- Library Management System (SQLite). The app runs this file automatically
-- the first time it starts. To reset all data, delete library.db and restart.
PRAGMA foreign_keys = ON;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  phone TEXT,
  role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student','librarian','admin')),
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_role ON users(role);

CREATE TABLE students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  roll_no TEXT NOT NULL UNIQUE,
  department TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE librarians (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  employee_id TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  isbn TEXT NOT NULL UNIQUE,
  category_id INTEGER,
  publisher TEXT,
  publish_year INTEGER,
  description TEXT,
  total_copies INTEGER NOT NULL DEFAULT 1,
  available_copies INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
  CHECK (available_copies >= 0 AND available_copies <= total_copies)
);
CREATE INDEX idx_books_title ON books(title);
CREATE INDEX idx_books_author ON books(author);

CREATE TABLE borrowings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL,
  student_id INTEGER NOT NULL,
  issued_by INTEGER,
  issue_date DATE NOT NULL,
  due_date DATE NOT NULL,
  return_date DATE,
  status TEXT NOT NULL DEFAULT 'issued' CHECK (status IN ('issued','return_requested','returned')),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT,
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE RESTRICT,
  FOREIGN KEY (issued_by) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX idx_borrow_status ON borrowings(status);
CREATE INDEX idx_borrow_due ON borrowings(due_date);

CREATE TABLE `returns` (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  borrowing_id INTEGER NOT NULL UNIQUE,
  returned_on DATE NOT NULL,
  received_by INTEGER,
  fine_amount REAL NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (borrowing_id) REFERENCES borrowings(id) ON DELETE CASCADE,
  FOREIGN KEY (received_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE fines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  borrowing_id INTEGER NOT NULL UNIQUE,
  student_id INTEGER NOT NULL,
  days_overdue INTEGER NOT NULL,
  amount REAL NOT NULL,
  paid INTEGER NOT NULL DEFAULT 0,
  paid_on DATETIME,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (borrowing_id) REFERENCES borrowings(id) ON DELETE CASCADE,
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
CREATE INDEX idx_fines_paid ON fines(paid);

-- ---------- sample data (passwords: admin123 / lib123 / student123) ----------
INSERT INTO users (id, username, email, password_hash, full_name, phone, role) VALUES
(1, 'admin',     'admin@library.edu',     'pbkdf2:sha256:600000$1ca7700a5c152ccb$a2ce1a8f50af95a17923a2b3058edbd8c4e141e6506790956b85ce9e67baf476', 'System Admin',  '9000000001', 'admin'),
(2, 'librarian', 'librarian@library.edu', 'pbkdf2:sha256:600000$b2bbbe14f9267fc5$883ce6eccb0bc4227418f34941287e76dc2597436ec35759066118c59caf5722',   'Meena Iyer',    '9000000002', 'librarian'),
(3, 'student1',  'arun@college.edu',      'pbkdf2:sha256:600000$a6870908aa36e484$a89949a8894e9b0957ced6ec88cf647dcf450c050eb1b16b192285efad1a59aa',   'Arun Kumar',    '9000000003', 'student'),
(4, 'student2',  'priya@college.edu',     'pbkdf2:sha256:600000$9b18848cda0b3172$7b2995c2937765a3e3dcc22ad43955699de5294887205128d27ee4ef7ce2e7b5',   'Priya Sharma',  '9000000004', 'student'),
(5, 'student3',  'karthik@college.edu',   'pbkdf2:sha256:600000$4fae2f6089f09e32$2cb86499d5fb4bc150d91c7505ff9e576864bd56fc65436ecd6895e754ed0592',   'Karthik Raj',   '9000000005', 'student');

INSERT INTO librarians (id, user_id, employee_id) VALUES (1, 2, 'LIB001');
INSERT INTO students (id, user_id, roll_no, department) VALUES
(1, 3, 'CS2024001', 'Computer Science'),
(2, 4, 'EC2024002', 'Electronics'),
(3, 5, 'ME2024003', 'Mechanical');

INSERT INTO categories (id, name, description) VALUES
(1, 'Computer Science', 'Programming, databases and systems'),
(2, 'Mathematics', 'Pure and applied mathematics'),
(3, 'Physics', 'Physics textbooks'),
(4, 'Literature', 'Novels, classics and biographies'),
(5, 'History', 'World and Indian history'),
(6, 'Business', 'Management and entrepreneurship'),
(7, 'Science Fiction', 'Sci-fi novels'),
(8, 'Self Help', 'Personal development');

INSERT INTO books (id, title, author, isbn, category_id, publisher, publish_year, description, total_copies, available_copies) VALUES
(1, 'Introduction to Algorithms', 'Thomas H. Cormen', '9780262046305', 1, 'MIT Press', 2022, 'Standard algorithms textbook.', 5, 4),
(2, 'Clean Code', 'Robert C. Martin', '9780132350884', 1, 'Prentice Hall', 2008, 'Writing readable, maintainable code.', 4, 3),
(3, 'Python Crash Course', 'Eric Matthes', '9781718502703', 1, 'No Starch Press', 2023, 'Hands-on introduction to Python.', 2, 1),
(4, 'Database System Concepts', 'Abraham Silberschatz', '9780078022159', 1, 'McGraw-Hill', 2019, 'Relational databases and SQL.', 4, 4),
(5, 'Operating System Concepts', 'Abraham Silberschatz', '9781119800361', 1, 'Wiley', 2021, 'Processes, memory and file systems.', 3, 3),
(6, 'Advanced Engineering Mathematics', 'Erwin Kreyszig', '9780470458365', 2, 'Wiley', 2010, 'Engineering maths reference.', 6, 6),
(7, 'Discrete Mathematics and Its Applications', 'Kenneth Rosen', '9781259676512', 2, 'McGraw-Hill', 2018, 'Logic, sets and graphs.', 4, 4),
(8, 'Physics for Scientists and Engineers', 'Raymond Serway', '9781337553278', 3, 'Cengage', 2018, 'Calculus-based physics.', 3, 3),
(9, 'Concepts of Physics', 'H. C. Verma', '9788177091878', 3, 'Bharati Bhawan', 1992, 'Popular physics for Indian students.', 5, 5),
(10, 'Wings of Fire', 'A. P. J. Abdul Kalam', '9788173711466', 4, 'Universities Press', 1999, 'Autobiography of Dr Kalam.', 4, 4),
(11, 'Pride and Prejudice', 'Jane Austen', '9780141439518', 4, 'Penguin', 2002, 'Classic English novel.', 3, 3),
(12, 'Sapiens', 'Yuval Noah Harari', '9780062316097', 5, 'Harper', 2015, 'A brief history of humankind.', 4, 4),
(13, 'India After Gandhi', 'Ramachandra Guha', '9780060958589', 5, 'Ecco', 2008, 'History of modern India.', 2, 2),
(14, 'Zero to One', 'Peter Thiel', '9780804139298', 6, 'Crown Business', 2014, 'Notes on startups.', 2, 1),
(15, 'Dune', 'Frank Herbert', '9780441172719', 7, 'Ace', 2005, 'Science fiction classic.', 2, 2),
(16, 'Atomic Habits', 'James Clear', '9780735211292', 8, 'Avery', 2018, 'Building good habits.', 4, 4);

-- active borrowings (books 3, 1, 14, 2 are currently out; stock above matches)
INSERT INTO borrowings (id, book_id, student_id, issued_by, issue_date, due_date, return_date, status) VALUES
(1, 3,  1, 2, date('now','localtime','-20 days'), date('now','localtime','-6 days'),  NULL, 'issued'),
(2, 1,  1, 2, date('now','localtime','-3 days'),  date('now','localtime','+11 days'), NULL, 'issued'),
(3, 14, 2, 2, date('now','localtime','-12 days'), date('now','localtime','+2 days'),  NULL, 'issued'),
(4, 2,  3, 2, date('now','localtime','-10 days'), date('now','localtime','+4 days'),  NULL, 'return_requested'),
(5, 12, 2, 2, date('now','localtime','-30 days'), date('now','localtime','-16 days'), date('now','localtime','-10 days'), 'returned'),
(6, 10, 3, 2, date('now','localtime','-25 days'), date('now','localtime','-11 days'), date('now','localtime','-15 days'), 'returned'),
(7, 16, 1, 2, date('now','localtime','-40 days'), date('now','localtime','-26 days'), date('now','localtime','-20 days'), 'returned');

INSERT INTO `returns` (borrowing_id, returned_on, received_by, fine_amount) VALUES
(5, date('now','localtime','-10 days'), 2, 30.00),
(6, date('now','localtime','-15 days'), 2, 0.00),
(7, date('now','localtime','-20 days'), 2, 30.00);

INSERT INTO fines (borrowing_id, student_id, days_overdue, amount, paid, paid_on) VALUES
(5, 2, 6, 30.00, 0, NULL),
(7, 1, 6, 30.00, 1, datetime('now','localtime'));
