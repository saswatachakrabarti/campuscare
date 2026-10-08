"""
main.py
-------
Entry point of CampusCare. Run with:  python main.py

Sets up the database, opens the window, shows the login screen and sends
the user to the student or admin screen depending on their role.
"""

import tkinter as tk

import database
import login
import admin
import complaint


def show_student_screen(root, user):
    complaint.show_student_dashboard(root, user, on_logout=lambda: show_login_screen(root))


def show_admin_screen(root, user):
    admin.show_admin_dashboard(root, user, on_logout=lambda: show_login_screen(root))


def show_login_screen(root):
    # the dashboards make the window bigger, so reset it for the login card
    root.minsize(0, 0)
    root.geometry("800x600")

    def on_login_success(user):
        if user["role"] == "admin":
            show_admin_screen(root, user)
        else:
            show_student_screen(root, user)

    login.show_login(root, on_login_success)


def main():
    database.create_tables()

    # Make sure a fresh install always has accounts to log in with
    if database.user_count() == 0:
        database.add_user("Admin", "admin@campus.edu", "admin123", "admin")
        database.add_user("Test Student", "student@campus.edu", "student123", "student")

    root = tk.Tk()
    root.title("CampusCare")
    root.geometry("800x600")

    show_login_screen(root)
    root.mainloop()


if __name__ == "__main__":
    main()
