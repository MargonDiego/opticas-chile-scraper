import httpx

headers = {
    'X-API-Key': 'dB57RDrRgEPNO6VK9AGUZoNwWANPBlrGgTOqk1D28OUqy5OhetekKsqfKDDAdoHoB7BowKMniCR4Guoiqxd2uNJyiKPyXKMS4AtgmC87FbzyJmPGeG7wJDFiRfwZp6Gj'
}

r = httpx.get('http://192.168.1.85:8008/api/products?limit=200', headers=headers)
products = r.json()

stores = {}
for p in products:
    st = p.get('store', 'unknown')
    if st not in stores:
        stores[st] = {'total': 0, 'with_img': 0, 'sample_img': None, 'samples': []}
    stores[st]['total'] += 1
    img = p.get('image_url')
    if img:
        stores[st]['with_img'] += 1
        if len(stores[st]['samples']) < 3:
            stores[st]['samples'].append((p.get('model_name'), img))

print(f"{'STORE':<18} | {'TOTAL':<6} | {'WITH IMAGE':<10} | SAMPLES")
print("-" * 80)
for st, d in stores.items():
    print(f"{st:<18} | {d['total']:<6} | {d['with_img']:<10} |")
    for name, url in d['samples']:
        print(f"   -> {name}: {url}")
