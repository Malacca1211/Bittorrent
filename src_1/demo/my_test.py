
import os
import psutil

def kill_process_by_port(port):
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            pid = conn.pid
            os.kill(pid, 9)  # Send SIGKILL signal to the process
            print(f"Process running on port {port} (PID: {pid}) killed.")
            return
    print(f"No process found running on port {port}.")

# Example usage to kill process on port 6666
kill_process_by_port(6666)



