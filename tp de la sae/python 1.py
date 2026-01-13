##Programme1.py ##
##Conversion d'un fichier .ics (un seul événement) vers le format pseudo-csv ##

def lire_fichier_ics(nom_fichier):
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


def extraire_propriete(contenu, identificateur):
    ##Extrait la valeur d'une propriété à partir de son identificateur##
    lignes = contenu.split('\n')
    for ligne in lignes:
        if ligne.startswith(identificateur + ':'):
            return ligne.split(':', 1)[1].strip()
    return ""


def convertir_date_ics_vers_csv(date_ics):
    ##Convertit une date au format AAAAMMDDThhmmssZ vers JJ-MM-AAAA##
    ##Exemple: 20251205T090000Z -> 05-12-2025##
    if not date_ics or len(date_ics) < 15:
        return ""
    
    annee = date_ics[0:4]
    mois = date_ics[4:6]
    jour = date_ics[6:8]
    
    return f"{jour}-{mois}-{annee}"


def extraire_heure_ics(date_ics):
    ##Extrait l'heure d'une date au format AAAAMMDDThhmmssZ vers HH:MM##
    ##Exemple: 20251205T090000Z -> 09:00##
    if not date_ics or len(date_ics) < 15:
        return ""
    
    heure = date_ics[9:11]
    minutes = date_ics[11:13]
    
    return f"{heure}:{minutes}"


def calculer_duree(dtstart, dtend):
    ##Calcule la durée entre deux dates au format AAAAMMDDThhmmssZ##
    ##Retourne la durée au format HH:MM##
    if not dtstart or not dtend:
        return "00:00"
    
    # Extraction des heures et minutes de début
    heure_debut = int(dtstart[9:11])
    min_debut = int(dtstart[11:13])
    
    # Extraction des heures et minutes de fin
    heure_fin = int(dtend[9:11])
    min_fin = int(dtend[11:13])
    
    # Calcul de la durée en minutes
    total_min_debut = heure_debut * 60 + min_debut
    total_min_fin = heure_fin * 60 + min_fin
    duree_minutes = total_min_fin - total_min_debut
    
    # Conversion en heures et minutes
    heures = duree_minutes // 60
    minutes = duree_minutes % 60
    
    return f"{heures:02d}:{minutes:02d}"


def extraire_modalite(summary):

    ##Extrait la modalité d'enseignement du SUMMARY##
    ##Cherche CM, TD, TP, Proj, DS dans l'intitulé##
    
    modalites = ['CM', 'TD', 'TP', 'Proj', 'DS']
    summary_upper = summary.upper()
    
    for modalite in modalites:
        if modalite in summary_upper:
            return modalite
    
    return "CM"  # Par défaut


def extraire_description_elements(description):
    
    ###Extrait les groupes et professeurs de la DESCRIPTION###
    ###Format typique: \n\nRT1-S1\nLACAN DAVID\n###
    ###Retourne: (liste_profs, liste_groupes)###
    if not description:
        return ([], [])
    
    # Nettoyage de la description
    lignes = [ligne.strip() for ligne in description.split('\\n') if ligne.strip()]
    
    profs = []
    groupes = []
    
    for ligne in lignes:
        # Si la ligne contient un espace et des majuscules, c'est probablement un prof
        if ' ' in ligne and ligne.isupper():
            profs.append(ligne)
        # Si la ligne contient RT, TP, ou S, c'est probablement un groupe
        elif any(prefix in ligne for prefix in ['RT', 'TP', 'S']):
            groupes.append(ligne)
    
    return (profs, groupes)


def convertir_ics_vers_csv(nom_fichier):
    ###Fonction principale qui convertit un fichier .ics en format pseudo-csv###
    # Lecture du fichier
    contenu = lire_fichier_ics(nom_fichier)
    if contenu is None:
        return None
    
    # Extraction des propriétés
    uid = extraire_propriete(contenu, 'UID')
    dtstart = extraire_propriete(contenu, 'DTSTART')
    dtend = extraire_propriete(contenu, 'DTEND')
    summary = extraire_propriete(contenu, 'SUMMARY')
    location = extraire_propriete(contenu, 'LOCATION')
    description = extraire_propriete(contenu, 'DESCRIPTION')
    
    # Conversion des dates et heures
    date = convertir_date_ics_vers_csv(dtstart)
    heure = extraire_heure_ics(dtstart)
    duree = calculer_duree(dtstart, dtend)
    
    # Extraction de la modalité
    modalite = extraire_modalite(summary)
    
    # Intitulé
    intitule = summary
    
    # Salles (peuvent être multiples, séparées par |)
    salles = location if location else ""
    
    # Extraction des profs et groupes de la description
    profs, groupes = extraire_description_elements(description)
    profs_str = "|".join(profs) if profs else ""
    groupes_str = "|".join(groupes) if groupes else ""
    
    # Construction de la chaîne pseudo-csv
    csv_ligne = f"{uid};{date};{heure};{duree};{modalite};{intitule};{salles};{profs_str};{groupes_str}"
    
    return csv_ligne


