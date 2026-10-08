"""
complaint.py
------------
Complaint Submission and Tracking Module (CampusCare, student side)

Two tabs:
  1. New Complaint  - form (category, location, priority, description),
                      validation, and the generated complaint ID after saving.
  2. My Complaints  - table of the student's own complaints, with search,
                      status filter, a progress tracker and the full status history.

How other files use this module:
    import complaint
    complaint.show_student_dashboard(root, user, on_logout)

Run `python complaint.py` to test this screen on its own.
"""

import tkinter as tk
from tkinter import ttk

import database
from login import (  # same colours/fonts as the rest of the app
    PRIMARY, PRIMARY_DARK, PANEL, BG, WHITE, BORDER, TEXT, MUTED, ERROR,
    FONT, FONT_SMALL, FONT_LABEL, _make_field,
)
from admin import (  # same categories/statuses as the admin screen
    SUCCESS, WARNING, STATUSES, PRIORITIES, DEFAULT_CATEGORIES, STATUS_ROW_COLORS,
)

# ------------------------------------------------------------ settings ----
CATEGORY_PLACEHOLDER = "Select a category"
MIN_DESCRIPTION = 10
MAX_DESCRIPTION = 500

STATUS_BADGE_COLORS = {
    "Pending": WARNING,
    "In Progress": "#3B82F6",
    "Resolved": SUCCESS,
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


def _set_text(widget, content):
    """Fill a read-only Text widget."""
    widget.config(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.config(state="disabled")


def _text_box(parent, height, editable=True):
    """Multi-line box with a border that turns blue when focused."""
    border = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
    text = tk.Text(border, height=height, wrap="word", font=FONT, relief="flat", bd=0,
                   bg=WHITE if editable else "#F8FAFC", fg=TEXT,
                   insertbackground=TEXT, padx=10, pady=8)
    text.pack(fill="both", expand=True)
    if editable:
        text.bind("<FocusIn>", lambda e: border.config(bg=PRIMARY))
        text.bind("<FocusOut>", lambda e: border.config(bg=BORDER))
    else:
        text.config(state="disabled")
    return border, text


# ---------------------------------------------------------- main screen ----
def show_student_dashboard(root, user, on_logout):
    """Clear the window and display the student dashboard."""
    for widget in root.winfo_children():
        widget.destroy()
    root.configure(bg=BG)
    root.geometry("1100x700")
    root.minsize(950, 620)

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
    tk.Label(topbar, text="Student Portal", font=FONT,
             bg=PANEL, fg="#BFDBFE").pack(side="left")

    logout_btn = _button(topbar, "Logout", on_logout, bg="#DC2626", hover="#B91C1C",
                         font=("Segoe UI", 10, "bold"), pady=6, padx=16)
    logout_btn.pack(side="right", padx=20)
    tk.Label(topbar, text=f"Welcome, {user['name']}", font=FONT,
             bg=PANEL, fg=WHITE).pack(side="right")

    # ---------- tab bar + pages ----------
    tabs = tk.Frame(root, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    tabs.pack(fill="x")
    holder = tk.Frame(root, bg=BG)
    holder.pack(fill="both", expand=True)

    new_page = tk.Frame(holder, bg=BG)
    track_page = tk.Frame(holder, bg=BG)

    tab_parts = {}

    def select_tab(name):
        for key, (lbl, line, page) in tab_parts.items():
            if key == name:
                lbl.config(fg=PRIMARY)
                line.config(bg=PRIMARY)
                page.pack(fill="both", expand=True)
            else:
                lbl.config(fg=MUTED)
                line.config(bg=WHITE)
                page.pack_forget()
        if name == "track":
            load_table()

    for key, title, page in (("new", "＋  New Complaint", new_page),
                             ("track", "📋  My Complaints", track_page)):
        cell = tk.Frame(tabs, bg=WHITE)
        cell.pack(side="left", padx=(20 if key == "new" else 0, 0))
        lbl = tk.Label(cell, text=title, font=("Segoe UI", 11, "bold"), bg=WHITE,
                       fg=MUTED, cursor="hand2", padx=18, pady=12)
        lbl.pack()
        line = tk.Frame(cell, bg=WHITE, height=3)
        line.pack(fill="x")
        lbl.bind("<Button-1>", lambda e, k=key: select_tab(k))
        tab_parts[key] = (lbl, line, page)

    # =====================================================================
    # TAB 1: NEW COMPLAINT
    # =====================================================================
    card = tk.Frame(new_page, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    card.pack(pady=22)
    form = tk.Frame(card, bg=WHITE)
    form.pack(padx=40, pady=26)

    tk.Label(form, text="Report a Problem", font=("Segoe UI", 20, "bold"),
             bg=WHITE, fg=TEXT).pack(anchor="w")
    tk.Label(form, text="Tell us what is wrong and where, and the right team will look into it.",
             font=FONT, bg=WHITE, fg=MUTED).pack(anchor="w", pady=(0, 16))

    # category + location side by side
    row1 = tk.Frame(form, bg=WHITE)
    row1.pack(fill="x")

    col_cat = tk.Frame(row1, bg=WHITE)
    col_cat.pack(side="left", fill="x", expand=True, padx=(0, 14))
    tk.Label(col_cat, text="Category", font=FONT_LABEL, bg=WHITE, fg=TEXT).pack(anchor="w", pady=(0, 4))
    category_var = tk.StringVar(value=CATEGORY_PLACEHOLDER)
    ttk.Combobox(col_cat, textvariable=category_var, values=DEFAULT_CATEGORIES,
                 state="readonly", font=FONT).pack(fill="x", ipady=5)

    col_loc = tk.Frame(row1, bg=WHITE)
    col_loc.pack(side="left", fill="x", expand=True)
    tk.Label(col_loc, text="Location", font=FONT_LABEL, bg=WHITE, fg=TEXT).pack(anchor="w", pady=(0, 4))
    loc_box, loc_entry, location_var, _ = _make_field(col_loc)
    loc_box.pack(fill="x")
    tk.Label(col_loc, text="e.g. Room 301, Library, Hostel Block B", font=FONT_SMALL,
             bg=WHITE, fg=MUTED).pack(anchor="w", pady=(2, 0))

    # priority chips
    tk.Label(form, text="Priority", font=FONT_LABEL, bg=WHITE, fg=TEXT).pack(
        anchor="w", pady=(14, 4))
    priority_var = tk.StringVar(value="Medium")
    chip_row = tk.Frame(form, bg=WHITE)
    chip_row.pack(anchor="w")
    chips = {}

    def refresh_chips():
        for p, chip in chips.items():
            if priority_var.get() == p:
                chip.config(bg=PRIMARY, fg=WHITE)
            else:
                chip.config(bg="#F1F5F9", fg=TEXT)

    def choose_priority(p):
        priority_var.set(p)
        refresh_chips()

    for p in PRIORITIES:
        chip = tk.Label(chip_row, text=p, font=("Segoe UI", 10, "bold"),
                        cursor="hand2", padx=22, pady=6)
        chip.pack(side="left", padx=(0, 8))
        chip.bind("<Button-1>", lambda e, p=p: choose_priority(p))
        chips[p] = chip
    refresh_chips()

    # description
    tk.Label(form, text="Description", font=FONT_LABEL, bg=WHITE, fg=TEXT).pack(
        anchor="w", pady=(14, 4))
    desc_border, desc_text = _text_box(form, height=6)
    desc_border.pack(fill="x")
    counter_label = tk.Label(form, text=f"0 / {MAX_DESCRIPTION}", font=FONT_SMALL,
                             bg=WHITE, fg=MUTED)
    counter_label.pack(anchor="e", pady=(2, 0))

    def update_counter(event=None):
        n = len(desc_text.get("1.0", "end").strip())
        counter_label.config(text=f"{n} / {MAX_DESCRIPTION}",
                             fg=ERROR if n > MAX_DESCRIPTION else MUTED)

    desc_text.bind("<KeyRelease>", update_counter)

    # message banner
    form_message = tk.Label(form, text="", font=("Segoe UI", 10, "bold"), bg=WHITE,
                            fg=ERROR, wraplength=520, justify="left", anchor="w")
    form_message.pack(fill="x", pady=(8, 8))

    def set_form_message(text, color=ERROR):
        form_message.config(text=text, fg=color)

    def reset_form():
        category_var.set(CATEGORY_PLACEHOLDER)
        location_var.set("")
        desc_text.delete("1.0", "end")
        choose_priority("Medium")
        update_counter()

    def submit_complaint():
        category = category_var.get().strip()
        location = location_var.get().strip()
        description = desc_text.get("1.0", "end").strip()

        if category == CATEGORY_PLACEHOLDER or not category:
            set_form_message("Please select a category.")
            return
        if not location:
            set_form_message("Please enter the location of the problem.")
            return
        if len(description) < MIN_DESCRIPTION:
            set_form_message(f"Please describe the problem (at least {MIN_DESCRIPTION} characters).")
            return
        if len(description) > MAX_DESCRIPTION:
            set_form_message(f"Description is too long (maximum {MAX_DESCRIPTION} characters).")
            return

        try:
            complaint_id = database.add_complaint(
                user["user_id"], category, location, description, priority_var.get()
            )
        except Exception as error:  # never crash the window on a database problem
            set_form_message(f"Could not save the complaint: {error}")
            return

        reset_form()
        state["selected_id"] = complaint_id
        set_form_message(
            f"✓ Complaint {database.format_complaint_id(complaint_id)} submitted. "
            "Keep this ID to track it under 'My Complaints'.", SUCCESS)

    _button(form, "Submit Complaint", submit_complaint).pack(fill="x")

    # =====================================================================
    # TAB 2: MY COMPLAINTS
    # =====================================================================
    track_body = tk.Frame(track_page, bg=BG)
    track_body.pack(fill="both", expand=True, padx=20, pady=14)

    # ---------- filter bar ----------
    filters = tk.Frame(track_body, bg=BG)
    filters.pack(fill="x", pady=(0, 8))

    status_var = tk.StringVar(value="All")
    status_box = tk.Frame(filters, bg=BG)
    status_box.pack(side="left", padx=(0, 12))
    tk.Label(status_box, text="Status", font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w")
    status_combo = ttk.Combobox(status_box, textvariable=status_var,
                                values=["All"] + list(STATUSES),
                                state="readonly", width=15, font=FONT_SMALL)
    status_combo.pack()
    status_combo.bind("<<ComboboxSelected>>", lambda e: load_table())

    search_box = tk.Frame(filters, bg=BG)
    search_box.pack(side="left")
    tk.Label(search_box, text="Search by ID, category or location", font=FONT_SMALL,
             bg=BG, fg=MUTED).pack(anchor="w")
    search_border, search_entry, search_var, _ = _make_field(search_box)
    search_entry.config(width=28, font=FONT_SMALL)
    search_border.pack()
    search_var.trace_add("write", lambda *a: load_table())

    _button(filters, "⟳  Refresh", lambda: load_table(),
            font=("Segoe UI", 10, "bold"), pady=6, padx=14).pack(side="right", anchor="s")
    count_label = tk.Label(filters, text="", font=FONT_SMALL, bg=BG, fg=MUTED)
    count_label.pack(side="right", anchor="s", padx=14, pady=(0, 6))

    # ---------- content: table (left) + details (right) ----------
    content = tk.Frame(track_body, bg=BG)
    content.pack(fill="both", expand=True)

    table_frame = tk.Frame(content, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    table_frame.pack(side="left", fill="both", expand=True)

    columns = ("id", "category", "location", "priority", "status", "created")
    headings = ("ID", "Category", "Location", "Priority", "Status", "Submitted")
    widths = (80, 120, 130, 70, 100, 130)

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
                     highlightthickness=1, width=360)
    panel.pack(side="right", fill="y", padx=(14, 0))
    panel.pack_propagate(False)
    inner = tk.Frame(panel, bg=WHITE)
    inner.pack(fill="both", expand=True, padx=18, pady=14)

    tk.Label(inner, text="Complaint Details", font=("Segoe UI", 14, "bold"),
             bg=WHITE, fg=TEXT).pack(anchor="w")

    id_row = tk.Frame(inner, bg=WHITE)
    id_row.pack(fill="x", pady=(0, 8))
    id_label = tk.Label(id_row, text="Select a complaint", font=("Segoe UI", 12, "bold"),
                        bg=WHITE, fg=PRIMARY)
    id_label.pack(side="left")
    badge = tk.Label(id_row, text="", font=("Segoe UI", 9, "bold"), fg=WHITE, padx=10, pady=2)
    badge.pack(side="right")

    # progress tracker: Pending -- In Progress -- Resolved
    progress_row = tk.Frame(inner, bg=WHITE)
    progress_row.pack(fill="x", pady=(0, 8))
    step_labels = []
    for i, step in enumerate(STATUSES):
        lbl = tk.Label(progress_row, text=f"○ {step}", font=("Segoe UI", 9, "bold"),
                       bg=WHITE, fg=MUTED)
        lbl.pack(side="left")
        step_labels.append(lbl)
        if i < len(STATUSES) - 1:
            tk.Label(progress_row, text=" ── ", font=FONT_SMALL, bg=WHITE, fg=BORDER).pack(side="left")

    info_vars = {}
    for key, title in (("category", "Category"), ("location", "Location"),
                       ("priority", "Priority"), ("department", "Handled by"),
                       ("created", "Submitted")):
        row = tk.Frame(inner, bg=WHITE)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=title, font=FONT_SMALL, bg=WHITE, fg=MUTED,
                 width=10, anchor="w").pack(side="left")
        var = tk.StringVar(value="—")
        tk.Label(row, textvariable=var, font=("Segoe UI", 10, "bold"), bg=WHITE,
                 fg=TEXT, anchor="w", wraplength=220, justify="left").pack(side="left")
        info_vars[key] = var

    tk.Label(inner, text="Description", font=FONT_SMALL, bg=WHITE, fg=MUTED).pack(
        anchor="w", pady=(8, 2))
    detail_desc = tk.Text(inner, height=4, wrap="word", font=FONT_SMALL, relief="flat",
                          bg="#F8FAFC", fg=TEXT, state="disabled", padx=8, pady=6)
    detail_desc.pack(fill="x")

    tk.Label(inner, text="Status History", font=FONT_SMALL, bg=WHITE, fg=MUTED).pack(
        anchor="w", pady=(10, 2))
    history_text = tk.Text(inner, height=5, wrap="none", font=("Segoe UI", 9), relief="flat",
                           bg="#F8FAFC", fg=TEXT, state="disabled", padx=8, pady=6)
    history_text.pack(fill="both", expand=True)

    # ---------- behaviour ----------
    def update_progress(status):
        reached = STATUSES.index(status) if status in STATUSES else -1
        for i, lbl in enumerate(step_labels):
            if i <= reached:
                lbl.config(text=f"● {STATUSES[i]}", fg=SUCCESS)
            else:
                lbl.config(text=f"○ {STATUSES[i]}", fg=MUTED)

    def show_details(c):
        state["selected_id"] = c["complaint_id"]
        id_label.config(text=database.format_complaint_id(c["complaint_id"]))
        badge.config(text=c["status"], bg=STATUS_BADGE_COLORS.get(c["status"], MUTED))
        update_progress(c["status"])
        info_vars["category"].set(c["category"])
        info_vars["location"].set(c["location"])
        info_vars["priority"].set(c.get("priority", "Medium"))
        info_vars["department"].set(c.get("department") or "Unassigned")
        info_vars["created"].set(c["created_at"])
        _set_text(detail_desc, c["description"])

        lines = []
        for h in database.get_complaint_history(c["complaint_id"]):
            old = h["old_status"] or "New"
            lines.append(f"{h['changed_at']}   {old} → {h['new_status']}")
        _set_text(history_text, "\n".join(lines))

    def clear_details():
        state["selected_id"] = None
        id_label.config(text="Select a complaint")
        badge.config(text="", bg=WHITE)
        update_progress("")
        for var in info_vars.values():
            var.set("—")
        _set_text(detail_desc, "")
        _set_text(history_text, "")

    def load_table():
        """Reload this student's complaints using the current filters."""
        all_rows = database.get_complaints_by_user(user["user_id"])
        rows = all_rows

        if status_var.get() != "All":
            rows = [c for c in rows if c["status"] == status_var.get()]

        term = search_var.get().strip().lower()
        if term:
            def matches(c):
                text = " ".join(str(c.get(k, "")) for k in ("category", "location", "description"))
                text += " " + database.format_complaint_id(c["complaint_id"])
                return term in text.lower()
            rows = [c for c in rows if matches(c)]

        tree.delete(*tree.get_children())
        current_rows.clear()
        for c in rows:
            cid = c["complaint_id"]
            current_rows[cid] = c
            tree.insert("", "end", iid=str(cid), tags=(c["status"],), values=(
                database.format_complaint_id(cid), c["category"], c["location"],
                c.get("priority", "Medium"), c["status"], c["created_at"][:16],
            ))

        if not all_rows:
            count_label.config(text="You have not submitted any complaints yet.")
        else:
            count_label.config(text=f"Showing {len(rows)} of {len(all_rows)} complaints")

        # keep the previous selection (or the one just submitted) if it is visible
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

    tree.bind("<<TreeviewSelect>>", on_select)

    select_tab("new")


# ------------------------------------------------------------ self-test ----
# Run `python complaint.py` to see only the student screen.
if __name__ == "__main__":
    database.create_tables()
    if database.user_count() == 0:
        database.add_user("Admin", "admin@campus.edu", "admin123", "admin")
        database.add_user("Test Student", "student@campus.edu", "student123", "student")

    test_user = database.authenticate_user("student@campus.edu", "student123")
    if test_user is None:
        raise SystemExit("Test student not found. Delete campuscare.db and run again.")

    test_root = tk.Tk()
    test_root.title("CampusCare - Student Test")
    show_student_dashboard(test_root, test_user, test_root.destroy)
    test_root.mainloop()
