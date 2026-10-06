import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, src_dir)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    
    from gui import App
    app = App()
    app.mainloop()