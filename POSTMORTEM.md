# Postmortem - JobMatch

## 📅 Sessions

### 2025-12-22 - Initialisation du projet
**Contexte:** Démarrage du projet JobMatch - plateforme de matching CV/offres d'emploi

**Réalisations:**
- Lecture et analyse des documents de contexte (One liner.pdf, Job match.xlsx)
- Compréhension de la vision produit (V1 MVP → V2 avec personnalisation CV)
- Identification de l'équipe (Matthieu, Clément, Mohamed, Maxime)
- Création du fichier POSTMORTEM.md
- Création du fichier PITCH.md

**Problèmes rencontrés:**
- Fichier Excel non lisible directement (format binaire) → résolu avec pandas + openpyxl

**Solutions appliquées:**
- Installation de pandas et openpyxl pour lire le fichier Excel

**Décisions techniques:**
- Stack technique à définir (deadline 22/12)
- Matthieu préfère travailler sur la partie SaaS (front, gestion compte, import CV)
- Partie Data Engineering (ingestion offres) à attribuer

## 🧠 Apprentissages clés
- Le projet a deux versions : V1 (matching simple) et V2 (matching + personnalisation CV)
- POC structuré en 4 domaines : Gestion Compte (DE:0), Import CV (DE:1), Ingestion Offres (DE:2), Smart Match (DE:2)
- Priorités MoSCoW définies dans les User Stories

## ⚠️ Pièges à éviter
- Ne pas oublier la conformité RGPD (tâche assignée à Maxime)
- Gentleman Agreement à signer avant de continuer

## 🏗️ Patterns qui fonctionnent
- Documentation structurée dans Google Drive
- User Stories avec priorités MoSCoW et critères d'acceptation
- Répartition des tâches selon les préférences/compétences

## 📋 TODO / Dette technique
- [ ] Choix de la stack technique (deadline 22/12)
- [ ] Gentleman Agreement à rédiger et signer
- [ ] Présentation GitHub à faire (Matthieu)
- [ ] État de l'art scientifique (données, algos, SaaS existants, limites)
- [ ] Se renseigner sur la RGPD (Maxime)
