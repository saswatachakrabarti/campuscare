"""
admin.py
--------
Admin Module (CampusCare)

Shows the administrator dashboard: summary cards, a filterable table of
all complaints, and a details panel where the admin can assign a
department and update the status (Pending -> In Progress -> Resolved).
Every status change is written to Complaint_History by
database.update_complaint_status().

How other files use this module:
    import admin
    admin.show_admin_dashboard(root, user, on_logout)

Run `python admin.py` to test this screen on its own.
"""

import tkinter as tk
from tkinter import ttk

import database
from login import (  # reuse the same colours/fonts so the app looks consistent
    PRIMARY, PRIMARY_DARK, PANEL, BG, WHITE, BORDER, TEXT, MUTED, ERROR,
    FONT, FONT_SMALL, FONT_LABEL, _make_field,
)

# ------------------------------------------------------------ settings ----
SUCCESS = "#16A34A"
WARNING = "#F59E0B"

STATUSES = ("Pending", "In Progress", "Resolved")
DEPARTMENTS = (
    "Unassigned", "Electrical", "Civil / Maintenance", "IT / Network",
    "Housekeeping", "Air Conditioning", "Hostel Administration",
)
DEFAULT_CATEGORIES = (
    "Classroom", "Laboratory", "Hostel", "Electrical",
    "Air Conditioning", "Furniture", "Cleanliness", "Internet",
)

# light row colours for each status in the table
STATUS_ROW_COLORS = {
    "Pending": "#FEF3C7",
    "In Progress": "#DBEAFE",
    "Resolved": "#DCFCE7",
}


# ------------------------------------------------------------ helpers ----
def _button(parent, text, command, bg=PRIMARY, hover=PRIMARY_DARK, fg=WHITE,
            font=("Segoe UI", 11, "bold"), pady=8, padx=0):
    """Flat coloured button (a Label, so colours work on every OS)."""
    b = tk.Label(parent, text=text, font=font, bg=bg, fg=fg,
                 cursor="hand2", pady=pady, padx=padx)
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>", lambda e: b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def _stat_card(parent, column, title, color):
    """Summary card with a coloured stripe. Returns the number label."""
    card = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 12, 0))
    tk.Frame(card, bg=color, width=6).pack(side="left", fill="y")
    body = tk.Frame(card, bg=WHITE)
    body.pack(side="left", padx=14, pady=8)
    number = tk.Label(body, text="0", font=("Segoe UI", 22, "bold"), bg=WHITE, fg=TEXT)
    number.pack(anchor="w")
    tk.Label(body, text=title, font=FONT_SMALL, bg=WHITE, fg=MUTED).pack(anchor="w")
    return number


