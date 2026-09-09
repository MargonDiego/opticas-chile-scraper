import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.85", username="chalaox", password="asd123123", timeout=10)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(f'echo asd123123 | sudo -S docker exec -i $(docker ps -q -f name=postgres | head -n 1) psql -U opticas_user -d opticas_db -c "{cmd}"')
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out.strip():
        print(out.strip())
    if err.strip():
        print("ERR:", err.strip())

print("Snapshots grouped by product_id:")
run("""
SELECT product_id, count(1), min(price_normal), max(price_normal)
FROM price_snapshots 
GROUP BY product_id 
HAVING count(1) > 1 
LIMIT 10;
""")

print("Inspect 1 product snapshots:")
run("""
SELECT id, product_id, price_normal, price_discount, is_in_stock, scraped_at 
FROM price_snapshots 
WHERE product_id = (SELECT product_id FROM price_snapshots GROUP BY product_id HAVING count(1) > 1 LIMIT 1);
""")
ssh.close()





