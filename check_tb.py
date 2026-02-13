import ttkbootstrap as tb
print("ScrolledFrame" in dir(tb))
try:
    from ttkbootstrap.scrolled import ScrolledFrame
    print("Found in ttkbootstrap.scrolled")
except ImportError:
    print("Not found in scrolled")