def _set_text(widget, content):
    """Fill a read-only Text widget."""
    widget.config(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.config(state="disabled")


# ---------------------------------------------------------- main screen ----
def show_admin_dashboard(root, user, on_logout):
    """Clear the window and display the admin dashboard."""
    for widget in root.winfo_children():
        widget.destroy()
    root.configure(bg=BG)
    root.geometry("1200x720")
    root.minsize(1000, 620)

    state = {"selected_id": None}
    current_rows = {}  # complaint_id -> complaint dict (rows currently shown)

    # ---------- table / combobox styling ----------
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Treeview", background=WHITE, fieldbackground=WHITE,
                    foreground=TEXT, rowheight=32, font=("Segoe UI", 10),
                    borderwidth=0)
    style.configure("Treeview.Heading", background=PANEL, foreground=WHITE,
                    font=("Segoe UI", 10, "bold"), relief="flat", padding=(8, 8))
    style.map("Treeview.Heading", background=[("active", PRIMARY)])
    style.map("Treeview", background=[("selected", PRIMARY)],
              foreground=[("selected", WHITE)])
    style.configure("TCombobox", padding=6)

    # ---------- top bar ----------
    topbar = tk.Frame(root, bg=PANEL, height=60)
    topbar.pack(fill="x")
    topbar.pack_propagate(False)

    tk.Label(topbar, text="🏫  CampusCare", font=("Segoe UI", 16, "bold"),
             bg=PANEL, fg=WHITE).pack(side="left", padx=(20, 10))
    tk.Label(topbar, text="Admin Dashboard", font=FONT,
             bg=PANEL, fg="#BFDBFE").pack(side="left")

    logout_btn = _button(topbar, "Logout", on_logout, bg="#DC2626", hover="#B91C1C",
                         font=("Segoe UI", 10, "bold"), pady=6, padx=16)
    logout_btn.pack(side="right", padx=20)
    tk.Label(topbar, text=f"Logged in as {user['name']}", font=FONT,
             bg=PANEL, fg=WHITE).pack(side="right")

    # ---------- body ----------
    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True, padx=20, pady=14)

    # ---------- summary cards ----------
    stats_row = tk.Frame(body, bg=BG)
    stats_row.pack(fill="x")
    for col in range(4):
        stats_row.columnconfigure(col, weight=1, uniform="stat")
    total_lbl = _stat_card(stats_row, 0, "Total Complaints", PRIMARY)
    pending_lbl = _stat_card(stats_row, 1, "Pending", WARNING)
    progress_lbl = _stat_card(stats_row, 2, "In Progress", "#3B82F6")
    resolved_lbl = _stat_card(stats_row, 3, "Resolved", SUCCESS)

    # ---------- filter bar ----------
    filters = tk.Frame(body, bg=BG)
    filters.pack(fill="x", pady=(14, 8))

    status_var = tk.StringVar(value="All")
    category_var = tk.StringVar(value="All")

    def _filter_box(label, var, values):
        box = tk.Frame(filters, bg=BG)
        box.pack(side="left", padx=(0, 12))
        tk.Label(box, text=label, font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w")
        combo = ttk.Combobox(box, textvariable=var, values=values,
                             state="readonly", width=15, font=FONT_SMALL)
        combo.pack()
        combo.bind("<<ComboboxSelected>>", lambda e: load_table())
        return combo

    _filter_box("Status", status_var, ["All"] + list(STATUSES))
    category_combo = _filter_box("Category", category_var, ["All"] + list(DEFAULT_CATEGORIES))

    search_box = tk.Frame(filters, bg=BG)
    search_box.pack(side="left", padx=(0, 12))
    tk.Label(search_box, text="Search", font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w")
    search_border, search_entry, search_var, _ = _make_field(search_box)
    search_entry.config(width=24, font=FONT_SMALL)
    search_border.pack()
    search_var.trace_add("write", lambda *a: load_table())

    refresh_btn = _button(filters, "⟳  Refresh", lambda: load_table(),
                          font=("Segoe UI", 10, "bold"), pady=6, padx=14)
    refresh_btn.pack(side="right", anchor="s")

    count_label = tk.Label(filters, text="", font=FONT_SMALL, bg=BG, fg=MUTED)
    count_label.pack(side="right", anchor="s", padx=14, pady=(0, 6))

    # ---------- content: table (left) + details (right) ----------
    content = tk.Frame(body, bg=BG)
    content.pack(fill="both", expand=True)

    # ----- table -----
    table_frame = tk.Frame(content, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    table_frame.pack(side="left", fill="both", expand=True)

    columns = ("id", "student", "category", "location", "status", "department", "created")
    headings = ("ID", "Student", "Category", "Location", "Status", "Department", "Submitted")
    widths = (80, 110, 110, 110, 90, 120, 120)

    tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
    for col, head, w in zip(columns, headings, widths):
        tree.heading(col, text=head)
        tree.column(col, width=w, anchor="w", stretch=True)
    for status, color in STATUS_ROW_COLORS.items():
        tree.tag_configure(status, background=color)

    scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)

    # ----- details panel -----
    panel = tk.Frame(content, bg=WHITE, highlightbackground=BORDER,
                     highlightthickness=1, width=340)
    panel.pack(side="right", fill="y", padx=(14, 0))
    panel.pack_propagate(False)
    inner = tk.Frame(panel, bg=WHITE)
    inner.pack(fill="both", expand=True, padx=18, pady=14)

    tk.Label(inner, text="Complaint Details", font=("Segoe UI", 14, "bold"),
             bg=WHITE, fg=TEXT).pack(anchor="w")
    id_label = tk.Label(inner, text="Select a complaint", font=("Segoe UI", 12, "bold"),
                        bg=WHITE, fg=PRIMARY)
    id_label.pack(anchor="w", pady=(0, 6))

    info_vars = {}
    for key, title in (("student", "Student"), ("category", "Category"),
                       ("location", "Location"),
                       ("created", "Submitted")):
        row = tk.Frame(inner, bg=WHITE)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=title, font=FONT_SMALL, bg=WHITE, fg=MUTED,
                 width=9, anchor="w").pack(side="left")
        var = tk.StringVar(value="—")
        tk.Label(row, textvariable=var, font=("Segoe UI", 10, "bold"), bg=WHITE,
                 fg=TEXT, anchor="w", wraplength=210, justify="left").pack(side="left")
        info_vars[key] = var

    tk.Label(inner, text="Description", font=FONT_SMALL, bg=WHITE, fg=MUTED).pack(
        anchor="w", pady=(8, 2))
    desc_text = tk.Text(inner, height=3, wrap="word", font=FONT_SMALL, relief="flat",
                        bg="#F8FAFC", fg=TEXT, state="disabled", padx=8, pady=6)
    desc_text.pack(fill="x")

    # department + status dropdowns side by side
    edit_row = tk.Frame(inner, bg=WHITE)
    edit_row.pack(fill="x", pady=(10, 0))
    dept_var = tk.StringVar(value=DEPARTMENTS[0])
    edit_status_var = tk.StringVar(value=STATUSES[0])

    left_col = tk.Frame(edit_row, bg=WHITE)
    left_col.pack(side="left")
    tk.Label(left_col, text="Assign Department", font=FONT_SMALL, bg=WHITE, fg=MUTED).pack(anchor="w")
    ttk.Combobox(left_col, textvariable=dept_var, values=DEPARTMENTS,
                 state="readonly", width=15, font=FONT_SMALL).pack()

    right_col = tk.Frame(edit_row, bg=WHITE)
    right_col.pack(side="right")
    tk.Label(right_col, text="Update Status", font=FONT_SMALL, bg=WHITE, fg=MUTED).pack(anchor="w")
    ttk.Combobox(right_col, textvariable=edit_status_var, values=STATUSES,
                 state="readonly", width=12, font=FONT_SMALL).pack()

    message_label = tk.Label(inner, text="", font=FONT_SMALL, bg=WHITE, fg=MUTED,
                             wraplength=300, justify="left", anchor="w")

    save_btn = _button(inner, "Save Changes", lambda: save_changes(),
                       bg=SUCCESS, hover="#15803D")
    save_btn.pack(fill="x", pady=(12, 0))
    message_label.pack(fill="x", pady=(6, 4))

    tk.Label(inner, text="Status History", font=FONT_SMALL, bg=WHITE, fg=MUTED).pack(anchor="w")
    history_text = tk.Text(inner, height=4, wrap="none", font=("Segoe UI", 9), relief="flat",
                           bg="#F8FAFC", fg=TEXT, state="disabled", padx=8, pady=6)
    history_text.pack(fill="both", expand=True)

    # ---------- behaviour ----------
    def set_message(text, color=MUTED):
        message_label.config(text=text, fg=color)

    def show_details(c):
        """Fill the right-hand panel with one complaint."""
        state["selected_id"] = c["complaint_id"]
        id_label.config(text=database.format_complaint_id(c["complaint_id"]))
        info_vars["student"].set(c.get("student_name", "—"))
        info_vars["category"].set(c["category"])
        info_vars["location"].set(c["location"])
        info_vars["created"].set(c["created_at"])
        _set_text(desc_text, c["description"])
        dept_var.set(c.get("department") or DEPARTMENTS[0])
        edit_status_var.set(c["status"])

        lines = []
        for h in database.get_complaint_history(c["complaint_id"]):
            old = h["old_status"] or "New"
            lines.append(f"{h['changed_at']}   {old} → {h['new_status']}")
        _set_text(history_text, "\n".join(lines))

    def clear_details():
        state["selected_id"] = None
        id_label.config(text="Select a complaint")
        for var in info_vars.values():
            var.set("—")
        _set_text(desc_text, "")
        _set_text(history_text, "")

    def load_table():
        """Reload statistics and the complaint table using the current filters."""
        # summary cards
        stats = database.get_statistics()
        total_lbl.config(text=str(stats["total"]))
        pending_lbl.config(text=str(stats["by_status"].get("Pending", 0)))
        progress_lbl.config(text=str(stats["by_status"].get("In Progress", 0)))
        resolved_lbl.config(text=str(stats["by_status"].get("Resolved", 0)))

        # category dropdown = defaults + anything found in the data
        categories = list(DEFAULT_CATEGORIES)
        for cat in stats["by_category"]:
            if cat not in categories:
                categories.append(cat)
        category_combo.config(values=["All"] + categories)

        # table
        rows = database.get_all_complaints()
        if status_var.get() != "All":
            rows = [c for c in rows if c["status"] == status_var.get()]
        if category_var.get() != "All":
            rows = [c for c in rows if c["category"] == category_var.get()]
        term = search_var.get().strip().lower()
        if term:
            def matches(c):
                text = " ".join(str(c.get(k, "")) for k in
                                ("student_name", "category", "location", "description", "department"))
                text += " " + database.format_complaint_id(c["complaint_id"])
                return term in text.lower()
            rows = [c for c in rows if matches(c)]

        tree.delete(*tree.get_children())
        current_rows.clear()
        for c in rows:
            cid = c["complaint_id"]
            current_rows[cid] = c
            tree.insert("", "end", iid=str(cid), tags=(c["status"],), values=(
                database.format_complaint_id(cid), c.get("student_name", ""),
                c["category"], c["location"],
                c["status"], c["department"], c["created_at"][:16],
            ))
        count_label.config(text=f"Showing {len(rows)} of {stats['total']} complaints")

        # keep the previous selection if that complaint is still visible
        sel = state["selected_id"]
        if sel in current_rows:
            tree.selection_set(str(sel))
            tree.see(str(sel))
            show_details(current_rows[sel])
        else:
            clear_details()

    def on_select(event=None):
        selected = tree.selection()
        if selected:
            show_details(current_rows[int(selected[0])])
            set_message("")

    def save_changes():
        cid = state["selected_id"]
        if cid is None:
            set_message("Select a complaint from the table first.", ERROR)
            return
        new_status = edit_status_var.get()
        department = dept_var.get()
        if new_status not in STATUSES:
            set_message("Please choose a valid status.", ERROR)
            return

        try:
            database.update_complaint_status(cid, new_status)
            database.assign_department(cid, department)
        except Exception as error:
            set_message(f"Could not save the changes: {error}", ERROR)
            return
        load_table()
        set_message(f"{database.format_complaint_id(cid)} updated successfully.", SUCCESS)

    tree.bind("<<TreeviewSelect>>", on_select)
    load_table()


# ------------------------------------------------------------ self-test ----
# Run `python admin.py` to see only the admin screen (adds sample data if empty).
if __name__ == "__main__":
    database.create_tables()
    if database.user_count() == 0:
        database.add_user("Admin", "admin@campus.edu", "admin123", "admin")
        database.add_user("Test Student", "student@campus.edu", "student123", "student")

    if database.get_statistics()["total"] == 0:
        student = database.authenticate_user("student@campus.edu", "student123")
        if student:
            samples = [
                ("Air Conditioning", "Room 301", "AC is not cooling in the classroom."),
                ("Furniture", "Library", "Two chairs have broken legs."),
                ("Internet", "Hostel Block B", "Wi-Fi keeps disconnecting every few minutes."),
                ("Electrical", "Lab 2", "Tube light flickering near the entrance."),
            ]
            for cat, loc, desc in samples:
                database.add_complaint(student["user_id"], cat, loc, desc)

    test_root = tk.Tk()
    test_root.title("CampusCare - Admin Test")
    show_admin_dashboard(test_root, {"name": "Admin", "role": "admin"}, test_root.destroy)
    test_root.mainloop()
