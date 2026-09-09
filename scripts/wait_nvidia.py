import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.85", username="chalaox", password="asd123123", timeout=10)

print("Waiting for background apt/dkms to complete...")
while True:
    stdin, stdout, stderr = ssh.exec_command("pgrep -f 'apt-get|dpkg' || true")
    pids = stdout.read().decode().strip()
    if not pids:
        print("apt/dpkg process finished!")
        break
    print(f"Still running (PIDs: {pids})... waiting 5s")
    time.sleep(5)

stdin, stdout, stderr = ssh.exec_command('echo asd123123 | sudo -S modprobe nvidia || true')
print("Modprobe output:\n", stdout.read().decode())
print("Modprobe err:\n", stderr.read().decode())

stdin, stdout, stderr = ssh.exec_command('nvidia-smi || true')
print("nvidia-smi:\n", stdout.read().decode())

ssh.close()
