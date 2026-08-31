# Aruba Switch Builder

**Aruba Switch Builder** est une application web conçue pour simplifier la configuration des commutateurs réseau (switches) de la gamme Aruba AOS-CX. Elle offre une interface graphique interactive permettant de concevoir, sauvegarder et générer automatiquement les scripts de commande (CLI) nécessaires à la mise en service d'un équipement.

---

## 1. Présentation Générale (Non-experts)

### À quoi sert l'application ?

La configuration d'un switch réseau s'effectue habituellement en saisissant des lignes de commande textuelles dans un terminal. **Aruba Switch Builder** permet d'effectuer cette tâche de manière visuelle et intuitive :

* **Visualisation matérielle** : Affichage d'un schéma interactif de la façade du switch respectant la disposition réelle des ports (cuivre RJ45 et fibre SFP+).


* **Organisation du réseau (VLANs)** : Création de réseaux virtuels (VLANs) et affectation sur les ports en mode *Access* (équipement final) ou *Trunk* (liaison inter-switchs).


* **Gestion des utilisateurs et de la sécurité** : Déclaration d'utilisateurs locaux et création de groupes d'accès définissant les commandes CLI autorisées ou interdites.


* **Génération automatique du script CLI** : Traduction instantanée des choix visuels en un fichier de configuration syntaxiquement exact, prêt à être appliqué sur le switch.


* **Sauvegarde et réutilisation** : Enregistrement des configurations en base de données pour modification ou déploiement ultérieur.



---

## 2. Architecture & Détails Techniques (Développeurs)

### Stack Technique

* **Frontend** : React 18, TypeScript, Vite, Tailwind CSS v4, Zustand (gestion d'état).


* **Backend** : Python 3.11, FastAPI, Pydantic v2, SQLAlchemy v2, Alembic.


* **Base de données** : PostgreSQL 16 (stockage des configurations au format JSONB).


* **Orchestration** : Docker & Docker Compose.



### Structure du Projet

```text
aruba-gui/
├── backend/
│   ├── alembic/                # Migrations de schéma PostgreSQL[cite: 2]
│   ├── app/
│   │   ├── cli_generators/     # Moteurs de génération CLI (Pattern Polymorphism)[cite: 2]
│   │   ├── domain/             # Modèles métiers Pydantic & règles de validation[cite: 2]
│   │   ├── repositories/       # Couche d'accès aux données (PostgreSQL/SQLAlchemy)[cite: 2]
│   │   ├── switch_profiles/    # Définitions matérielles & dispositions SVG des switches[cite: 2]
│   │   ├── database.py         # Gestion des sessions SQLAlchemy[cite: 2]
│   │   ├── main.py             # Routeur FastAPI et validation globale[cite: 2]
│   │   └── settings.py         # Configuration via Pydantic BaseSettings[cite: 2]
│   ├── Dockerfile              # Image Docker du backend FastAPI[cite: 2]
│   └── entrypoint.sh           # Script d'exécution des migrations et d'Uvicorn[cite: 2]
├── frontend/
│   ├── src/                    # Interface utilisateur React / TypeScript[cite: 2]
│   └── Dockerfile              # Image Docker du frontend Vite[cite: 2]
└── docker-compose.yml          # Déploiement multi-conteneurs[cite: 2]

```

### Principes de Conception (Patterns & Métier)

* **Polymorphisme (`ConfigOutputGenerator`)** : L'interface abstraite `ConfigOutputGenerator` impose le contrat de génération. L'implémentation `AosCxCliGenerator` traduit l'état désiré (`SwitchState`) en commandes AOS-CX. Ce découplage permet d'ajouter un générateur (ex. Playbook Ansible) sans impacter les contrôleurs.


* **Information Expert (`SwitchProfile`)** : Chaque profil définit les propriétés matérielles du switch (nombre de ports, coordonnées X/Y pour le SVG, VLANs réservés, comportements L2/L3 par défaut comme `requires_no_routing`).


* **Contraintes du Domaine Utilisateurs** :
* Les groupes système intégrés (`administrators`, `operators`, `auditors`) sont protégés contre toute redéfinition.


* Le compte `admin` est implicite et exclu de l'état désiré.


* Les règles de commande personnalisées évaluent les requêtes selon leur numéro de séquence (`seq`) avec des actions `permit` ou `deny`.


* Limites strictes : Maximum 63 utilisateurs locaux et 29 groupes personnalisés.





### Endpoints API REST

| Méthode | Route | Description |
| --- | --- | --- |
| `GET` | `/api/profiles` | Retourne la liste des modèles de switches supportés. |
| `GET` | `/api/profiles/{profile_id}` | Récupère les caractéristiques techniques et visuelles d'un modèle. |
| `POST` | `/api/profiles/{profile_id}/generate-cli` | Valide l'état désiré et retourne le script CLI AOS-CX généré. |
| `GET` | `/api/configurations` | Liste toutes les configurations enregistrées. |
| `POST` | `/api/configurations` | Enregistre ou met à jour une configuration. |
| `GET` | `/api/configurations/{config_id}` | Obtient le détail d'une configuration sauvegardée. |
| `DELETE` | `/api/configurations/{config_id}` | Supprime une configuration de la base de données. |

---

## 3. Installation et Déploiement

### Prérequis

* Docker Engine & Docker Compose.



### Lancement Rapide

1. Dupliquer le fichier de variables d'environnement :


```bash
cp .env.example .env
```


2. Démarrer les services avec Docker Compose :


```bash
docker-compose up --build
```


3. Accès aux applications :
* **Interface Web (Frontend)** : `http://localhost:5173`

* **API Backend** : `http://localhost:8000`

* **Documentation OpenAPI / Swagger** : `http://localhost:8000/docs`




### Migrations de la Base de Données

Les migrations sont appliquées automatiquement au démarrage du conteneur backend via `entrypoint.sh`. Pour générer une nouvelle migration suite à une modification du modèle ORM `ConfigurationORM` :

```bash
cd backend
alembic revision --autogenerate -m "description_de_la_modification"
alembic upgrade head
```

---

## 4. Guide de Maintenance et d'Extension

### Ajouter un nouveau modèle de Switch

1. Définir le nouveau profil dans `backend/app/switch_profiles/` en instanciant `SwitchProfile`.


2. Spécifier la disposition des ports (coordonnées SVG), le type de médium (`RJ45` ou `SFP_PLUS`), et les drapeaux système (`requires_no_routing`).


3. Enregistrer le profil dans le dictionnaire `PROFILES` de `backend/app/main.py`.



### Ajouter un nouveau format d'exportation (ex: Ansible)

1. Créer une classe dérivée de `ConfigOutputGenerator` dans `backend/app/cli_generators/`.


2. Implémenter la méthode `generate(self, profile: SwitchProfile, state: SwitchState) -> str`.


3. Enregistrer l'instance dans le dictionnaire `GENERATORS` du fichier `backend/app/main.py`.