import os
import subprocess
import time
import platform
import psutil

# --- Absolute paths ---
BACKEND_DIR = os.path.join(os.getcwd(), "backend")
FRONTEND_DIR = os.path.join(os.getcwd(), "frontend")

# --- Commands ---
mqtt_command = ["python", "mqtt_manager.py", "--simulate", "--subscribe"]
other_backend_scripts = [
    ["python", "mqtt_to_mongo.py"],
    ["python", "flask_api.py"]
]

# --- Keywords for identifying project processes ---
process_keywords = [
    "mqtt_manager.py",
    "mqtt_to_mongo.py",
    "flask_api.py",
    "npm", "node",  # React frontend
]

# --- Run a command in a new terminal window ---
def run_in_terminal(command, cwd):
    if os.name == "nt":
        subprocess.Popen(["start", "cmd", "/k"] + command, cwd=cwd, shell=True)
    else:
        subprocess.Popen(["gnome-terminal", "--"] + command, cwd=cwd)

# --- Start all components ---
def start_project():
    print("🚀 Launching backend processes...")
    run_in_terminal(mqtt_command, BACKEND_DIR)
    for cmd in other_backend_scripts:
        run_in_terminal(cmd, BACKEND_DIR)
        time.sleep(2)

    print("🚀 Launching React frontend...")
    if os.name == "nt":
        subprocess.Popen(["start", "cmd", "/k", "npm start"], cwd=FRONTEND_DIR, shell=True)
    else:
        subprocess.Popen(["gnome-terminal", "--", "npm", "start"], cwd=FRONTEND_DIR)

    print("✅ All components launched.")

# --- Stop all matching project processes ---
def stop_project():
    print("🛑 Stopping project...")
    found = False

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = " ".join(proc.info['cmdline']) if isinstance(proc.info['cmdline'], list) else ""
            name = proc.info['name']

            if name.lower() in ["cmd.exe", "python.exe", "node.exe", "npm"] and any(k in cmdline for k in process_keywords):
                print(f"✔ Terminating PID {proc.pid} - {name}")
                proc.terminate()
                found = True
        except Exception:
            continue

    if not found:
        print("⚠️ No matching project processes found. (Already stopped?)")
    else:
        time.sleep(2)
        print("✅ All project processes terminated.")

# --- CLI Menu ---
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
