"""
Programme3.py
Extraction des séances de R1.07 pour un groupe de TP spécifique
Retourne un tableau avec : date, durée, modalité
"""

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
    """
    Sépare le contenu d'un fichier .ics en une liste d'événements individuels
    """
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
    """Calcule la durée entre deux dates au format AAAAMMDDThhmmssZ"""
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


def extraire_modalite(summary):
    """Extrait la modalité d'enseignement du SUMMARY"""
    if not summary or summary == "vide":
        return "vide"
    
    modalites = ['CM', 'TD', 'TP', 'Proj', 'DS']
    summary_upper = summary.upper()
    
    for modalite in modalites:
        if modalite in summary_upper:
            return modalite
    
    return "CM"


def extraire_groupes(description):
    """Extrait la liste des groupes de la DESCRIPTION"""
    if not description or description == "vide":
        return []
    
    # Gérer différents formats de séparateurs
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
        # Détecter les groupes (RT, TP, A, B, C, D, S)
        if 'RT' in ligne_upper or 'TP' in ligne_upper or any(f'-{lettre}' in ligne_upper or f'{lettre}1' in ligne_upper or f'{lettre}2' in ligne_upper for lettre in ['A', 'B', 'C', 'D']):
            groupes.append(ligne)
        # Détecter aussi S1, S2, etc.
        elif ligne_upper.startswith('S') and len(ligne) <= 3:
            groupes.append(ligne)
    
    return groupes


def appartient_au_groupe(groupes_evenement, groupe_recherche):
    """
    Vérifie si le groupe recherché fait partie des groupes de l'événement
    Gère plusieurs formats possibles
    """
    if not groupes_evenement:
        return False
    
    # Normalisation du groupe recherché
    groupe_recherche_clean = groupe_recherche.upper().strip()
    
    # Extraire les composants du groupe recherché (ex: RT1-A1 -> RT1, A1, A, 1)
    composants_recherche = []
    composants_recherche.append(groupe_recherche_clean)
    
    # Ajouter des variantes
    if '-' in groupe_recherche_clean:
        parties = groupe_recherche_clean.split('-')
        composants_recherche.extend(parties)
    
    # Vérifier chaque groupe de l'événement
    for groupe in groupes_evenement:
        groupe_clean = groupe.upper().strip()
        
        # Correspondance exacte
        if groupe_clean == groupe_recherche_clean:
            return True
        
        # Vérifier si un composant du groupe recherché est dans le groupe de l'événement
        for composant in composants_recherche:
            if composant in groupe_clean:
                return True
        
        # Vérifier l'inverse : si le groupe de l'événement est dans le groupe recherché
        if groupe_clean in groupe_recherche_clean:
            return True
    
    return False


def est_ressource_r107(summary):
    """
    Vérifie si l'intitulé correspond à la ressource R1.07
    """
    if not summary or summary == "vide":
        return False
    
    summary_upper = summary.upper()
    
    # Recherche de différentes variantes possibles
    variantes = ['R1.07', 'R107', 'R1-07', 'R 1.07']
    
    for variante in variantes:
        if variante in summary_upper:
            return True
    
    return False