# Programme principal
if __name__ == "__main__":
    # Nom du fichier à traiter
    nom_fichier = "evenementSAE_15_2025.ics"
    
    print("=== Conversion d'un fichier .ics vers le format pseudo-csv ===\n")
    
    # Conversion
    resultat = convertir_ics_vers_csv(nom_fichier)
    
    if resultat:
        print("Résultat de la conversion :")
        print(resultat)
    else:
        print("La conversion a échoué.")



"""
Programme2.py
Conversion d'un fichier .ics (plusieurs événements) vers le format pseudo-csv
Retourne un tableau de chaînes pseudo-csv
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
    Chaque événement commence par BEGIN:VEVENT et se termine par END:VEVENT
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
    """
    Convertit une date au format AAAAMMDDThhmmssZ vers JJ-MM-AAAA
    Exemple: 20251205T090000Z -> 05-12-2025
    """
    if not date_ics or date_ics == "vide" or len(date_ics) < 15:
        return "vide"
    
    annee = date_ics[0:4]
    mois = date_ics[4:6]
    jour = date_ics[6:8]
    
    return f"{jour}-{mois}-{annee}"


def extraire_heure_ics(date_ics):
    """
    Extrait l'heure d'une date au format AAAAMMDDThhmmssZ vers HH:MM
    Exemple: 20251205T090000Z -> 09:00
    """
    if not date_ics or date_ics == "vide" or len(date_ics) < 15:
        return "vide"
    
    heure = date_ics[9:11]
    minutes = date_ics[11:13]
    
    return f"{heure}:{minutes}"


def calculer_duree(dtstart, dtend):
    """
    Calcule la durée entre deux dates au format AAAAMMDDThhmmssZ
    Retourne la durée au format HH:MM
    """
    if not dtstart or not dtend or dtstart == "vide" or dtend == "vide":
        return "vide"
    
    try:
        # Extraction des heures et minutes de début
        heure_debut = int(dtstart[9:11])
        min_debut = int(dtstart[11:13])
        
        # Extraction des heures et minutes de fin
        heure_fin = int(dtend[9:11])
        min_fin = int(dtend[11:13])
        
        # Calcul de la durée en minutes
        total_min_debut = heure_debut * 60 + min_debut
        total_min_fin = heure_fin * 60 + min_fin
        duree_minutes = total_min_fin - total_min_debut
        
        # Gestion du passage à un autre jour
        if duree_minutes < 0:
            duree_minutes += 24 * 60
        
        # Conversion en heures et minutes
        heures = duree_minutes // 60
        minutes = duree_minutes % 60
        
        return f"{heures:02d}:{minutes:02d}"
    except:
        return "vide"


def extraire_modalite(summary):
    """
    Extrait la modalité d'enseignement du SUMMARY
    Cherche CM, TD, TP, Proj, DS dans l'intitulé
    """
    if not summary or summary == "vide":
        return "vide"
    
    modalites = ['CM', 'TD', 'TP', 'Proj', 'DS']
    summary_upper = summary.upper()
    
    for modalite in modalites:
        if modalite in summary_upper:
            return modalite
    
    return "CM"  # Par défaut


def extraire_description_elements(description):
    """
    Extrait les groupes et professeurs de la DESCRIPTION
    Format typique: \n\nRT1-S1\nLACAN DAVID\n
    Retourne: (liste_profs, liste_groupes)
    """
    if not description or description == "vide":
        return ([], [])
    
    # Nettoyage de la description
    lignes = [ligne.strip() for ligne in description.split('\\n') if ligne.strip()]
    
    profs = []
    groupes = []
    
    for ligne in lignes:
        # Si la ligne contient un espace et des majuscules, c'est probablement un prof
        if ' ' in ligne and ligne.isupper():
            profs.append(ligne)
        # Si la ligne contient RT, TP, ou S, c'est probablement un groupe
        elif any(prefix in ligne for prefix in ['RT', 'TP', 'S', 'A', 'B', 'C', 'D']):
            groupes.append(ligne)
    
    return (profs, groupes)


def convertir_evenement_vers_csv(contenu_evenement):
    """
    Convertit un événement individuel (chaîne .ics) en format pseudo-csv
    """
    # Extraction des propriétés
    uid = extraire_propriete(contenu_evenement, 'UID')
    dtstart = extraire_propriete(contenu_evenement, 'DTSTART')
    dtend = extraire_propriete(contenu_evenement, 'DTEND')
    summary = extraire_propriete(contenu_evenement, 'SUMMARY')
    location = extraire_propriete(contenu_evenement, 'LOCATION')
    description = extraire_propriete(contenu_evenement, 'DESCRIPTION')
    
    # Conversion des dates et heures
    date = convertir_date_ics_vers_csv(dtstart)
    heure = extraire_heure_ics(dtstart)
    duree = calculer_duree(dtstart, dtend)
    
    # Extraction de la modalité
    modalite = extraire_modalite(summary)
    
    # Intitulé
    intitule = summary if summary != "vide" else "vide"
    
    # Salles (peuvent être multiples, séparées par |)
    salles = location if location != "vide" else "vide"
    
    # Extraction des profs et groupes de la description
    profs, groupes = extraire_description_elements(description)
    profs_str = "|".join(profs) if profs else "vide"
    groupes_str = "|".join(groupes) if groupes else "vide"
    
    # Construction de la chaîne pseudo-csv
    csv_ligne = f"{uid};{date};{heure};{duree};{modalite};{intitule};{salles};{profs_str};{groupes_str}"
    
    return csv_ligne


def convertir_ics_multiple_vers_csv(nom_fichier):
    """
    Fonction principale qui convertit un fichier .ics contenant plusieurs événements
    en un tableau de chaînes pseudo-csv
    """
    # Lecture du fichier
    contenu = lire_fichier_ics(nom_fichier)
    if contenu is None:
        return None
    
    # Extraction de tous les événements
    evenements = extraire_evenements(contenu)
    
    print(f"Nombre d'événements trouvés : {len(evenements)}\n")
    
    # Conversion de chaque événement
    tableau_csv = []
    for i, evenement in enumerate(evenements):
        csv_ligne = convertir_evenement_vers_csv(evenement)
        tableau_csv.append(csv_ligne)
    
    return tableau_csv


def ecrire_fichier_csv(nom_fichier_sortie, tableau_csv):
    """
    Écrit le tableau de chaînes pseudo-csv dans un fichier CSV
    Ajoute un en-tête avec les noms des colonnes
    """
    try:
        with open(nom_fichier_sortie, 'w', encoding='utf-8') as f:
            # Écriture de l'en-tête
            en_tete = "UID;Date;Heure;Durée;Modalité;Intitulé;Salles;Professeurs;Groupes\n"
            f.write(en_tete)
            
            # Écriture de chaque événement
            for ligne in tableau_csv:
                f.write(ligne + '\n')
        
        print(f"✓ Fichier CSV créé avec succès : {len(tableau_csv)} événements")
        return True
    except Exception as e:
        print(f"✗ Erreur lors de l'écriture du fichier CSV : {e}")
        return False


# Programme principal
if __name__ == "__main__":
    # Nom du fichier à traiter
    nom_fichier = "ADE_RT1_Septembre2025_Decembre2025.ics"
    
    print("=== Conversion d'un fichier .ics (multiple) vers le format pseudo-csv ===\n")
    
    # Conversion
    resultat = convertir_ics_multiple_vers_csv(nom_fichier)
    
    if resultat:
        print("Résultat de la conversion :")
        print(f"Tableau contenant {len(resultat)} événements\n")
        
        # Affichage des 5 premiers événements comme exemple
        print("Exemple des 5 premiers événements :")
        for i, ligne in enumerate(resultat[:5]):
            print(f"\nÉvénement {i+1}:")
            print(ligne)
        
        if len(resultat) > 5:
            print(f"\n... et {len(resultat) - 5} autres événements")
        
        # Écriture dans un fichier CSV
        print("\n--- Écriture dans un fichier CSV ---")
        nom_fichier_sortie = "calendrier_output.csv"
        ecrire_fichier_csv(nom_fichier_sortie, resultat)
        print(f"Résultat écrit dans '{nom_fichier_sortie}'")
    else:
        print("La conversion a échoué.")
