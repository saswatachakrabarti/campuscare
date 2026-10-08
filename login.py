"""
login.py
--------
User and Login Module (CampusCare)

Shows the login screen, checks the credentials against the Users table
(through database.authenticate_user) and tells main.py who logged in.

How other files use this module:
    import login
    login.show_login(root, on_login_success)

    on_login_success(user) is called with a dict such as:
    {"user_id": 1, "name": "Admin", "email": "...", "password": "<hash>", "role": "admin"}
"""

import re
import tkinter as tk

import database

# ------------------------------------------------------------ theme ----
PRIMARY = "#2563EB"       # main blue
PRIMARY_DARK = "#1D4ED8"  # button hover
PANEL = "#1E3A8A"         # left panel
BG = "#EEF2F7"            # window background
WHITE = "#FFFFFF"
BORDER = "#CBD5E1"
TEXT = "#0F172A"
MUTED = "#64748B"
ERROR = "#DC2626"
SUCCESS = "#15803D"

MIN_PASSWORD_LENGTH = 6
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

FONT = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 9)
FONT_LABEL = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 22, "bold")


def _make_field(parent, hidden=False):
    """Entry box with a border that turns blue when focused.
    Returns (container, entry, var, inner_frame)."""
    border = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
    inner = tk.Frame(border, bg=WHITE)
    inner.pack(fill="x")

    var = tk.StringVar()
    entry = tk.Entry(
        inner, textvariable=var, font=FONT, relief="flat", bd=0,
        bg=WHITE, fg=TEXT, insertbackground=TEXT,
        show="•" if hidden else "",
    )
    entry.pack(side="left", fill="x", expand=True, padx=10, pady=9)

    entry.bind("<FocusIn>", lambda e: border.config(bg=PRIMARY))
    entry.bind("<FocusOut>", lambda e: border.config(bg=BORDER))
    return border, entry, var, inner


