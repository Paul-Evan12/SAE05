"""
Programme5.py
Génération d'un rapport HTML avec le module Markdown
Affiche les travaux 3 (tableau des séances R1.07) et 4 (graphique)

INSTALLATION REQUISE :
    pip install markdown
    ou
    python -m pip install markdown
"""

import markdown
from collections import Counter
import os
import base64

def lire_fichier_ics(nom_fichier):
    """Lit le contenu d'un fichier .ics"""
    try:
        with open(nom_fichier, 'r', encoding='utf-8') as fichier:
            contenu = fichier.read()
        return contenu
    except FileNotFoundError:
        print(f"Erreur : Le fichier {nom_fichier} n'a pas été trouvé.")
        return None
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {e}")
        return None


def extraire_evenements(contenu):
    """Sépare le contenu d'un fichier .ics en une liste d'événements individuels"""
    evenements = []
    lignes = contenu.split('\n')
    evenement_actuel = []
    dans_evenement = False
    
    for ligne in lignes:
        ligne = ligne.strip()
        
        if ligne == "BEGIN:VEVENT":
            dans_evenement = True
            evenement_actuel = [ligne]
        elif ligne == "END:VEVENT":
            evenement_actuel.append(ligne)
            evenements.append('\n'.join(evenement_actuel))
            evenement_actuel = []
            dans_evenement = False
        elif dans_evenement:
            evenement_actuel.append(ligne)
    
    return evenements


def extraire_propriete(contenu, identificateur):
    """Extrait la valeur d'une propriété à partir de son identificateur"""
    lignes = contenu.split('\n')
    for ligne in lignes:
        if ligne.startswith(identificateur + ':'):
            return ligne.split(':', 1)[1].strip()
    return "vide"


def convertir_date_ics_vers_csv(date_ics):
    """Convertit une date au format AAAAMMDDThhmmssZ vers JJ-MM-AAAA"""
    if not date_ics or date_ics == "vide" or len(date_ics) < 15:
        return "vide"
    
    annee = date_ics[0:4]
    mois = date_ics[4:6]
    jour = date_ics[6:8]
    
    return f"{jour}-{mois}-{annee}"


def calculer_duree(dtstart, dtend):
    """Calcule la durée entre deux dates"""
    if not dtstart or not dtend or dtstart == "vide" or dtend == "vide":
        return "vide"
    
    try:
        heure_debut = int(dtstart[9:11])
        min_debut = int(dtstart[11:13])
        heure_fin = int(dtend[9:11])
        min_fin = int(dtend[11:13])
        
        total_min_debut = heure_debut * 60 + min_debut
        total_min_fin = heure_fin * 60 + min_fin
        duree_minutes = total_min_fin - total_min_debut
        
        if duree_minutes < 0:
            duree_minutes += 24 * 60
        
        heures = duree_minutes // 60
        minutes = duree_minutes % 60
        
        return f"{heures:02d}:{minutes:02d}"
    except:
        return "vide"


def extraire_mois_de_date(date_str):
    """Extrait le mois d'une date au format JJ-MM-AAAA"""
    if not date_str or date_str == "vide":
        return None
    
    mois_dict = {
        '01': 'Janvier', '02': 'Février', '03': 'Mars', '04': 'Avril',
        '05': 'Mai', '06': 'Juin', '07': 'Juillet', '08': 'Août',
        '09': 'Septembre', '10': 'Octobre', '11': 'Novembre', '12': 'Décembre'
    }
    
    parties = date_str.split('-')
    if len(parties) >= 2:
        return mois_dict.get(parties[1], None)
    
    return None


def extraire_modalite(summary):
    """Extrait la modalité d'enseignement du SUMMARY"""
    if not summary or summary == "vide":
        return "vide"
    
    modalites = ['CM', 'TD', 'TP', 'Proj', 'DS']
    summary_upper = summary.upper()
    
    for modalite in modalites:
        if modalite in summary_upper:
            return modalite
    
    return "vide"


def extraire_groupes(description):
    """Extrait la liste des groupes de la DESCRIPTION"""
    if not description or description == "vide":
        return []
    
    lignes = []
    for sep in ['\\n', '\n', '\\r\\n']:
        if sep in description:
            lignes = [ligne.strip() for ligne in description.split(sep) if ligne.strip()]
            break
    
    if not lignes:
        lignes = [description.strip()]
    
    groupes = []
    
    for ligne in lignes:
        ligne_upper = ligne.upper()
        if 'RT' in ligne_upper or 'TP' in ligne_upper or any(f'-{lettre}' in ligne_upper or f'{lettre}1' in ligne_upper or f'{lettre}2' in ligne_upper for lettre in ['A', 'B', 'C', 'D']):
            groupes.append(ligne)
        elif ligne_upper.startswith('S') and len(ligne) <= 3:
            groupes.append(ligne)
    
    return groupes


