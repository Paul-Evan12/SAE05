import matplotlib
# --- CONFIGURATION MATPLOTLIB ---
# On force l'utilisation du backend 'Agg'.
# Pourquoi ? Par défaut, Matplotlib cherche à ouvrir une fenêtre pour afficher les graphiques.
# Comme on utilise Tkinter juste avant, cela crée souvent des conflits ou des plantages.
# 'Agg' permet de générer des images en mémoire (RAM) sans jamais les afficher à l'écran.
matplotlib.use('Agg') 

import matplotlib.pyplot as plt # Pour créer les graphiques (visuels)
import re       # "Regular Expressions" : Pour découper le texte complexe des logs
import csv      # Pour créer le fichier Excel à la fin
import os       # Pour manipuler les chemins de fichiers (Windows/Linux)
import markdown # Convertit le texte formaté (*gras*, # titres) en code HTML
import base64   # Convertit une image en une longue chaîne de texte (pour l'incruster dans le HTML)
import io       # Permet de gérer des fichiers virtuels dans la mémoire RAM (très rapide)
import tkinter as tk            # Bibliothèque d'interface graphique
from tkinter import filedialog  # Module spécifique pour la boîte de dialogue "Ouvrir"
from collections import Counter # Outil statistique pour compter (ex: combien de fois l'IP X apparaît)

