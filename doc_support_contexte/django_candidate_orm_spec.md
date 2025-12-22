# Spécifications ORM Django — Modèle Candidat

## Contexte

Site de matching candidats / offres d'emploi en Django.

Les données candidat sont extraites automatiquement depuis un ou plusieurs CVs uploadés. Chaque information extraite doit être :
- Tracée vers son CV source
- Activable/désactivable par le candidat
- Supprimée en cascade si le CV source est retiré

---

## Principes de conception

1. **Coexistence** : plusieurs CVs peuvent coexister, les données s'ajoutent
2. **Traçabilité** : chaque ligne extraite est liée à son CV source
3. **Contrôle candidat** : le candidat peut désactiver des lignes qu'il juge non pertinentes
4. **Vue consolidée** : le matching utilise uniquement les lignes actives, agrégées
5. **Suppression propre** : retirer un CV supprime toutes les lignes associées (cascade)

---

## Modèles à créer

### 1. Candidate

Modèle principal représentant un candidat.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| email | EmailField | unique=True | Identifiant principal |
| first_name | CharField(100) | blank=True | Prénom (peut être extrait) |
| last_name | CharField(100) | blank=True | Nom (peut être extrait) |
| phone | CharField(20) | blank=True | Téléphone |
| created_at | DateTimeField | auto_now_add=True | Date de création |
| updated_at | DateTimeField | auto_now=True | Date de mise à jour |

---

### 2. CV

Représente un fichier CV uploadé par le candidat.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| candidate | ForeignKey | → Candidate, on_delete=CASCADE, related_name='cvs' | Propriétaire du CV |
| file | FileField | upload_to='cvs/' | Fichier uploadé |
| original_filename | CharField(255) | | Nom original du fichier |
| uploaded_at | DateTimeField | auto_now_add=True | Date d'upload |
| extraction_status | CharField(20) | choices, default='pending' | Statut d'extraction |
| extracted_at | DateTimeField | null=True, blank=True | Date de fin d'extraction |

**Choix pour extraction_status :**
```python
EXTRACTION_STATUS_CHOICES = [
    ('pending', 'En attente'),
    ('processing', 'En cours'),
    ('completed', 'Terminé'),
    ('failed', 'Échec'),
]
```

---

### 3. ExtractedLine

Modèle central. Chaque ligne représente une unité d'information extraite d'un CV.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| candidate | ForeignKey | → Candidate, on_delete=CASCADE, related_name='extracted_lines' | Candidat propriétaire |
| source_cv | ForeignKey | → CV, on_delete=CASCADE, related_name='extracted_lines' | CV source |
| content_type | CharField(20) | choices, db_index=True | Type de contenu |
| content | TextField | | Texte extrait |
| is_active | BooleanField | default=True | Actif pour le matching |
| order | PositiveIntegerField | default=0 | Ordre d'affichage |
| created_at | DateTimeField | auto_now_add=True | Date de création |
| modified_at | DateTimeField | auto_now=True | Date de modification |
| modified_by_candidate | BooleanField | default=False | True si édité manuellement |

**Choix pour content_type :**
```python
CONTENT_TYPE_CHOICES = [
    ('summary', 'Résumé / Accroche'),
    ('experience', 'Expérience professionnelle'),
    ('education', 'Formation'),
    ('skill_hard', 'Compétence technique'),
    ('skill_soft', 'Soft skill'),
    ('language', 'Langue'),
    ('certification', 'Certification'),
    ('interest', 'Centre d\'intérêt'),
    ('other', 'Autre'),
]
```

**Granularité par type :**
- `experience` : 1 poste = 1 ligne (bloc de texte complet)
- `education` : 1 diplôme = 1 ligne
- `skill_hard` : 1 compétence = 1 ligne
- `skill_soft` : 1 compétence = 1 ligne
- `language` : 1 langue = 1 ligne
- `certification` : 1 certification = 1 ligne
- `summary` : 1 paragraphe = 1 ligne
- `interest` : 1 centre d'intérêt = 1 ligne

---

## Index à créer

```python
class Meta:
    indexes = [
        models.Index(fields=['candidate', 'content_type']),
        models.Index(fields=['candidate', 'is_active']),
        models.Index(fields=['source_cv']),
    ]
    ordering = ['content_type', 'order', '-created_at']
```

---

## Méthodes à implémenter

### Sur Candidate

```python
def get_consolidated_profile(self):
    """
    Retourne toutes les lignes actives, groupées par content_type.
    Utilisé pour le matching et l'affichage du profil consolidé.
    Retourne : dict {content_type: [ExtractedLine, ...]}
    """

def get_lines_by_cv(self, cv_id):
    """
    Retourne toutes les lignes extraites d'un CV spécifique.
    Utilisé pour l'affichage par source.
    Retourne : QuerySet[ExtractedLine]
    """

def get_active_lines_count(self):
    """
    Retourne le nombre de lignes actives.
    Utilisé pour les indicateurs de complétion du profil.
    Retourne : int
    """
```

### Sur CV

```python
def get_extracted_lines(self):
    """
    Retourne toutes les lignes issues de ce CV.
    Retourne : QuerySet[ExtractedLine]
    """

def get_active_lines(self):
    """
    Retourne uniquement les lignes actives de ce CV.
    Retourne : QuerySet[ExtractedLine]
    """
```

### Sur ExtractedLine

```python
def toggle_active(self):
    """
    Inverse le statut is_active.
    """

def mark_as_modified(self):
    """
    Marque la ligne comme modifiée par le candidat.
    À appeler lors d'une édition manuelle du content.
    """
```

---

## Contraintes et règles métier

1. Un candidat peut avoir 0 à N CVs
2. Un CV appartient à exactement 1 candidat
3. Une ExtractedLine appartient à exactement 1 CV et 1 candidat
4. Supprimer un CV → supprime toutes ses ExtractedLine (CASCADE)
5. Supprimer un Candidate → supprime ses CVs et ses ExtractedLine (CASCADE)
6. Le champ `candidate` sur ExtractedLine est dénormalisé (redondant avec source_cv.candidate) pour optimiser les requêtes

---

## Structure des fichiers attendue

```
candidates/
├── models/
│   ├── __init__.py
│   ├── candidate.py
│   ├── cv.py
│   └── extracted_line.py
├── managers.py  (si managers custom nécessaires)
└── ...
```

Ou en fichier unique si préféré :

```
candidates/
├── models.py
└── ...
```

---

## Notes d'implémentation

- Utiliser `select_related('source_cv')` lors des requêtes sur ExtractedLine pour éviter les N+1
- Prévoir un signal `post_delete` sur CV si des actions supplémentaires sont nécessaires au-delà du CASCADE
- Le champ `order` permet au candidat de réordonner les lignes au sein d'un même content_type
