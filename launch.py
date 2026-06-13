import subprocess
import sys
import os

# Get the directory this script lives in
base_dir = os.path.dirname(os.path.abspath(__file__))
main_script = os.path.join(base_dir, "main.py")
user_data_dir = os.path.join(base_dir, "user_data")
os.makedirs(user_data_dir, exist_ok=True)
log_file = os.path.join(user_data_dir, "launch_error.log")

try:
    if os.name == "nt":
        # Windows — CREATE_NO_WINDOW flag hides the console
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

except Exception as e:
    with open(log_file, "w") as f:
        f.write(f"Launch failed: {e}\n")
        f.write(f"Python: {sys.executable}\n")
        f.write(f"Script: {main_script}\n")
