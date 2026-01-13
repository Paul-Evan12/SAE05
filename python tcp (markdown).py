import matplotlib
# On force Matplotlib à utiliser le backend 'Agg' (non-interactif).
# C'est quand on utilise Matplotlib avec Tkinter ou pour générer des images sans les afficher à l'écran.
# Si on ne met pas ça, le script risque de planter ou d'ouvrir des fenêtres vides.
matplotlib.use('Agg') 

import matplotlib.pyplot as plt
import re, csv, os, markdown, base64, io
import tkinter as tk
from tkinter import filedialog
from collections import Counter

def analyser_trafic():
    # =========================================================================
    # ÉTAPE 1 : SÉLECTION DU FICHIER (Traitement de l'interface graphique)
    # =========================================================================
    
    # On initialise Tkinter, qui est la bibliothèque graphique standard de Python.
    root = tk.Tk()
    
    # root.withdraw() : Cache la petite fenêtre vide principale de Tkinter. 
    # On ne veut voir QUE la boîte de dialogue de sélection de fichier.
    root.withdraw() 
    
    # root.attributes('-topmost', True) : Force la fenêtre de dialogue à s'afficher 
    # au-dessus de toutes les autres fenêtres (navigateur, éditeur de code, etc.).
    # C'est important pour que l'utilisateur ne cherche pas la fenêtre partout.
    root.attributes('-topmost', True) 
    
    # Ouvre l'explorateur de fichiers et retourne le chemin complet du fichier choisi.
    fichier = filedialog.askopenfilename(title="Sélectionnez le fichier tcpdump (.txt ou .log)")
    
    # Une fois le fichier choisi (ou annulé), on détruit l'instance Tkinter 
    # pour libérer la mémoire et fermer proprement le processus graphique.
    root.destroy() 
    
    # Si l'utilisateur a cliqué sur "Annuler", la variable 'fichier' est vide, on arrête tout.
    if not fichier: return
    
    print(f"Analyse en cours de : {os.path.basename(fichier)}...")
    nom_base = os.path.splitext(fichier)[0]

    # ÉTAPE 2 : TRAITEMENT DES DONNÉES (Parsing & Logique)
    
    # Initialisation des structures de données
    paquets = []
    # Counter est un outil génial qui compte automatiquement les éléments qu'on lui donne.
    # Ex: stats['flags'] va ressembler à {'S': 150, '.': 400, 'R': 10}
    stats = {'flags': Counter(), 'src': Counter(), 'srv': Counter(), 'menaces': Counter()}

    # REGEX (Expression Régulière) : C'est le filtre qui va lire le fichier ligne par ligne.
    # (\S+)       : Capture le premier bloc de texte (Timestamp/Heure)
    # IP          : Cherche le mot littéral "IP"
    # ([\w\.-]+)  : Capture l'IP Source (lettres, chiffres, points, tirets)
    # >           : Séparateur visuel dans les logs tcpdump
    # ([\w\.-]+)  : Capture l'IP Destination
    # Flags \[(.*?)] : Capture tout ce qui se trouve à l'intérieur des crochets des Flags
    regex = re.compile(r"(\S+) IP ([\w\.-]+) > ([\w\.-]+): Flags \[(.*?)\]")

    # Ouverture du fichier en mode lecture ('r')
    # errors='ignore' : Permet de ne pas planter si le fichier contient des caractères bizarres.
    with open(fichier, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # On applique la regex sur la ligne actuelle
            match = regex.search(line)
            
            # Si la ligne ne correspond pas au format attendu (ex: ligne vide ou entête), on passe à la suivante.
            if not match: continue
            
            # On récupère les morceaux capturés par les parenthèses de la regex
            heure, src_raw, dst_raw, flags = match.groups()
            flags = flags.strip() # Enlève les espaces inutiles

            # Traitement des IPs et Services 
            # Les logs tcpdump affichent souvent : "192.168.1.15.ssh" ou "10.0.0.1.443"
            # Cette fonction sépare l'IP (192.168.1.15) du Port/Service (ssh).
            def split_srv(x): 
                # rsplit('.', 1) coupe la chaîne au DERNIER point rencontré.
                p = x.rsplit('.', 1)
                # Si on a bien coupé en deux et que la partie après le point n'est pas juste un chiffre
                # (ou si c'est un chiffre, c'est considéré comme un port), on retourne le couple (IP, Port).
                # Ici, la logique garde le port s'il n'est PAS un chiffre (ex: 'ssh'), 
                # sinon on considère que c'est un port numérique standard.
                return (p[0], p[1]) if len(p) > 1 and not p[1].isdigit() else (x, "")
            
            src_ip, src_srv = split_srv(src_raw)
            dst_ip, dst_srv = split_srv(dst_raw)
            
            # On priorise le service de destination, sinon celui de la source
            service = dst_srv or src_srv 

            # --- Logique de Détection des Menaces ---
            verdict = "Normal"
            # Si le Flag contient 'S' (SYN) mais pas '.' (ACK), c'est une demande de connexion pure.
            # En grand nombre, c'est caractéristique d'un SYN Flood ou d'un Scan.
            if 'S' in flags and '.' not in flags: verdict = "SYN (Scan/Flood)"
            # Si le Flag contient 'R' (RST), la connexion a été rejetée brutalement.
            elif 'R' in flags: verdict = "Rejet (RST)"
            # Si le service détecté est sensible (administration à distance).
            elif service in ['ssh', 'telnet', 'rdp']: verdict = f"Admin Distant ({service})"

            # --- Stockage des résultats ---
            paquets.append([heure, src_ip, dst_ip, service, flags, verdict])
            
            stats['flags'][flags] += 1
            stats['src'][src_ip] += 1
            if service: stats['srv'][service] += 1
            
            # Si ce n'est pas "Normal", on l'ajoute aux menaces
            if verdict != "Normal": 
                # On masque le dernier octet de l'IP pour regrouper par sous-réseau (ex: 192.168.1.*)
                # Cela rend le tableau des menaces plus lisible.
                src_net = src_ip.rsplit('.', 1)[0] + ".*" if re.match(r"^\d", src_ip) else src_ip
                stats['menaces'][(src_net, dst_ip, verdict)] += 1


    # ÉTAPE 3 : GÉNÉRATION DES GRAPHIQUES (Matplotlib)
    
    # Fonction utilitaire pour convertir un graphique Matplotlib en image Base64.
    # Cela permet d'incruster l'image directement dans le HTML (pas de fichier .png externe).
    def plot_to_b64(data, title, chart_type='bar'):
        if not data: return ""
        # Création de la figure
        fig = plt.figure(figsize=(6, 3))
        plt.style.use('ggplot') # Style visuel propre
        
        # On ne prend que le Top 10 pour éviter les graphiques illisibles
        top_items = data.most_common(10)
        labels = [str(k) for k, v in top_items]
        values = [v for k, v in top_items]

        if chart_type == 'pie':
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        else:
            plt.barh(labels, values, color='#4a90e2')
            plt.gca().invert_yaxis() # Inverse l'axe Y pour avoir le plus grand en haut

        plt.title(title)
        plt.tight_layout()
        
        # Sauvegarde en mémoire tampon (RAM) au lieu d'un fichier disque
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig) # Important : ferme la figure pour libérer la mémoire
        
        # Encodage en Base64 (texte) pour le HTML
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    # Génération des 3 graphiques
    img_flags = plot_to_b64(stats['flags'], "Répartition Flags TCP", 'pie')
    img_srv = plot_to_b64(stats['srv'], "Top Services")
    img_src = plot_to_b64(stats['src'], "Top Sources IP")

    # =========================================================================
    # ÉTAPE 4 : GÉNÉRATION DU RAPPORT (Markdown -> HTML)
    # =========================================================================
    
    # Fonction pour créer un tableau Markdown proprement
    def md_table(headers, data_counter):
        # Création de l'entête du tableau Markdown
        tbl = "| " + " | ".join(headers) + " |\n" 
        tbl += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        # Remplissage des lignes
        for key, count in data_counter.most_common(15):
            # Si la clé est un tuple (Source, Dest, Verdict), on la décompose
            cols = list(key) if isinstance(key, tuple) else [key]
            cols = [str(c) for c in cols] + [str(count)]
            tbl += "| " + " | ".join(cols) + " |\n"
        return tbl

    # Construction du contenu du rapport en syntaxe Markdown
    # C'est beaucoup plus lisible que de concaténer des chaînes HTML
    md_content = f"""
# Rapport d'Analyse Réseau
*Fichier analysé : {os.path.basename(fichier)}*

## 📊 Visualisation des Données
| Statut des Connexions (Flags) | Services les plus demandés |
| :---: | :---: |
| ![][img1] | ![][img2] |

### Sources les plus actives
![][img3]

## 🚨 Menaces et Anomalies Détectées
{md_table(['Source (Réseau)', 'Cible', 'Type de Menace', 'Quantité'], stats['menaces'])}

## 🚩 Détails techniques des Flags
{md_table(['Flag TCP', 'Quantité'], stats['flags'])}

[img1]: data:image/png;base64,{img_flags}
[img2]: data:image/png;base64,{img_srv}
[img3]: data:image/png;base64,{img_src}
    """

    # Conversion du Markdown en HTML complet avec du CSS pour faire joli
    html_template = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Rapport {nom_base}</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: auto; padding: 20px; background-color: #f4f6f8; color: #333; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #2980b9; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; background: white; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #3498db; color: white; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        {markdown.markdown(md_content, extensions=['tables'])}
    </body>
    </html>
    """

    # Écriture du fichier HTML
    rapport_path = f"{nom_base}_rapport.html"
    with open(rapport_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"-> Rapport HTML généré avec succès : {rapport_path}")
    
    # Export CSV
    try:
        with open(f"{nom_base}_donnees.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Heure", "Source", "Dest", "Service", "Flags", "Verdict"])
            writer.writerows(paquets)
        print("-> Export CSV généré.")
    except Exception as e:
        print(f"Erreur CSV: {e}")

    # Tentative d'ouverture automatique du rapport
    try: os.startfile(rapport_path)
    except: pass

if __name__ == "__main__":
    analyser_trafic()