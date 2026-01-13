import matplotlib
# Force Matplotlib à ne pas utiliser d'interface graphique
# Cela empêche le conflit avec la fenêtre de sélection de fichier
matplotlib.use('Agg') 

import matplotlib.pyplot as plt
import re, csv, os, markdown, base64, io
import tkinter as tk
from tkinter import filedialog
from collections import Counter

def analyser_trafic():
    # --- 1. SÉLECTION FICHIER ---
    root = tk.Tk()
    root.withdraw() # Cache la fenêtre principale
    # Force la fenêtre de dialogue à apparaître au premier plan
    root.attributes('-topmost', True) 
    
    fichier = filedialog.askopenfilename(title="Sélectionnez le fichier tcpdump")
    
    # On détruit l'instance Tkinter immédiatement après la sélection pour libérer la mémoire
    root.destroy() 
    
    if not fichier: return
    print(f"Analyse de {os.path.basename(fichier)}...")
    
    nom_base = os.path.splitext(fichier)[0]

    # --- 2. ANALYSE ---
    paquets, stats = [], {'flags': Counter(), 'src': Counter(), 'srv': Counter(), 'menaces': Counter()}
    regex = re.compile(r"(\S+) IP ([\w\.-]+) > ([\w\.-]+): Flags \[(.*?)\]")

    try:
        with open(fichier, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = regex.search(line)
                if not match: continue
                heure, src, dst, flags = match.groups()
                flags = flags.strip()
                
                # Nettoyage IPs et Ports
                def get_srv(x): p=x.rsplit('.',1); return (p[0], p[1]) if len(p)>1 and not p[1].isdigit() else (x, "")
                s_ip, s_srv = get_srv(src); d_ip, d_srv = get_srv(dst)
                service = d_srv or s_srv

                # Logique Menaces
                verdict = "Normal"
                if 'S' in flags and '.' not in flags: verdict = "DDOS/SYN Flood"
                elif 'R' in flags: verdict = "Rejet (RST)"
                elif service in ['ssh', 'telnet', 'rdp']: verdict = f"Admin ({service})"

                # Stockage
                paquets.append([heure, s_ip, d_ip, service, flags, verdict])
                stats['flags'][flags] += 1; stats['src'][s_ip] += 1
                if service: stats['srv'][service] += 1
                if verdict != "Normal": 
                    src_net = s_ip.rsplit('.', 1)[0] + ".*" if re.match(r"^\d", s_ip) else s_ip
                    stats['menaces'][(src_net, d_ip, verdict)] += 1
    except Exception as e:
        print(f"Erreur lecture fichier : {e}")
        return

    # --- 3. EXPORT EXCEL (CSV) ---
    try:
        csv_path = f"{nom_base}_donnees.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Heure", "Source", "Destination", "Service", "Flags", "Verdict"])
            writer.writerows(paquets)
        print(f"-> Excel/CSV généré : {csv_path}")
    except Exception as e: print(f"Erreur CSV : {e}")

    # --- 4. EXPORT VISUEL ---
    def plot_b64(data, title, kind='bar'):
        if not data: return ""
        # On crée une nouvelle figure pour éviter les conflits
        fig = plt.figure(figsize=(6, 3))
        plt.style.use('ggplot')
        items = data.most_common(10)
        x, y = [str(k) for k,v in items], [v for k,v in items]
        
        if kind == 'pie': plt.pie(y, labels=x, autopct='%1.1f%%')
        else: plt.barh(x, y, color='#4a90e2'); plt.gca().invert_yaxis()
        
        plt.title(title); plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig) # Fermeture de la figure
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def md_table(headers, data):
        rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"]*len(headers)) + " |"]
        for k, v in data.most_common(10):
            cols = [str(x) for x in k] if isinstance(k, tuple) else [str(k)]
            rows.append("| " + " | ".join(cols + [str(v)]) + " |")
        return "\n".join(rows) if data else "_Aucune donnée_"

    # Génération graphiques
    img_flags = plot_b64(stats['flags'], "Répartition Flags", 'pie')
    img_srv = plot_b64(stats['srv'], "Top Services")
    img_src = plot_b64(stats['src'], "Top Sources")

    md_content = f"""
# Rapport d'Analyse Réseau
*Fichier source : {os.path.basename(fichier)}*

## 📊 Visualisation
| Flags TCP | Top Services |
| :---: | :---: |
| ![][1] | ![][2] |

![][3]

## 🚨 Menaces Détectées
{md_table(['Source', 'Cible', 'Type', 'Qté'], stats['menaces'])}

## 🚩 Détail Flags
{md_table(['Flag', 'Qté'], stats['flags'])}

[1]: data:image/png;base64,{img_flags}
[2]: data:image/png;base64,{img_srv}
[3]: data:image/png;base64,{img_src}
    """

    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Rapport</title>
    <style>body{{font-family:Segoe UI,sans-serif;max-width:900px;margin:auto;padding:20px;background:#f9f9f9}} 
    h1,h2{{color:#2c3e50}} table{{border-collapse:collapse;width:100%;margin-bottom:20px;background:white}} 
    th,td{{border:1px solid #ddd;padding:10px}} th{{background:#3498db;color:white}} img{{max-width:100%}}</style>
    </head><body>{markdown.markdown(md_content, extensions=['tables'])}</body></html>"""

    html_path = f"{nom_base}_rapport.html"
    with open(html_path, "w", encoding="utf-8") as f: f.write(html)
    print(f"-> Rapport HTML généré : {html_path}")
    try: os.startfile(html_path)
    except: pass

if __name__ == "__main__": analyser_trafic()