import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.85", username="chalaox", password="asd123123", timeout=10)

def run_sudo(cmd):
    print(f"=== Running: {cmd} ===")
    stdin, stdout, stderr = ssh.exec_command(f'echo asd123123 | sudo -S bash -c "{cmd}"')
    for line in iter(stdout.readline, ""):
        print(line, end="", flush=True)
    err = stderr.read().decode().strip()
    if err:
        print("\nSTDERR:\n", err)
    print()

print("Step 1: Installing nvidia-driver-580-server and utils...")
run_sudo("DEBIAN_FRONTEND=noninteractive apt-get install -y nvidia-driver-580-server nvidia-utils-580-server")

ssh.close()
