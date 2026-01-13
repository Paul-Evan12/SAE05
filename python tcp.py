import re, csv, os, json, tkinter as tk
from tkinter import filedialog
from collections import Counter

def analyser_trafic():
    # --- 1. SÉLECTION FICHIER ---
    root = tk.Tk(); root.withdraw()
    fichier = filedialog.askopenfilename(title="Fichier tcpdump")
    if not fichier: return
    print(f"Analyse de {os.path.basename(fichier)}...")

    paquets, stats = [], {'flags': Counter(), 'src': Counter(), 'srv': Counter(), 'menaces': Counter()}
    # Regex standard tcpdump (timestamp IP src > dst: Flags [flags])
    regex = re.compile(r"(\S+) IP ([\w\.-]+) > ([\w\.-]+): Flags \[(.*?)\]")

    with open(fichier, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = regex.search(line)
            if not match: continue
            
            heure, src_raw, dst_raw, flags = match.groups()
            flags = flags.strip()

            # Extraction port service (seulement si lettres)
            def split_srv(x): 
                p = x.rsplit('.', 1)
                return (p[0], p[1]) if len(p) > 1 and not p[1].isdigit() else (x, "")
            
            src_ip, src_srv = split_srv(src_raw)
            dst_ip, dst_srv = split_srv(dst_raw)
            service = dst_srv or src_srv # On garde le nom du service s'il existe

            # Détection Menaces
            verdict = "Normal"
            if 'S' in flags and '.' not in flags: verdict = "SYN Flood (DOS)"
            elif 'R' in flags: verdict = "Rejet (RST)"
            elif service in ['ssh', 'telnet', 'rdp']: verdict = f"Admin Distant ({service})"

            # Stockage & Stats
            paquets.append([heure, src_ip, dst_ip, service, flags, verdict])
            stats['flags'][flags] += 1
            stats['src'][src_ip] += 1
            if service: stats['srv'][service] += 1
            if verdict != "Normal": 
                # Regroupement des menaces par sous-réseau source
                src_net = src_ip.rsplit('.', 1)[0] + ".*" if re.match(r"^\d", src_ip) else src_ip
                stats['menaces'][(src_net, dst_ip, verdict)] += 1

    # --- 2. EXPORTS ---
    nom_base = os.path.splitext(fichier)[0]
    
    # CSV
    try:
        with open(f"{nom_base}_analyse.csv", 'w', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Heure", "Source", "Dest", "Service", "Flags", "Verdict"])
            writer.writerows(paquets)
        print("-> CSV généré.")
    except Exception as e: print(f"Err CSV: {e}")

    # HTML Generator Helpers
    def table_rows(data, is_dict=False):
        rows = ""
        items = data.most_common(10) if is_dict else data
        for k, v in items:
            if is_dict: # Traitement pour stats
                val_col = f"<td>{k}</td><td class='c'>{v}</td>"
                if isinstance(k, tuple): val_col = f"<td>{k[0]}</td><td>{k[1]}</td><td>{k[2]}</td><td class='c'>{v}</td>"
            else: # Traitement pour flags simple
                desc = ("SYN" if "S" in k else "") + ("ACK" if "." in k else "") + ("RST" if "R" in k else "")
                val_col = f"<td>{k}</td><td>{desc or 'Autre'}</td><td class='c'>{v}</td>"
            rows += f"<tr>{val_col}</tr>"
        return rows if rows else "<tr><td colspan='4'>Aucune donnée</td></tr>"

    js_data = {k: {'l': [x[0] for x in v.most_common(10)], 'd': [x[1] for x in v.most_common(10)]} 
               for k, v in stats.items() if k != 'menaces'}

    html = f"""<!DOCTYPE html><html lang='fr'><head><meta charset='UTF-8'><title>Rapport</title>
    <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
    <style>body{{font-family:sans-serif;background:#f0f2f5;padding:20px}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}} 
    .card{{background:#fff;padding:15px;border-radius:8px;box-shadow:0 2px 5px rgba(0,0,0,0.1)}} table{{width:100%;border-collapse:collapse}} 
    td,th{{padding:8px;border-bottom:1px solid #ddd}} th{{background:#007bff;color:#fff}} .c{{text-align:center}} .full{{grid-column:span 2}}</style></head>
    <body><h1>Rapport: {os.path.basename(fichier)}</h1><div class='grid'>
        <div class='card'><h3>Top Flags</h3><canvas id='c1'></canvas></div>
        <div class='card'><h3>Top Services (Nommés)</h3><canvas id='c2'></canvas></div>
        <div class='card full'><h3>🚨 Menaces Détectées</h3><table><tr><th>Source</th><th>Cible</th><th>Type</th><th>Qté</th></tr>{table_rows(stats['menaces'], True)}</table></div>
        <div class='card'><h3>Détail Flags</h3><table><tr><th>Flag</th><th>Desc</th><th>Qté</th></tr>{table_rows(stats['flags'].items())}</table></div>
        <div class='card'><h3>Top Sources</h3><canvas id='c3'></canvas></div>
    </div><script>
    const d = {json.dumps(js_data)};
    new Chart(document.getElementById('c1'), {{type:'pie', data:{{labels:d.flags.l, datasets:[{{data:d.flags.d, backgroundColor:['#36a2eb','#ff6384','#ffcd56','#4bc0c0']}}]}}}});
    new Chart(document.getElementById('c2'), {{type:'bar', indexAxis:'y', data:{{labels:d.srv.l, datasets:[{{label:'Paquets', data:d.srv.d, backgroundColor:'#9966ff'}}]}}}});
    new Chart(document.getElementById('c3'), {{type:'bar', data:{{labels:d.src.l, datasets:[{{label:'Source', data:d.src.d, backgroundColor:'#343a40'}}]}}}});
    </script></body></html>"""

    with open(f"{nom_base}_rapport.html", 'w', encoding='utf-8') as f: f.write(html)
    print("-> HTML généré.")
    try: os.startfile(f"{nom_base}_rapport.html")
    except: pass

if __name__ == "__main__": analyser_trafic()