def appartient_au_groupe(groupes_evenement, groupe_recherche):
    """Vérifie si le groupe recherché fait partie des groupes de l'événement"""
    if not groupes_evenement:
        return False
    
    groupe_recherche_clean = groupe_recherche.upper().strip()
    composants_recherche = [groupe_recherche_clean]
    
    if '-' in groupe_recherche_clean:
        parties = groupe_recherche_clean.split('-')
        composants_recherche.extend(parties)
    
    for groupe in groupes_evenement:
        groupe_clean = groupe.upper().strip()
        
        if groupe_clean == groupe_recherche_clean:
            return True
        
        for composant in composants_recherche:
            if composant in groupe_clean:
                return True
        
        if groupe_clean in groupe_recherche_clean:
            return True
    
    return False


def est_ressource_r107(summary):
    """Vérifie si l'intitulé correspond à la ressource R1.07"""
    if not summary or summary == "vide":
        return False
    
    summary_upper = summary.upper()
    variantes = ['R1.07', 'R107', 'R1-07', 'R 1.07']
    
    for variante in variantes:
        if variante in summary_upper:
            return True
    
    return False


def obtenir_seances_r107(nom_fichier, groupe_tp):
    """Obtient toutes les séances de R1.07 pour un groupe"""
    contenu = lire_fichier_ics(nom_fichier)
    if contenu is None:
        return []
    
    evenements = extraire_evenements(contenu)
    seances = []
    
    for evenement in evenements:
        summary = extraire_propriete(evenement, 'SUMMARY')
        description = extraire_propriete(evenement, 'DESCRIPTION')
        
        if est_ressource_r107(summary):
            groupes = extraire_groupes(description)
            
            if appartient_au_groupe(groupes, groupe_tp):
                dtstart = extraire_propriete(evenement, 'DTSTART')
                dtend = extraire_propriete(evenement, 'DTEND')
                
                date = convertir_date_ics_vers_csv(dtstart)
                duree = calculer_duree(dtstart, dtend)
                modalite = extraire_modalite(summary)
                
                seances.append({
                    'date': date,
                    'duree': duree,
                    'modalite': modalite
                })
    
    return seances


def compter_tp_par_mois(nom_fichier, groupe_tp):
    """Compte le nombre de séances de TP par mois"""
    contenu = lire_fichier_ics(nom_fichier)
    if contenu is None:
        return {}
    
    evenements = extraire_evenements(contenu)
    mois_list = []
    
    for evenement in evenements:
        summary = extraire_propriete(evenement, 'SUMMARY')
        description = extraire_propriete(evenement, 'DESCRIPTION')
        modalite = extraire_modalite(summary)
        
        if modalite == 'TP':
            groupes = extraire_groupes(description)
            
            if appartient_au_groupe(groupes, groupe_tp):
                dtstart = extraire_propriete(evenement, 'DTSTART')
                date = convertir_date_ics_vers_csv(dtstart)
                mois = extraire_mois_de_date(date)
                
                if mois:
                    mois_list.append(mois)
    
    return Counter(mois_list)


def generer_graphique_base64(compteur_mois):
    """Génère un graphique SVG et le convertit en base64"""
    
    mois_ordre = ['Septembre', 'Octobre', 'Novembre', 'Décembre']
    valeurs = [compteur_mois.get(mois, 0) for mois in mois_ordre]
    couleurs = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
    
    max_valeur = max(valeurs) if max(valeurs) > 0 else 5
    echelle_max = max_valeur + 2
    
    svg = '<svg width="900" height="500" xmlns="http://www.w3.org/2000/svg">'
    svg += '<rect width="900" height="500" fill="white"/>'
    
    # Grille
    for i in range(0, int(echelle_max) + 1):
        y = 400 - (i * 300 / echelle_max)
        svg += f'<line x1="100" y1="{y}" x2="850" y2="{y}" stroke="#e0e0e0" stroke-width="1"/>'
        svg += f'<text x="80" y="{y + 5}" text-anchor="end" font-size="14">{i}</text>'
    
    # Axes
    svg += '<line x1="100" y1="50" x2="100" y2="400" stroke="black" stroke-width="2"/>'
    svg += '<line x1="100" y1="400" x2="850" y2="400" stroke="black" stroke-width="2"/>'
    svg += '<text x="50" y="230" font-size="16" font-weight="bold" transform="rotate(-90 50 230)">Nombre de TP</text>'
    svg += '<text x="450" y="470" font-size="16" font-weight="bold" text-anchor="middle">Mois</text>'
    
    # Barres
    largeur_barre = 120
    espace = 180
    x_start = 150
    
    for i, (mois, valeur, couleur) in enumerate(zip(mois_ordre, valeurs, couleurs)):
        x = x_start + i * espace
        if echelle_max > 0:
            hauteur = (valeur * 300) / echelle_max
        else:
            hauteur = 0
        y = 400 - hauteur
        
        svg += f'<rect x="{x}" y="{y}" width="{largeur_barre}" height="{hauteur}" '
        svg += f'fill="{couleur}" stroke="black" stroke-width="2"/>'
        svg += f'<text x="{x + largeur_barre/2}" y="{y - 10}" text-anchor="middle" '
        svg += f'font-size="18" font-weight="bold">{int(valeur)}</text>'
        svg += f'<text x="{x + largeur_barre/2}" y="430" text-anchor="middle" '
        svg += f'font-size="14">{mois}</text>'
    
    svg += '</svg>'
    
    # Convertir en base64
    svg_bytes = svg.encode('utf-8')
    svg_base64 = base64.b64encode(svg_bytes).decode('utf-8')
    
    return f"data:image/svg+xml;base64,{svg_base64}"


