# Contributing to Horai

[English](#english) | [Français](#français)

---

## English

Thank you for your interest in contributing to Horai.

### How to contribute

- **Bug reports** — Open an issue on [GitHub](https://github.com/mikaelmasson/horai/issues).
  Please include your Python version, OS, and the full error message.
- **Feature requests** — Open an issue describing the use case before writing code.
- **Pull requests** — Fork the repository, create a branch, and submit a PR against `main`.

### Development setup

```bash
git clone https://github.com/mikaelmasson/horai.git
cd horai
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Horai is intentionally a single-file script with minimal dependencies. Before
adding a new dependency, consider whether the task can be accomplished with the
Python standard library.

### Code style

- Python 3.10+ with full type hints on all public functions.
- Follow PEP 8. Black formatting is preferred.
- Google-style docstrings for public functions.
- Keep the script runnable as a standalone file: `python horai.py --help` must
  work with only `msal` installed.

### Tests

```bash
pytest tests/
```

Add tests for any new functionality. Edge cases (empty folders, non-ASCII folder
names, network errors) are especially welcome.

### License

By contributing to Horai, you agree that your contributions will be licensed
under the **Mozilla Public License 2.0** (MPL-2.0). This means:

- Your modifications to Horai's files must remain open-source under MPL-2.0.
- You retain copyright over your contributions.
- Horai can be used as a component in GPL or proprietary projects without
  contaminating the larger work.

Please ensure you have the right to submit code under these terms before
opening a pull request.

---

## Français

Merci de votre intérêt pour la contribution à Horai.

### Comment contribuer

- **Rapports de bugs** — Ouvrez une issue sur [GitHub](https://github.com/mikaelmasson/horai/issues).
  Veuillez inclure votre version Python, votre OS, et le message d'erreur complet.
- **Demandes de fonctionnalités** — Ouvrez une issue décrivant le cas d'usage
  avant d'écrire du code.
- **Pull requests** — Forkez le dépôt, créez une branche et soumettez une PR
  contre `main`.

### Mise en place de l'environnement de développement

```bash
git clone https://github.com/mikaelmasson/horai.git
cd horai
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Horai est intentionnellement un script mono-fichier avec des dépendances minimales.
Avant d'ajouter une nouvelle dépendance, vérifiez si la tâche peut être accomplie
avec la bibliothèque standard Python.

### Style de code

- Python 3.10+ avec des annotations de type complètes sur toutes les fonctions
  publiques.
- Respecter la PEP 8. Le formatage Black est préféré.
- Docstrings au style Google pour les fonctions publiques.
- Garder le script exécutable en mode autonome : `python horai.py --help` doit
  fonctionner avec seulement `msal` installé.

### Tests

```bash
pytest tests/
```

Ajoutez des tests pour toute nouvelle fonctionnalité. Les cas limites (dossiers
vides, noms de dossiers non-ASCII, erreurs réseau) sont particulièrement
bienvenus.

### Licence

En contribuant à Horai, vous acceptez que vos contributions soient licenciées
sous la **Mozilla Public License 2.0** (MPL-2.0). Cela signifie :

- Vos modifications aux fichiers de Horai doivent rester open-source sous MPL-2.0.
- Vous conservez le droit d'auteur sur vos contributions.
- Horai peut être utilisé comme composant dans des projets GPL ou propriétaires
  sans contaminer l'ensemble du projet.

Veuillez vous assurer que vous avez le droit de soumettre du code sous ces
conditions avant d'ouvrir une pull request.
