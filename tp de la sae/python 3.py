"""
Programme4.py
Affichage graphique du nombre de séances de TP par mois pour le groupe A1
Export en format PNG (généré manuellement pixel par pixel)
AUCUNE BIBLIOTHÈQUE EXTERNE REQUISE - Utilise uniquement Python standard
"""

from collections import Counter

def lire_fichier_ics(nom_fichier):
    """Lit le contenu d'un fichier .ics et retourne son contenu sous forme de chaîne"""
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


def compter_tp_par_mois(nom_fichier, groupe_tp):
    """Compte le nombre de séances de TP par mois pour un groupe spécifique"""
    contenu = lire_fichier_ics(nom_fichier)
    if contenu is None:
        return None
    
    evenements = extraire_evenements(contenu)
    print(f"Nombre total d'événements : {len(evenements)}")
    
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
    
    compteur = Counter(mois_list)
    return compteur


def afficher_graphique_ascii(compteur_mois, groupe_tp):
    """Affiche un graphique en bâtons en ASCII art dans la console"""
    
    mois_ordre = ['Septembre', 'Octobre', 'Novembre', 'Décembre']
    valeurs = [compteur_mois.get(mois, 0) for mois in mois_ordre]
    
    print("\n" + "="*70)
    print(f"  GRAPHIQUE - Séances de TP pour le groupe {groupe_tp}")
    print(f"  (Septembre - Décembre 2025)")
    print("="*70 + "\n")
    
    # Trouver la valeur maximale pour l'échelle
    max_val = max(valeurs) if max(valeurs) > 0 else 5
    hauteur_graphique = 20  # Hauteur en lignes
    
    # Dessiner le graphique ligne par ligne (de haut en bas)
    for ligne in range(hauteur_graphique, -1, -1):
        # Afficher l'échelle sur l'axe Y
        valeur_ligne = (ligne * max_val) / hauteur_graphique
        print(f"{valeur_ligne:5.1f} |", end="")
        
        # Dessiner les barres pour chaque mois
        for i, valeur in enumerate(valeurs):
            hauteur_barre = (valeur * hauteur_graphique) / max_val
            
            if ligne <= hauteur_barre:
                # Différents caractères pour chaque mois
                caracteres = ['█', '▓', '▒', '░']
                print(f"  {caracteres[i] * 8}  ", end="")
            else:
                print(f"  {'':8}  ", end="")
        
        print()
    
    # Ligne horizontale (axe X)
    print("      " + "-" * 60)
    
    # Labels des mois
    print("      ", end="")
    for mois in mois_ordre:
        print(f"  {mois[:4]:^8}  ", end="")
    print("\n")
    
    # Légende avec valeurs exactes
    print("      Valeurs exactes :")
    for mois, valeur in zip(mois_ordre, valeurs):
        print(f"        - {mois:12} : {valeur} séance(s)")
    
    print("\n" + "="*70 + "\n")


def generer_png_manuel(compteur_mois, groupe_tp, nom_fichier):
    """
    Génère un fichier PNG manuellement (pixel par pixel)
    en créant un fichier binaire PNG valide
    """
    
    mois_ordre = ['Septembre', 'Octobre', 'Novembre', 'Décembre']
    valeurs = [compteur_mois.get(mois, 0) for mois in mois_ordre]
    
    # Dimensions de l'image
    largeur = 800
    hauteur = 600
    
    # Créer une image RGB (3 octets par pixel)
    image = [[[255, 255, 255] for _ in range(largeur)] for _ in range(hauteur)]
    
    # Couleurs pour les barres (RGB)
    couleurs = [
        [255, 107, 107],  # Rouge clair - Septembre
        [78, 205, 196],   # Turquoise - Octobre
        [69, 183, 209],   # Bleu clair - Novembre
        [255, 160, 122]   # Orange clair - Décembre
    ]
    
    # Zones de dessin
    marge_gauche = 80
    marge_droite = 50
    marge_haut = 100
    marge_bas = 100
    
    zone_largeur = largeur - marge_gauche - marge_droite
    zone_hauteur = hauteur - marge_haut - marge_bas
    
    # Dessiner le fond blanc (déjà fait par défaut)
    
    # Dessiner les axes
    # Axe Y (vertical)
    for y in range(marge_haut, hauteur - marge_bas):
        image[y][marge_gauche] = [0, 0, 0]
        image[y][marge_gauche + 1] = [0, 0, 0]
    
    # Axe X (horizontal)
    for x in range(marge_gauche, largeur - marge_droite):
        image[hauteur - marge_bas][x] = [0, 0, 0]
        image[hauteur - marge_bas - 1][x] = [0, 0, 0]
    
    # Calculer l'échelle
    max_val = max(valeurs) if max(valeurs) > 0 else 5
    echelle_max = max_val + 2
    
    # Dessiner la grille horizontale
    for i in range(0, int(echelle_max) + 1):
        y = hauteur - marge_bas - int((i * zone_hauteur) / echelle_max)
        if marge_haut <= y < hauteur - marge_bas:
            for x in range(marge_gauche, largeur - marge_droite):
                if x % 2 == 0:  # Ligne pointillée
                    image[y][x] = [220, 220, 220]
    
    # Dessiner les barres
    nb_barres = len(mois_ordre)
    largeur_barre = zone_largeur // (nb_barres * 2)
    espace_entre_barres = zone_largeur // nb_barres
    
    for i, (valeur, couleur) in enumerate(zip(valeurs, couleurs)):
        # Position de la barre
        x_centre = marge_gauche + espace_entre_barres * i + espace_entre_barres // 2
        x_gauche = x_centre - largeur_barre // 2
        x_droite = x_centre + largeur_barre // 2
        
        # Hauteur de la barre
        if echelle_max > 0:
            hauteur_barre = int((valeur * zone_hauteur) / echelle_max)
        else:
            hauteur_barre = 0
        
        y_haut = hauteur - marge_bas - hauteur_barre
        y_bas = hauteur - marge_bas
        
        # Remplir la barre
        for y in range(max(marge_haut, y_haut), y_bas):
            for x in range(x_gauche, x_droite):
                if 0 <= x < largeur and 0 <= y < hauteur:
                    image[y][x] = couleur
        
        # Bordure noire autour de la barre
        # Haut
        for x in range(x_gauche, x_droite):
            if y_haut >= marge_haut:
                image[y_haut][x] = [0, 0, 0]
        # Bas
        for x in range(x_gauche, x_droite):
            image[y_bas - 1][x] = [0, 0, 0]
        # Gauche
        for y in range(max(marge_haut, y_haut), y_bas):
            image[y][x_gauche] = [0, 0, 0]
        # Droite
        for y in range(max(marge_haut, y_haut), y_bas):
            if x_droite - 1 < largeur:
                image[y][x_droite - 1] = [0, 0, 0]
    
    # Écrire le fichier PNG
    try:
        ecrire_png(image, nom_fichier)
        print(f"\n✓ Graphique PNG créé : {nom_fichier}")
        return True
    except Exception as e:
        print(f"\n✗ Erreur lors de la création du PNG : {e}")
        return False