def generer_contenu_markdown(groupe_tp, seances_r107, compteur_mois):
    """Génère le contenu en Markdown pour le rapport"""
    
    markdown_content = f"""# Rapport d'Analyse - SAÉ 1.5
## Traiter des Données avec Python

---

### Informations générales

- **Groupe de TP** : {groupe_tp}
- **Date de génération** : {obtenir_date_actuelle()}
- **Fichier source** : ADE_RT1_Septembre2025_Decembre2025.ics

---

## Travail 3 : Tableau des séances de R1.07

Cette section présente toutes les séances de la ressource **R1.07 (Informatique)** pour le groupe **{groupe_tp}**.

### Résultats

"""
    
    if seances_r107:
        markdown_content += f"Nombre total de séances : **{len(seances_r107)}**\n\n"
        markdown_content += "| Date | Durée | Modalité |\n"
        markdown_content += "|------|-------|----------|\n"
        
        for seance in seances_r107:
            markdown_content += f"| {seance['date']} | {seance['duree']} | {seance['modalite']} |\n"
    else:
        markdown_content += "*Aucune séance trouvée pour ce groupe.*\n"
    
    markdown_content += "\n---\n\n"
    markdown_content += "## Travail 4 : Graphique du nombre de séances de TP par mois\n\n"
    markdown_content += "Ce graphique présente le nombre de séances de **TP** (tous modules confondus) pour le groupe "
    markdown_content += f"**{groupe_tp}** sur la période septembre-décembre 2025.\n\n"
    
    # Statistiques
    mois_ordre = ['Septembre', 'Octobre', 'Novembre', 'Décembre']
    total_tp = sum(compteur_mois.get(mois, 0) for mois in mois_ordre)
    
    markdown_content += "### Statistiques\n\n"
    markdown_content += "| Mois | Nombre de TP |\n"
    markdown_content += "|------|-------------|\n"
    
    for mois in mois_ordre:
        nb = compteur_mois.get(mois, 0)
        markdown_content += f"| {mois} | {nb} |\n"
    
    markdown_content += f"| **TOTAL** | **{total_tp}** |\n\n"
    
    markdown_content += "### Diagramme en bâtons\n\n"
    
    # Générer le graphique en base64
    graphique_base64 = generer_graphique_base64(compteur_mois)
    
    markdown_content += f'<img src="{graphique_base64}" alt="Graphique des séances de TP" style="max-width: 100%; border: 1px solid #ddd; border-radius: 5px; padding: 10px; background: white;"/>\n\n'
    
    markdown_content += "---\n\n"
    markdown_content += "## Analyse\n\n"
    
    # Ajouter une petite analyse
    mois_max = max(mois_ordre, key=lambda m: compteur_mois.get(m, 0))
    val_max = compteur_mois.get(mois_max, 0)
    
    markdown_content += f"- Le mois avec le **plus de séances de TP** est **{mois_max}** avec **{val_max}** séance(s).\n"
    markdown_content += f"- Le groupe **{groupe_tp}** a eu au total **{total_tp}** séances de TP sur la période.\n"
    
    if len(seances_r107) > 0:
        markdown_content += f"- Le groupe a également suivi **{len(seances_r107)}** séance(s) de R1.07 (Informatique).\n"
    
    markdown_content += "\n---\n\n"
    markdown_content += "*Rapport généré automatiquement par Programme5.py*\n"
    
    return markdown_content


def obtenir_date_actuelle():
    """Retourne la date actuelle au format JJ/MM/AAAA"""
    from datetime import datetime
    return datetime.now().strftime("%d/%m/%Y")


