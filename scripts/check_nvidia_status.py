import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.85", username="chalaox", password="asd123123", timeout=10)

def run(cmd):
    print(f"=== {cmd} ===")
    stdin, stdout, stderr = ssh.exec_command(f'echo asd123123 | sudo -S {cmd}')
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        print(f"STDOUT:\n{out}")
    if err:
        print(f"STDERR:\n{err}")
    print()

run("modprobe nvidia")
run("nvidia-smi")
run("dmesg | grep -i nvidia | tail -n 20")

ssh.close()