def filtrer_seances_r107(nom_fichier, groupe_tp, mode_debug=False):
    """
    Filtre les séances de R1.07 pour un groupe de TP spécifique
    Retourne un tableau avec [date, durée, modalité]
    """
    # Lecture du fichier
    contenu = lire_fichier_ics(nom_fichier)
    if contenu is None:
        return None
    
    # Extraction de tous les événements
    evenements = extraire_evenements(contenu)
    print(f"Nombre total d'événements : {len(evenements)}")
    
    # Filtrage des séances R1.07 pour le groupe spécifié
    seances_filtrees = []
    nb_r107_total = 0
    
    if mode_debug:
        print("\n=== MODE DEBUG ===")
    
    for i, evenement in enumerate(evenements):
        summary = extraire_propriete(evenement, 'SUMMARY')
        description = extraire_propriete(evenement, 'DESCRIPTION')
        
        # Vérifier si c'est une séance R1.07
        if est_ressource_r107(summary):
            nb_r107_total += 1
            
            # Extraire les groupes
            groupes = extraire_groupes(description)
            
            if mode_debug and nb_r107_total <= 5:  # Afficher seulement les 5 premiers en debug
                print(f"\nÉvénement R1.07 #{nb_r107_total}:")
                print(f"  Summary: {summary}")
                print(f"  Description brute: {description[:100]}...")
                print(f"  Groupes extraits: {groupes}")
                print(f"  Correspond au groupe {groupe_tp}? {appartient_au_groupe(groupes, groupe_tp)}")
            
            # Vérifier si le groupe recherché est dans la liste
            if appartient_au_groupe(groupes, groupe_tp):
                # Extraire les informations nécessaires
                dtstart = extraire_propriete(evenement, 'DTSTART')
                dtend = extraire_propriete(evenement, 'DTEND')
                
                date = convertir_date_ics_vers_csv(dtstart)
                duree = calculer_duree(dtstart, dtend)
                modalite = extraire_modalite(summary)
                
                # Ajouter au tableau résultat
                seances_filtrees.append([date, duree, modalite])
    
    if mode_debug:
        print(f"\n=== FIN DEBUG ===")
        print(f"Nombre total de séances R1.07 trouvées: {nb_r107_total}")
    
    return seances_filtrees


def afficher_resultats(seances, groupe_tp):
    """Affiche les résultats de manière formatée"""
    if not seances:
        print(f"\nAucune séance de R1.07 trouvée pour le groupe {groupe_tp}")
        return
    
    print(f"\n=== Séances de R1.07 pour le groupe {groupe_tp} ===")
    print(f"Nombre de séances trouvées : {len(seances)}\n")
    
    print(f"{'Date':<15} {'Durée':<10} {'Modalité':<10}")
    print("-" * 40)
    
    for seance in seances:
        date, duree, modalite = seance
        print(f"{date:<15} {duree:<10} {modalite:<10}")


def exporter_vers_csv(seances, nom_fichier_sortie, groupe_tp):
    """Exporte les résultats dans un fichier CSV"""
    try:
        with open(nom_fichier_sortie, 'w', encoding='utf-8') as f:
            # En-tête
            f.write(f"# Séances de R1.07 pour le groupe {groupe_tp}\n")
            f.write("Date;Durée;Modalité\n")
            
            # Données
            for seance in seances:
                date, duree, modalite = seance
                f.write(f"{date};{duree};{modalite}\n")
        
        print(f"\n✓ Résultats exportés dans '{nom_fichier_sortie}'")
        return True
    except Exception as e:
        print(f"\n✗ Erreur lors de l'export : {e}")
        return False


# Programme principal
if __name__ == "__main__":
    # Configuration
    nom_fichier = "ADE_RT1_Septembre2025_Decembre2025.ics"
    groupe_tp = input("Entrez votre groupe de TP (ex: RT1-A1, RT1-B2, etc.) : ").strip()
    
    # Demander si mode debug
    mode_debug = input("Activer le mode debug pour voir les détails d'extraction ? (o/n) : ").strip().lower() == 'o'
    
    print(f"\n=== Recherche des séances R1.07 pour le groupe {groupe_tp} ===\n")
    
    # Filtrage des séances
    seances = filtrer_seances_r107(nom_fichier, groupe_tp, mode_debug)
    
    if seances is not None:
        # Affichage des résultats
        afficher_resultats(seances, groupe_tp)
        
        # Export optionnel
        if seances:
            reponse = input("\nVoulez-vous exporter les résultats dans un fichier CSV ? (o/n) : ").strip().lower()
            if reponse == 'o':
                nom_sortie = f"seances_R107_{groupe_tp.replace('-', '_')}.csv"
                exporter_vers_csv(seances, nom_sortie, groupe_tp)
    else:
        print("Échec du traitement du fichier.")
