import os
import subprocess
import time
import psutil

# === Absolute Paths ===
BACKEND_DIR = os.path.join(os.getcwd(), "backend")
FRONTEND_DIR = os.path.join(os.getcwd(), "frontend")

# === Commands ===
BACKEND_COMMANDS = [
    ["python", "mqtt_manager.py", "--simulate", "--subscribe"],
    ["python", "app.py"]
]

FRONTEND_COMMAND = ["npm", "start"]

# === Process Matching Keywords ===
PROCESS_KEYWORDS = [
    "mqtt_manager.py",
    "app.py",
    "npm", "node"
]

# === Launch Command in New Terminal ===
def run_in_terminal(command, cwd):
    if os.name == "nt":
        subprocess.Popen(["start", "cmd", "/k"] + command, cwd=cwd, shell=True)
    else:
        subprocess.Popen(["gnome-terminal", "--"] + command, cwd=cwd)

# === Start All Services ===
def start_project():
    print("🚀 Starting backend services...")
    for cmd in BACKEND_COMMANDS:
        run_in_terminal(cmd, BACKEND_DIR)
        time.sleep(1)

    print("🚀 Launching React frontend...")
    run_in_terminal(FRONTEND_COMMAND, FRONTEND_DIR)

    print("✅ Project launched successfully.")

# === Stop All Services ===
def stop_project():
    print("🛑 Stopping project processes...")
    found = False

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = " ".join(proc.info['cmdline']) if isinstance(proc.info['cmdline'], list) else ""
            name = proc.info['name'].lower()

            if any(keyword in cmdline for keyword in PROCESS_KEYWORDS):
                print(f"✔ Terminating PID {proc.pid} - {name}")
                proc.terminate()
                found = True
        except Exception:
            continue

    if not found:
        print(" No matching project processes found.")
    else:
        time.sleep(2)
        print("✅All project processes terminated.")

# === CLI Prompt ===
if __name__ == "__main__":
    print("\nIoT Project Launcher")
    print("=======================")
    print("1. Start Project")
    print("2. Stop Project")
    choice = input("Choose an option (1 or 2): ").strip()

    if choice == "1":
        start_project()
    elif choice == "2":
        stop_project()
    else:
        print("❌ Invalid choice. Please run again and enter 1 or 2.")