def _make_card(root, height):
    """Clear the window and build the shared card with the blue branding panel.
    Returns the white form panel on the right."""
    for widget in root.winfo_children():
        widget.destroy()
    root.configure(bg=BG)

    # ---------- card ----------
    card = tk.Frame(root, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    card.place(relx=0.5, rely=0.5, anchor="center", width=720, height=height)

    # ---------- left branding panel ----------
    left = tk.Frame(card, bg=PANEL, width=290)
    left.pack(side="left", fill="y")
    left.pack_propagate(False)

    brand = tk.Frame(left, bg=PANEL)
    brand.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(brand, text="🏫", font=("Segoe UI Emoji", 40), bg=PANEL, fg=WHITE).pack()
    tk.Label(brand, text="CampusCare", font=("Segoe UI", 24, "bold"),
             bg=PANEL, fg=WHITE).pack(pady=(5, 2))
    tk.Label(brand, text="Digital Complaint Tracking\nfor Campus Facilities",
             font=FONT, bg=PANEL, fg="#BFDBFE", justify="center").pack(pady=(0, 25))

    for line in ("✓  Report facility issues", "✓  Track complaint status", "✓  Faster resolution"):
        tk.Label(brand, text=line, font=FONT, bg=PANEL, fg=WHITE, anchor="w").pack(
            anchor="w", pady=3
        )

    # ---------- right form panel ----------
    right = tk.Frame(card, bg=WHITE)
    right.pack(side="left", fill="both", expand=True, padx=40, pady=30)
    return right


def _make_button(parent, text, command):
    """Big blue button (a Label so colours work on every OS)."""
    button = tk.Label(parent, text=text, font=("Segoe UI", 12, "bold"),
                      bg=PRIMARY, fg=WHITE, cursor="hand2", pady=10)
    button.bind("<Button-1>", command)
    button.bind("<Enter>", lambda e: button.config(bg=PRIMARY_DARK))
    button.bind("<Leave>", lambda e: button.config(bg=PRIMARY))
    return button


def _make_link_row(parent, prompt, link_text, command):
    """A line like  'New here?  Sign up'  where the second part is clickable."""
    row = tk.Frame(parent, bg=WHITE)
    tk.Label(row, text=prompt, font=FONT_SMALL, bg=WHITE, fg=MUTED).pack(side="left")
    link = tk.Label(row, text=link_text, font=("Segoe UI", 9, "bold"),
                    bg=WHITE, fg=PRIMARY, cursor="hand2")
    link.pack(side="left", padx=(4, 0))
    link.bind("<Button-1>", lambda e: command())
    return row


def show_login(root, on_login_success, notice="", prefill_email=""):
    """Clear the window and display the login screen.

    notice        - optional green message (e.g. 'Account created')
    prefill_email - optional email to put in the email box
    """
    right = _make_card(root, height=470)

    tk.Label(right, text="Welcome back", font=FONT_TITLE, bg=WHITE, fg=TEXT).pack(anchor="w")
    tk.Label(right, text="Sign in to continue", font=FONT, bg=WHITE, fg=MUTED).pack(
        anchor="w", pady=(0, 22)
    )

    # email
    tk.Label(right, text="Email", font=FONT_LABEL, bg=WHITE, fg=TEXT).pack(anchor="w", pady=(0, 4))
    email_box, email_entry, email_var, _ = _make_field(right)
    email_box.pack(fill="x", pady=(0, 14))

    # password
    tk.Label(right, text="Password", font=FONT_LABEL, bg=WHITE, fg=TEXT).pack(anchor="w", pady=(0, 4))
    pwd_box, pwd_entry, pwd_var, pwd_inner = _make_field(right, hidden=True)
    pwd_box.pack(fill="x")

    toggle = tk.Label(pwd_inner, text="Show", font=FONT_SMALL, bg=WHITE, fg=PRIMARY, cursor="hand2")
    toggle.pack(side="right", padx=10)

    def toggle_password(event=None):
        if pwd_entry.cget("show") == "":
            pwd_entry.config(show="•")
            toggle.config(text="Show")
        else:
            pwd_entry.config(show="")
            toggle.config(text="Hide")

    toggle.bind("<Button-1>", toggle_password)

    # message label (errors appear here)
    message_label = tk.Label(right, text=notice, font=FONT_SMALL, bg=WHITE,
                             fg=SUCCESS if notice else ERROR, anchor="w")
    message_label.pack(fill="x", pady=(8, 8))

    if prefill_email:
        email_var.set(prefill_email)

    # ---------- login logic ----------
    def attempt_login(event=None):
        email = email_var.get().strip()
        password = pwd_var.get()

        if not email or not password:
            message_label.config(text="Please enter both email and password.", fg=ERROR)
            return

        user = database.authenticate_user(email, password)
        if user is None:
            message_label.config(text="Invalid email or password.", fg=ERROR)
            pwd_var.set("")
            pwd_entry.focus()
            return

        on_login_success(user)

    # login button
    _make_button(right, "Login", attempt_login).pack(fill="x")

    # pressing Enter in either box also logs in
    email_entry.bind("<Return>", attempt_login)
    pwd_entry.bind("<Return>", attempt_login)

    # link to the signup screen
    _make_link_row(
        right, "New student?", "Create an account",
        lambda: show_signup(root, on_login_success),
    ).pack(pady=(14, 0))

    tk.Label(right, text="Contact your administrator if you forgot your password.",
             font=FONT_SMALL, bg=WHITE, fg=MUTED).pack(side="bottom", anchor="w")

    if prefill_email:
        pwd_entry.focus()
    else:
        email_entry.focus()


def show_signup(root, on_login_success):
    """Clear the window and display the student signup screen."""
    right = _make_card(root, height=540)

    tk.Label(right, text="Create account", font=FONT_TITLE, bg=WHITE, fg=TEXT).pack(anchor="w")
    tk.Label(right, text="Sign up as a student to report issues", font=FONT,
             bg=WHITE, fg=MUTED).pack(anchor="w", pady=(0, 14))

    def labelled_field(label, hidden=False):
        tk.Label(right, text=label, font=FONT_LABEL, bg=WHITE, fg=TEXT).pack(anchor="w", pady=(0, 3))
        box, entry, var, inner = _make_field(right, hidden=hidden)
        box.pack(fill="x", pady=(0, 9))
        return entry, var, inner

    name_entry, name_var, _ = labelled_field("Full name")
    email_entry, email_var, _ = labelled_field("Email")
    pwd_entry, pwd_var, pwd_inner = labelled_field(f"Password (min {MIN_PASSWORD_LENGTH} characters)", hidden=True)
    confirm_entry, confirm_var, _ = labelled_field("Confirm password", hidden=True)

    # one Show/Hide toggle controls both password boxes
    toggle = tk.Label(pwd_inner, text="Show", font=FONT_SMALL, bg=WHITE, fg=PRIMARY, cursor="hand2")
    toggle.pack(side="right", padx=10)

    def toggle_password(event=None):
        hiding = pwd_entry.cget("show") == ""
        for entry in (pwd_entry, confirm_entry):
            entry.config(show="•" if hiding else "")
        toggle.config(text="Show" if hiding else "Hide")

    toggle.bind("<Button-1>", toggle_password)

    message_label = tk.Label(right, text="", font=FONT_SMALL, bg=WHITE, fg=ERROR,
                             anchor="w", justify="left", wraplength=300)
    message_label.pack(fill="x", pady=(0, 6))

    def attempt_signup(event=None):
        name = " ".join(name_var.get().split())
        email = email_var.get().strip().lower()
        password = pwd_var.get()
        confirm = confirm_var.get()

        if not name or not email or not password or not confirm:
            message_label.config(text="Please fill in all the fields.")
            return
        if len(name) < 2:
            message_label.config(text="Please enter your full name.")
            name_entry.focus()
            return
        if not EMAIL_PATTERN.match(email):
            message_label.config(text="Please enter a valid email address.")
            email_entry.focus()
            return
        if len(password) < MIN_PASSWORD_LENGTH:
            message_label.config(
                text=f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
            pwd_entry.focus()
            return
        if password != confirm:
            message_label.config(text="Passwords do not match.")
            confirm_var.set("")
            confirm_entry.focus()
            return

        user_id = database.register_student(name, email, password)
        if user_id is None:
            message_label.config(text="An account with this email already exists.")
            email_entry.focus()
            return

        # success: send them back to login with their email filled in
        show_login(root, on_login_success,
                   notice="Account created! Please log in.", prefill_email=email)

    _make_button(right, "Sign up", attempt_signup).pack(fill="x")

    for entry in (name_entry, email_entry, pwd_entry, confirm_entry):
        entry.bind("<Return>", attempt_signup)

    _make_link_row(
        right, "Already have an account?", "Log in",
        lambda: show_login(root, on_login_success),
    ).pack(pady=(10, 0))

    name_entry.focus()


# Quick test: run `python login.py` to see only the login window.
if __name__ == "__main__":
    database.create_tables()
    if database.user_count() == 0:
        database.add_user("Admin", "admin@campus.edu", "admin123", "admin")
        database.add_user("Test Student", "student@campus.edu", "student123", "student")

    test_root = tk.Tk()
    test_root.title("CampusCare - Login Test")
    test_root.geometry("800x600")

    def _print_user(user):
        print("Logged in:", user["name"], "-", user["role"])

    show_login(test_root, _print_user)
    test_root.mainloop()