def analyser_trafic():


    # ÉTAPE 1 : INTERFACE DE SÉLECTION DE FICHIER
    
    # On crée une instance Tkinter (la base de la fenêtre)
    root = tk.Tk()
    
    # On cache la fenêtre principale (le petit carré gris vide inutile)
    # On ne veut voir QUE la boîte de dialogue.
    root.withdraw() 
    
    # On force la fenêtre à passer au premier plan (devant le navigateur ou l'éditeur de code)
    root.attributes('-topmost', True) 
    
    # Ouvre l'explorateur et attend que l'utilisateur choisisse un fichier
    fichier = filedialog.askopenfilename(title="Sélectionnez le fichier tcpdump (.txt ou .log)")
    
    # On détruit l'interface graphique pour libérer la mémoire du PC
    root.destroy() 
    
    # Sécurité : Si l'utilisateur clique sur "Annuler", fichier est vide, donc on arrête tout.
    if not fichier: return
    
    print(f"Démarrage de l'analyse sur : {os.path.basename(fichier)}...")
    nom_base = os.path.splitext(fichier)[0] # On garde le nom sans l'extension pour les sauvegardes


    # ÉTAPE 2 : LE CŒUR DE L'ANALYSE (PARSING)
    
    paquets = []
    # Initialisation des compteurs pour les statistiques
    stats = {'flags': Counter(), 'src': Counter(), 'srv': Counter(), 'menaces': Counter()}

    # EXPLICATION DE LA REGEX (Le filtre de lecture)
    # r"..." signifie "raw string" (pour éviter les conflits avec les caractères spéciaux)
    # (\S+)       : Groupe 1 -> Capture le Timestamp (l'heure) au début de la ligne.
    # IP          : Cherche le mot exact "IP".
    # ([\w\.-]+)  : Groupe 2 -> Capture l'IP Source (lettres, chiffres, points).
    # >           : Le séparateur visuel.
    # ([\w\.-]+)  : Groupe 3 -> Capture l'IP Destination.
    # : (.*)      : Groupe 4 -> Capture TOUT LE RESTE de la ligne après les deux points.
    #               C'est crucial car cela capture aussi bien les "Flags [S]" du TCP 
    #               que les requêtes "A? google.com" du DNS.
    regex = re.compile(r"(\S+) IP ([\w\.-]+) > ([\w\.-]+): (.*)")

    try:
        with open(fichier, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # On teste si la ligne correspond à notre format tcpdump
                match = regex.search(line)
                if not match: continue # Si la ligne est bizarre/vide, on passe à la suivante
                
                # Extraction des données brutes
                heure, src_raw, dst_raw, info_brute = match.groups()
                
                # --- A. Extraction Spécifique des Flags TCP ---
                # On cherche si le motif "Flags [quelquechose]" existe dans la fin de la ligne.
                # Si oui, c'est du TCP. Si non, c'est probablement de l'UDP ou du DNS.
                match_flags = re.search(r"Flags \[(.*?)\]", info_brute)
                if match_flags:
                    flags = match_flags.group(1).strip() # Ex: "S" ou "S." ou "R"
                else:
                    flags = "" # Pas de flags (contexte UDP/ICMP/DNS)

                # --- B. Nettoyage des IPs et Ports ---
                # Les logs mélangent souvent IP et Port (ex: 192.168.1.5.80 ou 10.0.0.1.domain)
                def split_srv(x): 
                    # On coupe au dernier point
                    p = x.rsplit('.', 1)
                    # Si la partie après le point n'est pas un chiffre (ex: 'ssh', 'domain'), on la garde comme Service.
                    # Sinon, on considère que c'est une partie de l'IP ou un port numérique.
                    return (p[0], p[1]) if len(p) > 1 and not p[1].isdigit() else (x, "")
                
                src_ip, src_srv = split_srv(src_raw)
                dst_ip, dst_srv = split_srv(dst_raw)
                
                # Le service est défini par la destination (cible), sinon la source.
                service = dst_srv or src_srv 

                # ÉTAPE 3 : DÉTECTION DES MENACES (MOTEUR DE RÈGLES)
                verdict = "Normal"
                
                # --- Règle 1 : Menaces TCP (Basées sur les Flags) ---
                if flags:
                    # SYN sans ACK (.) = Tentative de connexion unilatérale
                    if 'S' in flags and '.' not in flags: verdict = "SYN Scan/Flood"
                    # RST = Connexion rejetée (Port fermé ou Firewall)
                    elif 'R' in flags: verdict = "Rejet (RST)"
                    # Administration à distance en clair ou sensible
                    elif service in ['ssh', 'telnet', 'rdp']: verdict = f"Admin Distant ({service})"
                
                # --- Règle 2 : Menaces DNS (Basées sur le contenu) ---
                # On vérifie si c'est du trafic DNS (Port 53 ou nom de service 'domain')
                is_dns = 'domain' in str(service) or '53' in str(service)
                
                if is_dns:
                    # 2.1 Zone Transfer (AXFR/IXFR)
                    # Un attaquant demande au serveur DNS de lui donner TOUTE sa liste de domaines.
                    # C'est une fuite d'information critique.
                    if 'AXFR' in info_brute or 'IXFR' in info_brute:
                        verdict = "DNS Zone Transfer (Critique)"
                    
                    # 2.2 DNS Tunneling / Exfiltration
                    # Le DNS sert normalement à résoudre des noms courts (google.com).
                    # Si la requête est très longue (>200 caractères), c'est souvent un attaquant 
                    # qui cache des données volées DANS la requête DNS pour contourner le firewall.
                    elif len(info_brute) > 200: 
                        verdict = "DNS Tunneling / Exfiltration"
                    
                    # 2.3 Botnet / DGA (NXDomain)
                    # Si on voit beaucoup de réponses "NXDomain" (Domaine inexistant),
                    # c'est souvent un virus qui essaie de contacter des serveurs de commande aléatoires.
                    elif 'NXDomain' in info_brute or 'NXDOMAIN' in info_brute:
                        verdict = "DNS NXDomain (Suspect)"
                    
                    # Si c'est juste une requête DNS normale
                    elif verdict == "Normal":
                        verdict = "Requête DNS"

                # --- Stockage ---
                # Pour l'affichage, si on n'a pas de flags TCP, on affiche un bout de l'info brute (ex: la requête DNS)
                affichage_info = flags if flags else (info_brute[:30] + "..." if len(info_brute)>30 else info_brute)
                
                paquets.append([heure, src_ip, dst_ip, service, affichage_info, verdict])
                
                # Mise à jour des statistiques
                stats['flags'][flags if flags else "UDP/Autre"] += 1
                stats['src'][src_ip] += 1
                if service: stats['srv'][service] += 1
                
                # Si une menace est détectée (on exclut le trafic normal et les simples requêtes DNS)
                if verdict not in ["Normal", "Requête DNS"]: 
                    # On masque le dernier chiffre de l'IP (ex: 192.168.1.12 -> 192.168.1.*)
                    # Cela permet de regrouper les attaques venant d'un même sous-réseau.
                    src_net = src_ip.rsplit('.', 1)[0] + ".*" if re.match(r"^\d", src_ip) else src_ip
                    stats['menaces'][(src_net, dst_ip, verdict)] += 1

    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {e}")
        return

    # ÉTAPE 4 : GÉNÉRATION DES VISUELS (Encoding Base64)
    
    # Cette fonction transforme un graphique Matplotlib en texte (Base64)
    # pour pouvoir l'écrire directement dans le fichier HTML.
    def plot_to_b64(data, title, chart_type='bar'):
        if not data: return ""
        fig = plt.figure(figsize=(6, 3))
        plt.style.use('ggplot') # Style "R" ou "Excel" moderne
        
        # On ne garde que le Top 10 pour la lisibilité
        top_items = data.most_common(10)
        labels = [str(k) for k, v in top_items]
        values = [v for k, v in top_items]

        if chart_type == 'pie':
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        else:
            plt.barh(labels, values, color='#4a90e2')
            plt.gca().invert_yaxis() # Met le plus grand en haut

        plt.title(title); plt.tight_layout()
        
        # Sauvegarde en RAM (buffer)
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig) # Ferme la figure pour libérer la mémoire
        
        # Retourne la chaîne encodée
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    print("Génération des graphiques...")
    img_flags = plot_to_b64(stats['flags'], "Répartition Protocoles/Flags", 'pie')
    img_srv = plot_to_b64(stats['srv'], "Top Services")
    img_src = plot_to_b64(stats['src'], "Top Sources IP")


    # ÉTAPE 5 : CRÉATION DU RAPPORT HTML

    
    # Fonction pour créer un tableau au format Markdown
    def md_table(headers, data_counter):
        # Création de l'entête | Col1 | Col2 |
        tbl = "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n"
        # Remplissage des lignes
        for key, count in data_counter.most_common(15):
            cols = list(key) if isinstance(key, tuple) else [key]
            cols = [str(c) for c in cols] + [str(count)]
            tbl += "| " + " | ".join(cols) + " |\n"
        return tbl

    # Contenu du rapport en Markdown (Texte simple enrichi)
    md_content = f"""
# Rapport de Sécurité Réseau
*Fichier analysé : {os.path.basename(fichier)}*

## 📊 Synthèse Visuelle
| Distribution du Trafic | Top Services |
| :---: | :---: |
| ![][img1] | ![][img2] |

### Sources les plus actives
![][img3]

## 🚨 ALERTES DE SÉCURITÉ (DNS & TCP)
{md_table(['Source', 'Cible', 'Type d\'Alerte', 'Volume'], stats['menaces'])}

## ℹ️ Détails Techniques (Flags/Info)
{md_table(['Type', 'Volume'], stats['flags'])}

[img1]: data:image/png;base64,{img_flags}
[img2]: data:image/png;base64,{img_srv}
[img3]: data:image/png;base64,{img_src}
    """

    # Template HTML final avec CSS (Mise en page)
    # On injecte le résultat de la conversion Markdown -> HTML au milieu
    html_template = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>Rapport {nom_base}</title>
    <style>
        body{{font-family:'Segoe UI',sans-serif;max-width:900px;margin:auto;padding:20px;background:#f4f6f8;color:#333}}
        h1{{color:#2c3e50;border-bottom:2px solid #3498db;padding-bottom:10px}}
        table{{width:100%;border-collapse:collapse;background:white;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}}
        th,td{{border:1px solid #ddd;padding:10px;text-align:left}} 
        th{{background:#3498db;color:white}} 
        img{{max-width:100%;height:auto}}
    </style>
    </head><body>{markdown.markdown(md_content, extensions=['tables'])}</body></html>"""

    # Écriture du fichier HTML sur le disque
    rapport_path = f"{nom_base}_rapport.html"
    with open(rapport_path, 'w', encoding='utf-8') as f: f.write(html_template)
    print(f"-> Rapport HTML généré : {rapport_path}")
    
    # Export des données brutes en CSV (pour Excel)
    try:
        with open(f"{nom_base}_donnees.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Heure", "Source", "Dest", "Service", "Info/Flags", "Verdict"])
            writer.writerows(paquets)
        print("-> Fichier CSV généré.")
    except Exception as e: print(f"Erreur lors de la création du CSV: {e}")

    # On essaie d'ouvrir le rapport automatiquement dans le navigateur
    try: os.startfile(rapport_path)
    except: pass

if __name__ == "__main__":
    analyser_trafic()