def generer_html_avec_style(contenu_html):
    """Ajoute le CSS et la structure HTML complète"""
    
    html_complet = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport SAÉ 1.5 - Traiter des Données</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        
        h3 {
            color: #7f8c8d;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        th {
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        tr:hover {
            background-color: #f0f0f0;
        }
        
        hr {
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }
        
        ul, ol {
            line-height: 1.8;
        }
        
        strong {
            color: #e74c3c;
        }
        
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        
        .info-box {
            background-color: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        
        img {
            display: block;
            margin: 20px auto;
        }
        
        @media print {
            body {
                background-color: white;
            }
            
            .container {
                box-shadow: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
"""
    
    html_complet += contenu_html
    html_complet += """
    </div>
</body>
</html>
"""
    
    return html_complet


def generer_rapport_html(nom_fichier_ics, groupe_tp, nom_fichier_html):
    """Fonction principale qui génère le rapport HTML"""
    
    print("="*70)
    print("  PROGRAMME 5 - GÉNÉRATION DU RAPPORT HTML")
    print("="*70)
    print()
    
    # Vérifier que le module markdown est installé
    try:
        import markdown as md_module
        print(f"✓ Module Markdown version {md_module.__version__} détecté\n")
    except ImportError:
        print("\n" + "!"*70)
        print("  ERREUR : Le module markdown n'est pas installé !")
        print("!"*70)
        print("\nPour installer le module markdown, exécutez :")
        print("  → python -m pip install markdown")
        print("  ou")
        print("  → pip install markdown")
        print("\nPuis relancez ce programme.\n")
        return False
    
    print(f"Groupe analysé : {groupe_tp}")
    print(f"Fichier source : {nom_fichier_ics}\n")
    
    print("-" * 70)
    print("Étape 1 : Extraction des séances R1.07")
    print("-" * 70)
    
    seances_r107 = obtenir_seances_r107(nom_fichier_ics, groupe_tp)
    print(f"✓ {len(seances_r107)} séance(s) de R1.07 trouvée(s)\n")
    
    print("-" * 70)
    print("Étape 2 : Comptage des TP par mois")
    print("-" * 70)
    
    compteur_mois = compter_tp_par_mois(nom_fichier_ics, groupe_tp)
    total_tp = sum(compteur_mois.values())
    print(f"✓ {total_tp} séance(s) de TP trouvée(s) au total\n")
    
    print("-" * 70)
    print("Étape 3 : Génération du contenu Markdown")
    print("-" * 70)
    
    contenu_markdown = generer_contenu_markdown(groupe_tp, seances_r107, compteur_mois)
    print("✓ Contenu Markdown généré\n")
    
    print("-" * 70)
    print("Étape 4 : Conversion Markdown → HTML")
    print("-" * 70)
    
    # Convertir le Markdown en HTML avec le module markdown
    md = markdown.Markdown(extensions=['tables', 'extra'])
    contenu_html = md.convert(contenu_markdown)
    print("✓ Conversion Markdown → HTML effectuée\n")
    
    print("-" * 70)
    print("Étape 5 : Ajout du CSS et structure HTML")
    print("-" * 70)
    
    html_final = generer_html_avec_style(contenu_html)
    print("✓ Style CSS ajouté\n")
    
    print("-" * 70)
    print("Étape 6 : Écriture du fichier HTML")
    print("-" * 70)
    
    try:
        with open(nom_fichier_html, 'w', encoding='utf-8') as f:
            f.write(html_final)
        print(f"✓ Fichier HTML créé : {nom_fichier_html}\n")
        
        # Ouvrir automatiquement dans le navigateur
        import webbrowser
        chemin_complet = os.path.abspath(nom_fichier_html)
        webbrowser.open('file://' + chemin_complet)
        
        print("✓ Fichier ouvert dans le navigateur\n")
        print("="*70)
        print("  RAPPORT GÉNÉRÉ AVEC SUCCÈS !")
        print("="*70)
        
        return True
    except Exception as e:
        print(f"✗ Erreur lors de l'écriture du fichier : {e}\n")
        return False


# Programme principal
if __name__ == "__main__":
    # Configuration
    nom_fichier_ics = "ADE_RT1_Septembre2025_Decembre2025.ics"
    groupe_tp = "RT1-A1"
    nom_fichier_html = f"rapport_SAE15_{groupe_tp.replace('-', '_')}.html"
    
    # Générer le rapport
    succes = generer_rapport_html(nom_fichier_ics, groupe_tp, nom_fichier_html)
    
    if succes:
        print(f"\n✓ Vous pouvez consulter le rapport : {nom_fichier_html}")
    else:
        print("\n✗ La génération du rapport a échoué.")
