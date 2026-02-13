import ttkbootstrap as tb
import sys

try:
    print("Initializing tb.Window...")
    root = tb.Window(themename="cosmo")
    print("Window initialized.")
    root.geometry("200x200")
    tb.Label(root, text="Test Success").pack()
    print("Starting mainloop... (will exit in 3s)")
    root.after(3000, root.destroy)
    root.mainloop()
    print("Mainloop finished.")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
