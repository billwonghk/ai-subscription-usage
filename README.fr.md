# AI Subscription Usage

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | **Français** | [Deutsch](README.de.md) | [Español](README.es.md)

Une application de barre de menus / de la zone de notification, locale et sans compte, qui lit les journaux d'utilisation stockés sur votre machine pour ChatGPT, Claude Code, Claude Desktop, Gemini CLI et Grok, puis compare la valeur équivalente en API sur 30 jours à ce que vous payez réellement pour chaque abonnement. Tout s'exécute sur votre propre machine — aucune clé API IA, aucune connexion à un compte, aucun accès OAuth/jeton d'authentification/cookie, et aucun service cloud impliqué.

**Fonctionnalités**
- Tableau de bord sur 30 jours : jetons totaux/entrée/sortie, valeur équivalente en API, coût d'abonnement effectif et multiple de valeur, par fournisseur
- Graphiques quotidiens des jetons et du multiple de valeur, détail par modèle
- Historique des plans d'abonnement (mensuel/annuel, calculé au prorata selon la date d'effet)
- Détection automatique des journaux d'utilisation locaux, avec une méthode sécurisée et sur liste blanche pour pointer vers un dossier non par défaut
- Les tarifs des modèles pris en charge sont actualisés automatiquement environ une fois par semaine à partir des données tarifaires publiques de l'API d'[OpenRouter](https://openrouter.ai/) — aucune modification manuelle nécessaire
- Sept langues : English, Français, Deutsch, Español, 简体中文, 日本語, 한국어
- Lancement au démarrage, intervalle d'actualisation réglable, accès en un clic à votre dossier de données locales
- Diagnostics anonymisés uniquement sur consentement explicite — jamais de contenu de conversation, de chemins de fichiers ni d'identifiants

**Captures d'écran**

| Rapport | Paramètres |
| --- | --- |
| ![Tableau de bord du rapport](assets/screenshots/report.png) | ![Panneau des paramètres](assets/screenshots/settings.png) |

Détail par fournisseur (jetons et valeur par modèle), et le même rapport en chinois :

![Détail du fournisseur Claude](assets/screenshots/report-claude-tab.png)
![Rapport en chinois](assets/screenshots/report-zh.png)

**Obtenir l'application**

Téléchargez la dernière version depuis la page [Releases](../../releases) :
- **macOS** : `AI-Subscription-Usage-macOS.zip` — décompressez puis déplacez `AI Subscription Usage.app` dans le dossier Applications.
- **Windows** : `AI-Subscription-Usage-Windows-Setup.exe` pour une installation classique (raccourci dans le menu Démarrer, désinstallation normale), ou `AI-Subscription-Usage-Windows-Portable.zip` si vous préférez simplement décompresser et lancer l'exécutable, sans rien écrire dans le registre ni dans Program Files.

Chaque version est également accompagnée d'un fichier `SHA256SUMS.txt` permettant de vérifier votre téléchargement. La version Windows est compilée et testée automatiquement en intégration continue, mais n'a pas encore été testée manuellement sur une machine Windows physique — voir le tableau ci-dessous.

Vous préférez compiler depuis les sources ?

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/pip install pyinstaller
.venv-desktop/bin/pyinstaller --clean --noconfirm ai-subscription-usage.spec
```

La version macOS est générée dans `dist/AI Subscription Usage.app` ; la version Windows dans `dist/AI Subscription Usage.exe`.

## Ce qui est vérifié à ce jour

| Plateforme | macOS (application + CLI) | Windows (application + CLI) |
| --- | --- | --- |
| ChatGPT | ✅ Fonctionne, vérifié | 🟡 Même logique de code, devrait fonctionner — non testé sur un vrai Windows |
| Claude | ✅ Fonctionne, vérifié (l'application et le CLI partagent le même journal) | 🟡 L'application a un chemin Windows dédié ; le CLI devrait aussi fonctionner — non testé sur un vrai Windows |
| Gemini CLI | ✅ Fonctionne, vérifié | 🟡 Devrait fonctionner — non testé sur un vrai Windows |
| Gemini Desktop (Antigravity/Spark) | ❌ Confirmé impossible | ❌ Probablement impossible aussi (même produit) — non confirmé spécifiquement |
| Grok | 🟡 Le code devrait être correct, mais il n'y a pas de données Grok réelles sur cette machine pour vérifier | 🟡 Également non vérifié, et les tests Windows n'ont pas non plus eu lieu |

Gemini Desktop (Antigravity/Spark) écrit ses fichiers de session locaux sous forme chiffrée (`~/.gemini/antigravity/conversations/*.pb`), sans structure lisible ni API locale sûre et documentée, si bien que l'utilisation de jetons ne peut pas être lue pour ce produit — il apparaît comme détecté mais non tarifé.

Si vous disposez d'une machine Windows, ou si vous utilisez réellement Grok, les tests et retours sont particulièrement bienvenus — ce sont les deux points qui ne peuvent pas être vérifiés ici. Merci d'ouvrir une [Issue](../../issues) en cas de problème.

## Vue d'ensemble

Les numéros de version s'affichent dans le menu de la zone de notification, la page de rapport et la page d'aide. macOS stocke les données utilisateur dans `~/Library/Application Support/AI Subscription Usage/` ; Windows les stocke dans `%LOCALAPPDATA%\AI Subscription Usage\`. Une mise à jour ne remplace que le programme, la base de données tarifaires intégrée, les fichiers de langue et les adaptateurs — les plans d'abonnement, la configuration des sources de données, le choix de langue, le consentement aux diagnostics et les rapports locaux ne sont jamais écrasés par l'installateur. Avant toute migration des paramètres, les fichiers d'origine sont sauvegardés dans `backups/` au sein du dossier de données utilisateur.

La version publique publiée sur GitHub ne contient ni plans d'abonnement, ni résultats de détection, ni chemins absolus locaux, ni comptages de jetons, ni rapports générés — les résultats de détection sont toujours générés en temps réel, sur la machine où l'application est installée. Le workflow de publication exécute d'abord `scripts/privacy_check.py` et interrompt la construction en cas d'échec.

## Sources de données

| Plateforme | Dossier local | Ce qui est comptabilisé |
| --- | --- | --- |
| ChatGPT | `~/.codex/sessions/` | JSONL interne de Codex ; entrée, sortie et entrée en cache |
| Claude Code | `~/.claude/projects/` | Entrée, sortie, lecture de cache et écriture de cache |
| Claude Desktop | `~/Library/Application Support/Claude/local-agent-mode-sessions/` | Détecte les sessions de l'application de bureau ; l'utilisation de jetons est agrégée via le journal JSONL Claude partagé |
| Gemini CLI | `~/.gemini/tmp/*/chats/` | Entrée, sortie, réflexion et jetons en cache |
| Antigravity Desktop | `~/.gemini/antigravity/` | Détection automatique ; non tarifé tant que les champs de jetons du format `.pb` ne sont pas vérifiés |
| Antigravity CLI | `~/.gemini/antigravity-cli/` | Détection automatique ; non tarifé tant que le format n'est pas vérifié |
| Grok Build | `~/.grok/logs/unified.jsonl` | Privilégie la lecture exacte des jetons d'entrée, de sortie, de raisonnement et de cache |
| Source de repli Grok Build | `~/.grok/sessions/**/signals.json` | Utilisée uniquement en l'absence de `unified.jsonl` ; signalée comme une estimation |

Les noms de modèles doivent correspondre exactement à ceux de `config/pricing.json`. Les modèles inconnus continuent d'avoir leurs jetons comptabilisés, mais aucune valeur équivalente en API n'est calculée pour eux, et le tarif d'aucun autre modèle ne leur est appliqué. La base de données tarifaires peut stocker des tarifs différents selon la date d'effet ; les enregistrements historiques utilisent le tarif qui était en vigueur ce jour-là.

## Génération en ligne de commande

```bash
python3 src/ai_usage_report.py --days 30
```

Le résultat est écrit dans `outputs/ai-usage-report.html`. Le bouton « Actualiser les données locales » en haut à droite communique avec le point de terminaison d'actualisation locale que l'application de bureau expose sur `127.0.0.1:17653` ; ce port n'est lié qu'à l'interface locale (loopback) et n'est jamais exposé au réseau local ni à Internet.

## Barre de menus macOS et zone de notification Windows

L'application de bureau propose : ouvrir le rapport, actualiser maintenant, mettre à jour les tarifs des modèles, vérifier les mises à jour de l'application, changer de langue, accéder à la configuration et au guide d'utilisation, activer/désactiver les diagnostics anonymes, et quitter. Au premier lancement, elle ouvre automatiquement la configuration et le guide d'utilisation, qui affiche l'état de détection des sources de données locales, les commandes de diagnostic et une invite de configuration sûre que vous pouvez copier vers votre propre assistant IA local. Par défaut, elle actualise les données locales et vérifie la version de l'application toutes les 24 heures.

## Détection automatique et configuration assistée par IA

L'application ne vérifie que les dossiers par défaut enregistrés — elle ne scanne jamais l'intégralité du disque. Exécutez `AI Subscription Usage --doctor --json` pour voir l'état de détection de ChatGPT, Claude Desktop, Claude Code, Gemini CLI, Antigravity Desktop, Antigravity CLI et Grok. Les dossiers non par défaut se configurent via des commandes contrôlées :

```bash
AI\ Subscription\ Usage --configure-source --provider chatgpt --surface chatgpt-desktop --format codex-jsonl --path "$HOME/.codex/sessions"
AI\ Subscription\ Usage --verify-sources --json
```

`SETUP_WITH_AI.md` peut être confié à votre propre assistant IA local — ChatGPT, Claude Code, Gemini CLI ou autre — qui ne pourra appeler que les commandes de diagnostic en lecture seule et de configuration contrôlée ci-dessus. Le fichier de configuration n'accepte jamais de commandes, d'adresses réseau, d'identifiants ni de code d'analyse arbitraire.

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/python src/desktop_app.py
```

L'application de bureau est un processus de longue durée qui tourne dans la barre de menus ou la zone de notification. Assurez-vous qu'aucun autre programme n'utilise déjà le port `17653` avant de la démarrer ; quitter depuis le menu arrête à la fois l'icône de la zone de notification et le point de terminaison d'actualisation locale.

## Langues multiples

L'interface de bureau intègre des ressources en anglais, français, allemand, espagnol, chinois simplifié, japonais et coréen. Elle suit la langue du système par défaut et peut être changée depuis la page des paramètres. Aucun champ calculé ni aucune donnée tarifaire ne change selon la langue.

## Mises à jour de la base de données tarifaires

`config/pricing.json` stocke la version des tarifs, les sources officielles, les prix des modèles et les dates d'effet. Le client télécharge les mises à jour tarifaires depuis un manifeste, vérifie la somme de contrôle SHA-256 et la structure des champs, puis remplace de façon atomique la base de données tarifaires locale. Cet outil est conçu pour montrer une tendance, pas pour être une référence tarifaire parfaitement précise ; la source de mise à jour est donc constituée par les données tarifaires publiques de l'API d'[OpenRouter](https://openrouter.ai/) — un proxy LLM bien connu dont les tarifs d'API suivent généralement les tarifs officiels.

`config/model_id_map.json` fait correspondre les noms de modèles locaux de ce projet à leur identifiant exact chez OpenRouter. `scripts/fetch_pricing.py` utilise cette correspondance pour récupérer les tarifs actuels et réécrire `config/pricing.json` et `config/pricing-manifest.json` ; `.github/workflows/update-pricing.yml` l'exécute automatiquement environ une fois par semaine et ne valide (commit) que si un tarif a réellement changé. Un changement de tarif réel est enregistré comme une nouvelle période datée, afin que les dates de rapport passées continuent d'utiliser le tarif réellement en vigueur à l'époque. Les modèles disposant déjà d'un calendrier daté renseigné manuellement ne sont pas modifiés par cette automatisation. Lorsque les journaux d'utilisation révèlent un tout nouveau nom de modèle absent de la correspondance, il est simplement affiché comme non tarifé jusqu'à ce qu'une ligne soit ajoutée à `config/model_id_map.json` — l'application de bureau tente également une actualisation immédiate des tarifs dès qu'elle détecte un nouveau modèle.

L'onglet de détail de chaque fournisseur affiche aussi son taux de succès du cache pour la période, ainsi qu'un coût estimé si la même utilisation avait tourné sur [DeepSeek](https://www.deepseek.com/). Chaque modèle est associé à un niveau DeepSeek V4 Flash ou Pro selon sa capacité (voir `config/deepseek_tier_map.json`), en utilisant les tarifs publics propres à DeepSeek (également tenus à jour via OpenRouter) et la répartition réelle succès/échec du cache pour cette période — pas un ratio estimé. Les modèles haut de gamme sans véritable équivalent chez DeepSeek sont tout de même comparés au niveau Pro, délibérément en faveur de DeepSeek, afin que la comparaison ne soit jamais exagérée.

## Diagnostics anonymes

Les diagnostics anonymes sont désactivés par défaut et ne sont envoyés qu'après activation explicite dans les paramètres. Les champs autorisés se limitent à : la version de l'application, le système d'exploitation, la langue, le module en erreur, le type d'erreur, une trace de pile anonymisée et l'état des adaptateurs. Ne sont jamais envoyés : le contenu des conversations, les invites, les réponses, les noms d'utilisateur, les chemins de fichiers locaux, les clés API, les détails d'abonnement, le détail des jetons ou les journaux bruts. Le `telemetry_endpoint` sera renseigné une fois le service de réception des diagnostics publié.

## Publications automatiques

`.github/workflows/release.yml` exécute les tests après la publication d'un tag de version, construit les artefacts macOS et Windows, génère les sommes de contrôle SHA-256 et crée une GitHub Release. Des mises à jour entièrement automatiques nécessitent en plus une adresse de dépôt GitHub, un Developer ID macOS, des identifiants de notarisation et un certificat de signature de code Windows.

## Licence

Ce projet est publié sous licence [PolyForm Noncommercial 1.0.0](LICENSE) — libre d'utilisation, d'étude, de modification et de partage pour tout usage non commercial. L'usage commercial n'est pas autorisé. Des questions sur la licence, ou sur un cas d'usage particulier ? Ouvrez une [Issue](../../issues). Le code tiers réutilisé doit néanmoins voir sa licence, sa mention de droits d'auteur et son origine consignées dans `THIRD_PARTY_NOTICES.md`.
