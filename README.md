# Horai

*Named after the Horai (Ὧραι), the Greek goddesses of seasons — companions of Hermes.*

**Horai** is a standalone CLI tool that dumps an entire email mailbox into a portable archive.
No server needed, no complex setup — just Python and one command.

[English](#english) | [Français](#français)

---

## English

### Features

- **M365 / Office 365** — OAuth2 device flow, zero credential storage
- **Any IMAP server** — Gmail, Fastmail, Yahoo, iCloud, self-hosted...
- **Auto-detects** the IMAP server from the email domain
- **One `.mbox` file per folder**, bundled in a single `.tar.gz`
- **Resume** interrupted dumps with `--resume`
- **Selective dump** with `--folders`
- **Standalone** — requires only Python 3.10+ and `msal` (for M365)

---

### Quick Start

```bash
# Install (from PyPI)
pip install horai

# Or run directly without installing
pip install msal          # only needed for M365
python horai.py --email user@company.com --name my-backup
```

---

### Usage Examples

#### Microsoft 365 / Office 365 (OAuth2, recommended)

```bash
horai --email user@company.com --name company-backup
```

A device-flow prompt will appear in your terminal. Open the URL, enter the code,
and authenticate in your browser. No password is ever stored.

#### Gmail (IMAP with app password)

```bash
horai --email user@gmail.com --name gmail-backup --imap
```

Gmail requires an **app password** — generate one at
[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

#### Fastmail / Yahoo / iCloud

```bash
horai --email user@fastmail.com --name fastmail-backup --imap
horai --email user@yahoo.com    --name yahoo-backup    --imap
horai --email user@icloud.com   --name icloud-backup   --imap
```

The IMAP server is detected automatically from the domain.

#### Custom IMAP server

```bash
horai --email user@example.com --name custom-backup \
      --imap --host imap.example.com --port 993
```

#### Resume an interrupted dump

```bash
horai --email user@company.com --name company-backup --resume
```

Folders already completed are skipped. The work state is stored in a temporary
`.work_<name>_<date>/` directory and cleaned up automatically on success.

#### Dump specific folders only

```bash
horai --email user@company.com --name inbox-only \
      --folders INBOX "Sent Items" "Archive"
```

#### Write archive to a specific directory

```bash
horai --email user@company.com --name company-backup --output /mnt/nas/backups/
```

---

### All Options

| Option | Default | Description |
|---|---|---|
| `--email` | *(required)* | Email address to dump |
| `--name` | *(required)* | Base name for the archive file |
| `--imap` | off | Use IMAP login/password instead of M365 OAuth2 |
| `--host` | auto | IMAP server hostname |
| `--port` | 993 | IMAP port |
| `--password` | prompted | IMAP password (or app password) |
| `--output` | `.` | Output directory for the archive |
| `--resume` | off | Skip folders already completed |
| `--folders` | all | Dump only the listed folders |

---

### Output Format

The archive follows a simple, transparent structure:

```
company-backup_2026-04-01.tar.gz
├── INBOX.mbox
├── Sent_Items.mbox
├── Drafts.mbox
├── Archive.mbox
└── ...
```

Each `.mbox` file is the standard Unix mbox format, readable by any email client
(Thunderbird, Mutt, Apple Mail via import, etc.) and by any mail processing tool.
Folder names with spaces or slashes are normalized with underscores.

---

### Import into Hermes

The archive is directly importable into
[Hermes](https://github.com/mikaelmasson/hermes), the self-hosted email archive system.

```bash
# Copy the archive to your Hermes imports volume
cp company-backup_2026-04-01.tar.gz /path/to/hermes/imports/

# Import via CLI
hermes import-archive /imports/company-backup_2026-04-01.tar.gz --name company-backup

# Or import a single mbox file
tar xzf company-backup_2026-04-01.tar.gz
hermes import-file /imports/INBOX.mbox --name company-backup
```

---

### M365 Authentication

Horai uses Microsoft's **OAuth2 device flow** with Thunderbird's well-known
public client ID (`9e5f94bc-e8a4-4e73-b8be-63364c29d753`). This client ID is
public, read-only in scope, and widely used by open-source mail clients.

**First run:** you will be asked to open a URL and enter a short code.
Authentication happens entirely in your browser — Horai never sees your password.

**Subsequent runs:** the access token is cached in `.token_cache_<email>.json`
(permissions `600`) and refreshed silently. Delete this file to force
re-authentication.

No Azure app registration or admin consent is required for personal accounts.
For organizational accounts, your IT administrator must allow the
`IMAP.AccessAsUser.All` permission.

---

### IMAP Authentication

For non-M365 providers, Horai uses standard IMAP LOGIN.

| Provider | Setup required |
|---|---|
| **Gmail** | Enable IMAP in settings, generate an [app password](https://myaccount.google.com/apppasswords) |
| **Yahoo** | Generate an [app password](https://help.yahoo.com/kb/generate-third-party-passwords-sln15241.html) |
| **iCloud** | Generate an [app-specific password](https://support.apple.com/HT204397) |
| **Fastmail** | Use your regular password or create an app password in settings |
| **ProtonMail** | Requires [ProtonMail Bridge](https://proton.me/mail/bridge) running locally |
| **Others** | Use your regular password; specify `--host` if auto-detection fails |

---

### Requirements

- Python 3.10+
- `msal >= 1.20.0` — only required for M365/Office 365 authentication

No other third-party dependencies. All IMAP, mbox, and archive handling uses
the Python standard library.

---

### License

Mozilla Public License 2.0 — see [LICENSE](LICENSE).

You may use, modify, and distribute this software freely. Modifications to
Horai's files must remain under MPL-2.0. It is compatible with GPL and
proprietary projects when used as a standalone tool.

---

## Français

### Fonctionnalités

- **M365 / Office 365** — flux OAuth2 par appareil, aucun mot de passe stocké
- **Tout serveur IMAP** — Gmail, Fastmail, Yahoo, iCloud, hébergement perso...
- **Détection automatique** du serveur IMAP à partir du domaine e-mail
- **Un fichier `.mbox` par dossier**, regroupé dans une archive `.tar.gz`
- **Reprise** des téléchargements interrompus avec `--resume`
- **Sélection de dossiers** avec `--folders`
- **Autonome** — nécessite uniquement Python 3.10+ et `msal` (pour M365)

---

### Démarrage rapide

```bash
# Installation (depuis PyPI)
pip install horai

# Ou exécution directe sans installation
pip install msal          # uniquement pour M365
python horai.py --email user@societe.com --name ma-sauvegarde
```

---

### Exemples d'utilisation

#### Microsoft 365 / Office 365 (OAuth2, recommandé)

```bash
horai --email user@societe.com --name sauvegarde-societe
```

Un lien et un code s'affichent dans le terminal. Ouvrez l'URL, entrez le code
et authentifiez-vous dans votre navigateur. Aucun mot de passe n'est jamais stocké.

#### Gmail (IMAP avec mot de passe d'application)

```bash
horai --email user@gmail.com --name sauvegarde-gmail --imap
```

Gmail exige un **mot de passe d'application** — créez-en un sur
[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

#### Fastmail / Yahoo / iCloud

```bash
horai --email user@fastmail.com --name sauvegarde-fastmail --imap
horai --email user@yahoo.fr     --name sauvegarde-yahoo     --imap
horai --email user@icloud.com   --name sauvegarde-icloud    --imap
```

Le serveur IMAP est détecté automatiquement à partir du domaine.

#### Serveur IMAP personnalisé

```bash
horai --email user@example.com --name sauvegarde-custom \
      --imap --host imap.example.com --port 993
```

#### Reprendre une sauvegarde interrompue

```bash
horai --email user@societe.com --name sauvegarde-societe --resume
```

Les dossiers déjà traités sont ignorés. L'état de progression est conservé dans
un répertoire temporaire `.work_<nom>_<date>/`, supprimé automatiquement à la fin.

#### Sauvegarder uniquement certains dossiers

```bash
horai --email user@societe.com --name boite-de-reception \
      --folders INBOX "Éléments envoyés" "Archive"
```

#### Écrire l'archive dans un répertoire spécifique

```bash
horai --email user@societe.com --name sauvegarde-societe --output /mnt/nas/sauvegardes/
```

---

### Toutes les options

| Option | Défaut | Description |
|---|---|---|
| `--email` | *(obligatoire)* | Adresse e-mail à sauvegarder |
| `--name` | *(obligatoire)* | Nom de base pour le fichier archive |
| `--imap` | désactivé | Utiliser IMAP login/mot de passe au lieu de M365 OAuth2 |
| `--host` | auto | Nom d'hôte du serveur IMAP |
| `--port` | 993 | Port IMAP |
| `--password` | demandé | Mot de passe IMAP (ou mot de passe d'application) |
| `--output` | `.` | Répertoire de destination de l'archive |
| `--resume` | désactivé | Ignorer les dossiers déjà traités |
| `--folders` | tous | Sauvegarder uniquement les dossiers listés |

---

### Format de l'archive

L'archive suit une structure simple et transparente :

```
sauvegarde-societe_2026-04-01.tar.gz
├── INBOX.mbox
├── Elements_envoyes.mbox
├── Brouillons.mbox
├── Archive.mbox
└── ...
```

Chaque fichier `.mbox` est au format mbox Unix standard, lisible par n'importe
quel client de messagerie (Thunderbird, Mutt, Apple Mail via import, etc.) et
par tout outil de traitement de courrier. Les noms de dossiers contenant des
espaces ou des barres obliques sont normalisés avec des tirets bas.

---

### Import dans Hermes

L'archive est directement importable dans
[Hermes](https://github.com/mikaelmasson/hermes), le système d'archivage de courrier
auto-hébergé.

```bash
# Copier l'archive dans le volume d'imports Hermes
cp sauvegarde-societe_2026-04-01.tar.gz /chemin/vers/hermes/imports/

# Import via CLI
hermes import-archive /imports/sauvegarde-societe_2026-04-01.tar.gz --name sauvegarde-societe

# Ou importer un seul fichier mbox
tar xzf sauvegarde-societe_2026-04-01.tar.gz
hermes import-file /imports/INBOX.mbox --name sauvegarde-societe
```

---

### Authentification M365

Horai utilise le **flux OAuth2 par appareil** de Microsoft avec l'identifiant
client public de Thunderbird (`9e5f94bc-e8a4-4e73-b8be-63364c29d753`). Cet
identifiant est public, en lecture seule, et largement utilisé par les clients
de messagerie open-source.

**Première exécution :** une URL et un code court s'affichent. L'authentification
s'effectue entièrement dans votre navigateur — Horai ne voit jamais votre mot
de passe.

**Exécutions suivantes :** le jeton d'accès est mis en cache dans
`.token_cache_<email>.json` (permissions `600`) et renouvelé silencieusement.
Supprimez ce fichier pour forcer une nouvelle authentification.

Aucune inscription d'application Azure ni consentement administrateur n'est
nécessaire pour les comptes personnels. Pour les comptes organisationnels,
votre administrateur IT doit autoriser la permission `IMAP.AccessAsUser.All`.

---

### Authentification IMAP

Pour les fournisseurs autres que M365, Horai utilise le LOGIN IMAP standard.

| Fournisseur | Configuration requise |
|---|---|
| **Gmail** | Activer IMAP dans les paramètres, générer un [mot de passe d'application](https://myaccount.google.com/apppasswords) |
| **Yahoo** | Générer un [mot de passe d'application](https://help.yahoo.com/kb/generate-third-party-passwords-sln15241.html) |
| **iCloud** | Générer un [mot de passe spécifique à l'application](https://support.apple.com/fr-fr/HT204397) |
| **Fastmail** | Utiliser votre mot de passe habituel ou créer un mot de passe d'application dans les paramètres |
| **ProtonMail** | Nécessite [ProtonMail Bridge](https://proton.me/mail/bridge) en cours d'exécution localement |
| **Autres** | Utiliser votre mot de passe habituel ; spécifier `--host` si la détection automatique échoue |

---

### Prérequis

- Python 3.10+
- `msal >= 1.20.0` — requis uniquement pour l'authentification M365/Office 365

Aucune autre dépendance tierce. La gestion IMAP, mbox et des archives utilise
exclusivement la bibliothèque standard Python.

---

### Licence

Mozilla Public License 2.0 — voir [LICENSE](LICENSE).

Vous pouvez utiliser, modifier et distribuer ce logiciel librement. Les
modifications apportées aux fichiers de Horai doivent rester sous MPL-2.0.
Il est compatible avec les projets GPL et propriétaires lorsqu'il est utilisé
comme outil autonome.
