import paramiko

HOST = "192.168.1.85"
PORT = 22
USER = "chalaox"
PASS = "asd123123"

def run_remote():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS)

    print("Connected to homelab.")
    stdin, stdout, stderr = ssh.exec_command('docker ps')
    print("Running containers:\n", stdout.read().decode())

    # Find the db container name
    stdin, stdout, stderr = ssh.exec_command("docker ps --filter 'name=postgres-wktecurp' --format '{{.Names}}'")
    db_container = stdout.read().decode().strip()
    if not db_container:
        stdin, stdout, stderr = ssh.exec_command("docker ps --filter 'ancestor=pgvector/pgvector:pg16' --format '{{.Names}}'")
        db_container = stdout.read().decode().strip()
    print(f"Detected DB container: {db_container}")

    if db_container:
        # 1. Check count before
        stdin, stdout, stderr = ssh.exec_command(
            f'docker exec {db_container} psql -U opticas_user -d opticas_db -c "SELECT count(*) FROM price_snapshots;"'
        )
        print("Snapshots count before:\n", stdout.read().decode())

        # 2. Run deduplication query
        dedup_sql = """
        DELETE FROM price_snapshots a USING price_snapshots b
        WHERE a.product_id = b.product_id
          AND date(a.scraped_at) = date(b.scraped_at)
          AND a.id < b.id;
        """
        cmd = f'docker exec {db_container} psql -U opticas_user -d opticas_db -c "{dedup_sql}"'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("Deduplication result:\n", stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print("Deduplication stderr:\n", err)

        # 3. Check count after
        stdin, stdout, stderr = ssh.exec_command(
            f'docker exec {db_container} psql -U opticas_user -d opticas_db -c "SELECT count(*) FROM price_snapshots;"'
        )
        print("Snapshots count after:\n", stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    run_remote()
