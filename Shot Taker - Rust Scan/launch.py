import subprocess
import sys
import os

# Get the directory this script lives in
base_dir = os.path.dirname(os.path.abspath(__file__))
main_script = os.path.join(base_dir, "main.py")
user_data_dir = os.path.join(base_dir, "user_data")
os.makedirs(user_data_dir, exist_ok=True)
log_file = os.path.join(user_data_dir, "launch_error.log")
lock_file = os.path.join(user_data_dir, "shottaker.lock")


# =========================
# SINGLE INSTANCE CHECK
# =========================
def is_already_running():
    if not os.path.exists(lock_file):
        return False
    try:
        with open(lock_file, "r") as f:
            pid = int(f.read().strip())
        import psutil
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline()).lower()
        if "main.py" in cmdline or "shottaker" in cmdline:
            return True
        return False  # stale lock — different process has this PID now
    except Exception:
        return False  # psutil missing, process gone, or bad lock file


def write_lock(pid):
    try:
        with open(lock_file, "w") as f:
            f.write(str(pid))
    except OSError:
        pass


def focus_existing():
    """Write a focus flag so the running instance brings its window to front."""
    try:
        focus_flag = os.path.join(user_data_dir, "commands", "focus.flag")
        os.makedirs(os.path.dirname(focus_flag), exist_ok=True)
        with open(focus_flag, "w") as f:
            f.write("1")
    except OSError:
        pass


if is_already_running():
    focus_existing()
    sys.exit(0)


try:
    if os.name == "nt":
        # Windows — CREATE_NO_WINDOW hides the console
        CREATE_NO_WINDOW = 0x08000000
        proc = subprocess.Popen(
            [sys.executable, main_script],
            creationflags=CREATE_NO_WINDOW,
            cwd=base_dir,
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT
        )
    else:
        # Mac / Linux
        proc = subprocess.Popen(
            [sys.executable, main_script],
            cwd=base_dir
        )

    write_lock(proc.pid)

except Exception as e:
    with open(log_file, "w") as f:
        f.write(f"Launch failed: {e}\n")
        f.write(f"Python: {sys.executable}\n")
        f.write(f"Script: {main_script}\n")