def ecrire_png(image, nom_fichier):
    """Écrit une image au format PNG (format simplifié)"""
    import struct
    import zlib
    
    hauteur = len(image)
    largeur = len(image[0])
    
    # En-tête PNG
    png_signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk (information sur l'image)
    ihdr_data = struct.pack('>IIBBBBB', largeur, hauteur, 8, 2, 0, 0, 0)
    ihdr_chunk = creer_chunk(b'IHDR', ihdr_data)
    
    # IDAT chunk (données de l'image)
    raw_data = bytearray()
    for ligne in image:
        raw_data.append(0)  # Filtre : aucun
        for pixel in ligne:
            raw_data.extend(pixel)
    
    compressed_data = zlib.compress(raw_data, 9)
    idat_chunk = creer_chunk(b'IDAT', compressed_data)
    
    # IEND chunk (fin du fichier)
    iend_chunk = creer_chunk(b'IEND', b'')
    
    # Écrire le fichier
    with open(nom_fichier, 'wb') as f:
        f.write(png_signature)
        f.write(ihdr_chunk)
        f.write(idat_chunk)
        f.write(iend_chunk)


def creer_chunk(chunk_type, data):
    """Crée un chunk PNG"""
    import struct
    import zlib
    
    length = len(data)
    crc = zlib.crc32(chunk_type + data) & 0xffffffff
    return struct.pack('>I', length) + chunk_type + data + struct.pack('>I', crc)


def afficher_statistiques(compteur_mois, groupe_tp):
    """Affiche les statistiques détaillées"""
    print(f"\n{'='*60}")
    print(f"  Statistiques des séances de TP pour le groupe {groupe_tp}")
    print(f"{'='*60}\n")
    
    mois_ordre = ['Septembre', 'Octobre', 'Novembre', 'Décembre']
    total = 0
    
    print(f"{'Mois':<20} {'Nombre de TP':>15}")
    print("-" * 40)
    
    for mois in mois_ordre:
        nb = compteur_mois.get(mois, 0)
        total += nb
        print(f"{mois:<20} {nb:>15}")
    
    print("-" * 40)
    print(f"{'TOTAL':<20} {total:>15}")
    print(f"{'='*60}\n")


# Programme principal
if __name__ == "__main__":
    print("="*70)
    print("  PROGRAMME 4 - ANALYSE DES SÉANCES DE TP PAR MOIS")
    print("  (Sans bibliothèques externes)")
    print("="*70)
    
    # Configuration
    nom_fichier = "ADE_RT1_Septembre2025_Decembre2025.ics"
    groupe_tp = "RT1-A1"
    
    print(f"\nGroupe analysé : {groupe_tp}")
    print(f"Fichier source : {nom_fichier}\n")
    
    # Compter les TP par mois
    compteur = compter_tp_par_mois(nom_fichier, groupe_tp)
    
    if compteur is not None:
        # Afficher les statistiques
        afficher_statistiques(compteur, groupe_tp)
        
        # Afficher le graphique ASCII
        afficher_graphique_ascii(compteur, groupe_tp)
        
        # Générer le fichier PNG
        print("\n" + "-" * 70)
        print("Génération du fichier PNG...")
        print("-" * 70)
        
        nom_png = f"graphique_TP_{groupe_tp.replace('-', '_')}.png"
        generer_png_manuel(compteur, groupe_tp, nom_png)
        
        print("\n✓ Programme terminé avec succès !")
        print(f"✓ Fichier créé : {nom_png}")
    else:
        print("\n✗ Échec du traitement du fichier.")
