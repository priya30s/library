/* Library Management System - front-end logic.
   Every page calls the Flask JSON API with fetch(); nothing here is fake data. */
const $ = (sel, root = document) => root.querySelector(sel);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const money = n => "₹" + Number(n || 0).toFixed(2);
const role = document.body.dataset.role;
let reload = () => {};          // each page sets this to "refresh my data"

/* ---------- helpers ---------- */
async function api(url, method = "GET", body) {
  const res = await fetch(url, {method, headers: {"Content-Type": "application/json"},
                                body: body ? JSON.stringify(body) : undefined});
  if (res.status === 401 && url !== "/api/login") { location = "/login"; return; }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}
function toast(msg, type = "success") {
  const t = document.createElement("div");
  t.className = "toast " + type; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 4000);
}
async function safe(fn) { try { return await fn(); } catch (e) { toast(e.message, "error"); } }
const badge = (text, cls) => `<span class="badge ${cls}">${esc(text)}</span>`;
const card = (label, value) => `<div class="stat"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
function table(headers, rows) {   // cells are HTML strings (escape user text with esc())
  const head = headers.map(h => `<th>${esc(h)}</th>`).join("");
  const body = rows.length
    ? rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("")
    : `<tr><td colspan="${headers.length}" class="empty">No records found</td></tr>`;
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
function availBadge(b) {
  if (b.available_copies <= 0) return badge("Unavailable", "red");
  if (b.available_copies <= 2) return badge(`Low: ${b.available_copies}/${b.total_copies}`, "amber");
  return badge(`Available: ${b.available_copies}/${b.total_copies}`, "green");
}
const STATUS = {issued: "Issued", return_requested: "Return requested", returned: "Returned"};
function statusBadge(r) {
  const cls = r.status === "returned" ? "green" : r.status === "issued" ? "blue" : "amber";
  return badge(STATUS[r.status], cls) + (r.is_overdue ? badge("Overdue", "red") : "");
}
const btn = (act, id, text, cls = "") => `<button class="btn small ${cls}" data-act="${act}" data-id="${id}">${text}</button>`;

/* ---------- button actions (one click listener for the whole page) ---------- */
const actions = {
  borrow: async id => {
    if (!confirm("Borrow this book?")) return;
    const r = await api("/api/student/borrow", "POST", {book_id: id});
    toast(`Borrowed "${r.title}". Due on ${r.due_date}`); reload();
  },
  "delete-book": async id => {
    if (!confirm("Delete this book permanently?")) return;
    await api("/api/books/" + id, "DELETE"); toast("Book deleted"); reload();
  },
  return: async id => {
    if (!confirm("Request to return this book?")) return;
    const r = await api("/api/student/return/" + id, "POST"); toast(r.message); reload();
  },
  accept: async id => {
    if (!confirm("Accept this returned book?")) return;
    const r = await api("/api/librarian/return/" + id, "POST"); toast(r.message); reload();
  },
  pay: async id => {
    if (!confirm("Mark this fine as paid?")) return;
    await api(`/api/librarian/fines/${id}/pay`, "POST"); toast("Fine marked as paid"); reload();
  },
};
document.addEventListener("click", e => {
  const el = e.target.closest("[data-act]");
  if (el && actions[el.dataset.act]) safe(() => actions[el.dataset.act](el.dataset.id, el));
});
$("#menu-btn")?.addEventListener("click", () => $("#sidebar").classList.toggle("open"));

/* ---------- pages ---------- */
const pages = {};

pages.login = () => {
  $("#login-form").addEventListener("submit", e => {
    e.preventDefault();
    safe(async () => {
      const r = await api("/api/login", "POST", Object.fromEntries(new FormData(e.target)));
      location = r.redirect;
    });
  });
};

// dashboards and reports: the API returns {cards:[...], tables:[...]}
function dashboardPage(url) {
  reload = async () => {
    const d = await api(url);
    $("#cards").innerHTML = d.cards.map(c => card(c.label, c.value)).join("");
    $("#tables").innerHTML = d.tables.map(t =>
      `<section class="panel"><h3>${esc(t.title)}</h3>${table(t.headers, t.rows.map(r => r.map(esc)))}</section>`).join("");
  };
  reload();
}
pages.student_dashboard = () => dashboardPage("/api/student/dashboard");
pages.librarian_dashboard = () => dashboardPage("/api/librarian/dashboard");
pages.admin_dashboard = () => dashboardPage("/api/admin/dashboard");
pages.reports = () => dashboardPage("/api/librarian/reports");

pages.books = async () => {
  const cats = await api("/api/categories");
  $("#category").innerHTML = `<option value="">All categories</option>` +
    cats.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
  reload = async () => {
    const p = new URLSearchParams({q: $("#q").value, category: $("#category").value, available: $("#available").checked ? 1 : 0});
    const books = await api("/api/books?" + p);
    $("#book-list").innerHTML = table(["Title", "Author", "ISBN", "Category", "Availability", "Actions"],
      books.map(b => [`<a href="/books/${b.id}">${esc(b.title)}</a>`, esc(b.author), esc(b.isbn), esc(b.category || "-"), availBadge(b),
        role === "student"
          ? btn("borrow", b.id, "Borrow") .replace("<button", b.available_copies <= 0 ? "<button disabled" : "<button")
          : `<a class="btn small secondary" href="/books/${b.id}/edit">Edit</a> ` + btn("delete-book", b.id, "Delete", "danger")]));
  };
  let timer;
  $("#q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => safe(reload), 250); });
  $("#category").addEventListener("change", () => safe(reload));
  $("#available").addEventListener("change", () => safe(reload));
  reload();
};

pages.book_details = () => {
  reload = async () => {
    const b = await api("/api/books/" + document.body.dataset.id);
    $("#book-detail").innerHTML = `<h2>${esc(b.title)}</h2><p class="muted">by ${esc(b.author)}</p>
      <dl class="details"><dt>ISBN</dt><dd>${esc(b.isbn)}</dd><dt>Category</dt><dd>${esc(b.category || "-")}</dd>
      <dt>Publisher</dt><dd>${esc(b.publisher || "-")}</dd><dt>Year</dt><dd>${esc(b.publish_year || "-")}</dd>
      <dt>Description</dt><dd>${esc(b.description || "-")}</dd><dt>Availability</dt><dd>${availBadge(b)}</dd></dl>
      ${role === "student"
        ? `<button class="btn" data-act="borrow" data-id="${b.id}" ${b.available_copies <= 0 ? "disabled" : ""}>Borrow this book</button>`
        : `<a class="btn" href="/books/${b.id}/edit">Edit book</a>`}`;
  };
  reload();
};

async function bookForm(editing) {
  const f = $("#book-form"), id = document.body.dataset.id;
  const cats = await api("/api/categories");
  $("#category").innerHTML = `<option value="">-- none --</option>` +
    cats.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
  if (editing) {
    const b = await api("/api/books/" + id);
    for (const k of Object.keys(b)) if (f.elements[k]) f.elements[k].value = b[k] ?? "";
  }
  f.addEventListener("submit", e => {
    e.preventDefault();
    safe(async () => {
      const d = Object.fromEntries(new FormData(f));
      if (editing) await api("/api/books/" + id, "PUT", d); else await api("/api/books", "POST", d);
      toast("Book saved"); setTimeout(() => location = "/books", 700);
    });
  });
}
pages.add_book = () => bookForm(false);
pages.edit_book = () => bookForm(true);

pages.borrowed_books = () => {
  if (role === "student") {
    reload = async () => {
      const rows = await api("/api/student/borrowings");
      $("#borrow-list").innerHTML = table(["Book", "Issued", "Due", "Returned", "Status", "Fine", "Action"],
        rows.map(r => [esc(r.title), r.issue_date, r.due_date, r.return_date || "-", statusBadge(r), money(r.fine),
          r.status === "issued" ? btn("return", r.id, "Return") : r.status === "return_requested" ? "Waiting for librarian" : "-"]));
    };
  } else {
    reload = async () => {
      const books = await api("/api/books?available=1");
      $("#issue-book").innerHTML = books.map(b => `<option value="${b.id}">${esc(b.title)} (${b.available_copies} left)</option>`).join("");
      const rows = await api("/api/librarian/borrowings?status=" + $("#status-filter").value);
      $("#borrow-list").innerHTML = table(["Student", "Book", "Issued", "Due", "Status", "Fine", "Action"],
        rows.map(r => [`${esc(r.student_name)}<br><small class="muted">${esc(r.roll_no)}</small>`, esc(r.title),
          r.issue_date, r.due_date, statusBadge(r), money(r.fine),
          r.status !== "returned" ? btn("accept", r.id, "Accept return") : "-"]));
    };
    $("#status-filter").addEventListener("change", () => safe(reload));
    $("#issue-form").addEventListener("submit", e => {
      e.preventDefault();
      safe(async () => {
        const r = await api("/api/librarian/issue", "POST", Object.fromEntries(new FormData(e.target)));
        toast(r.message); e.target.reset(); reload();
      });
    });
  }
  reload();
};

// students and librarians share one add/edit/delete screen
function accountsPage(base, extra) {
  const form = $("#acct-form"); let cache = [];
  const clear = () => { form.reset(); form.username.readOnly = false; form.password.required = true; };
  reload = async () => {
    cache = await api(base);
    $("#acct-list").innerHTML = table(["Name", "Username", "Email", "Phone", ...extra.map(x => x[1]), "Status", "Actions"],
      cache.map(a => [esc(a.full_name), esc(a.username), esc(a.email), esc(a.phone || "-"),
        ...extra.map(x => esc(a[x[0]] || "-")), badge(a.is_active ? "Active" : "Disabled", a.is_active ? "green" : "red"),
        btn("acct-edit", a.id, "Edit") + " " + btn("acct-del", a.id, "Delete", "danger")]));
  };
  actions["acct-edit"] = id => {
    const a = cache.find(x => x.id == id);
    for (const [k, v] of Object.entries(a)) if (form.elements[k]) form.elements[k].value = v ?? "";
    form.elements.pid.value = a.id; form.username.readOnly = true; form.password.required = false; form.password.value = "";
    scrollTo(0, 0);
  };
  actions["acct-del"] = async id => {
    if (!confirm("Delete this account permanently?")) return;
    await api(`${base}/${id}`, "DELETE"); toast("Deleted"); reload();
  };
  form.addEventListener("submit", e => {
    e.preventDefault();
    safe(async () => {
      const d = Object.fromEntries(new FormData(form)); const pid = d.pid; delete d.pid;
      if (pid) await api(`${base}/${pid}`, "PUT", d); else await api(base, "POST", d);
      toast("Saved"); clear(); reload();
    });
  });
  $("#acct-reset").addEventListener("click", clear);
  reload();
}
pages.students = () => accountsPage("/api/librarian/students", [["roll_no", "Roll no"], ["department", "Department"]]);
pages.librarians = () => accountsPage("/api/admin/librarians", [["employee_id", "Employee ID"]]);

pages.categories = () => {
  let cache = [];
  reload = async () => {
    cache = await api("/api/categories");
    $("#cat-list").innerHTML = table(["Name", "Description", "Books", "Actions"],
      cache.map(c => [esc(c.name), esc(c.description || "-"), c.book_count,
        btn("cat-edit", c.id, "Rename") + " " + btn("cat-del", c.id, "Delete", "danger")]));
  };
  actions["cat-edit"] = async id => {
    const c = cache.find(x => x.id == id), name = prompt("New category name:", c.name);
    if (!name) return;
    await api("/api/admin/categories/" + id, "PUT", {name, description: c.description}); toast("Updated"); reload();
  };
  actions["cat-del"] = async id => {
    if (!confirm("Delete this category? Its books will become uncategorised.")) return;
    await api("/api/admin/categories/" + id, "DELETE"); toast("Deleted"); reload();
  };
  $("#cat-form").addEventListener("submit", e => {
    e.preventDefault();
    safe(async () => { await api("/api/admin/categories", "POST", Object.fromEntries(new FormData(e.target))); toast("Category added"); e.target.reset(); reload(); });
  });
  reload();
};

pages.users = () => {
  reload = async () => {
    const rows = await api("/api/admin/users");
    $("#user-list").innerHTML = table(["Name", "Username", "Email", "Role", "Status", "Action"],
      rows.map(u => [esc(u.full_name), esc(u.username), esc(u.email), badge(u.role, "blue"),
        badge(u.is_active ? "Active" : "Disabled", u.is_active ? "green" : "red"),
        btn("toggle-user", u.id, u.is_active ? "Disable" : "Enable", u.is_active ? "danger" : "")]));
  };
  actions["toggle-user"] = async id => {
    if (!confirm("Change this user's access?")) return;
    await api(`/api/admin/users/${id}/toggle`, "PUT"); toast("User updated"); reload();
  };
  reload();
};

pages.fines = () => {
  const staff = role !== "student";
  reload = async () => {
    const d = await api(staff ? "/api/librarian/fines" : "/api/student/fines");
    $("#cards").innerHTML = card("Outstanding fines", money(d.outstanding)) + card("Fine per overdue day", money(d.fine_per_day));
    const stateCls = {Paid: "green", Unpaid: "red", Accruing: "amber"};
    $("#fine-list").innerHTML = table(["Book", ...(staff ? ["Student"] : []), "Days overdue", "Fine", "Status", ...(staff ? ["Action"] : [])],
      d.rows.map(r => [esc(r.title), ...(staff ? [`${esc(r.student)} <small class="muted">${esc(r.roll_no)}</small>`] : []),
        r.days, money(r.amount), badge(r.state === "Accruing" ? "Accruing (book not returned)" : r.state, stateCls[r.state]),
        ...(staff ? [r.state === "Unpaid" ? btn("pay", r.id, "Mark paid") : "-"] : [])]));
  };
  reload();
};

pages.profile = () => {
  reload = async () => {
    const u = await api("/api/me"), f = $("#profile-form");
    for (const k of ["full_name", "email", "phone"]) f.elements[k].value = u[k] || "";
    const extra = [["roll_no", "Roll no"], ["department", "Department"], ["employee_id", "Employee ID"]]
      .filter(x => u[x[0]]).map(x => `<dt>${x[1]}</dt><dd>${esc(u[x[0]])}</dd>`).join("");
    $("#profile-info").innerHTML = `<h3>${esc(u.full_name)}</h3><dl class="details"><dt>Username</dt><dd>${esc(u.username)}</dd>
      <dt>Role</dt><dd>${esc(u.role)}</dd>${extra}<dt>Member since</dt><dd>${esc(String(u.created_at).slice(0, 10))}</dd></dl>`;
  };
  $("#profile-form").addEventListener("submit", e => {
    e.preventDefault();
    safe(async () => { await api("/api/me", "PUT", Object.fromEntries(new FormData(e.target))); toast("Profile updated"); reload(); });
  });
  $("#password-form").addEventListener("submit", e => {
    e.preventDefault();
    safe(async () => { await api("/api/me/password", "POST", Object.fromEntries(new FormData(e.target))); toast("Password changed"); e.target.reset(); });
  });
  reload();
};

/* ---------- start the script for the current page ---------- */
const start = pages[document.body.dataset.page];
if (start) safe(start);
