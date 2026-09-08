# AI Subscription Usage

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | **Français** | [Deutsch](README.de.md) | [Español](README.es.md)

Application locale de barre de menus ou de zone de notification, sans compte, qui lit les journaux pris en charge de ChatGPT, Claude Code, Claude Desktop, Gemini CLI, Grok et MiniMax, puis compare la valeur API des 30 derniers jours au prix réellement payé. Kimi, GLM et Alibaba Bailian sont détectés mais ne sont pas comptés avant validation de leur format local. Tout s'exécute sur la machine : aucune clé API IA, connexion de compte, donnée OAuth/Auth Token/Cookie ni service cloud.

⭐ Si cet outil vous a aidé à savoir si votre abonnement IA en vaut vraiment la peine, un Star aide d'autres personnes à le trouver.

📺 **Démo vidéo :** [YouTube](https://youtu.be/VXnwn82lOsc) · [Bilibili](https://www.bilibili.com/video/BV1kN8h6NEQy/)

**Fonctionnalités**
- Tableau de bord sur 30 jours : jetons totaux/entrée/sortie, valeur équivalente en API, coût d'abonnement effectif et multiple de valeur, par fournisseur
- Graphiques quotidiens des jetons et du multiple de valeur, détail par modèle
- Historique des plans d'abonnement (mensuel/annuel, calculé au prorata selon la date d'effet)
- Ajout ou retrait des fournisseurs surveillés ; un fournisseur retiré n'est ni lu, ni calculé, ni affiché
- Saisie et affichage des abonnements en USD ou CNY, avec conversion selon les taux de référence quotidiens de la BCE
- Lecture du compteur local MiniMax ; Kimi, GLM et Alibaba Bailian restent en détection seule tant que leur format n'est pas vérifié
- Détection automatique des journaux d'utilisation locaux, avec une méthode sécurisée et sur liste blanche pour pointer vers un dossier non par défaut
- Les tarifs des modèles pris en charge sont actualisés automatiquement environ une fois par semaine à partir des données tarifaires publiques de l'API d'[OpenRouter](https://openrouter.ai/) — aucune modification manuelle nécessaire
- Sept langues : English, Français, Deutsch, Español, 简体中文, 日本語, 한국어
- Lancement au démarrage, actualisation automatique quotidienne à 03:00, rattrapage 15 minutes après le lancement si nécessaire, accès en un clic au dossier de données locales
- Diagnostics anonymisés uniquement sur consentement explicite — jamais de contenu de conversation, de chemins de fichiers ni d'identifiants


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
| MiniMax | ✅ Table locale de comptage vérifiée sur macOS | 🟡 Analyseur implémenté, non testé sur un vrai Windows |
| Kimi / GLM / Alibaba Bailian | 🟡 Installation et fichiers locaux détectés ; aucune analyse avant validation du format | 🟡 Même état de détection seule, non testé sur un vrai Windows |

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
| MiniMax | `~/.minimax/sqlite.db` | Jetons exacts d'entrée, sortie, raisonnement, lecture et écriture du cache issus du compteur local |
| Kimi / GLM / Alibaba Bailian | Dossiers par défaut enregistrés | Détection seule ; aucune utilisation comptée avant validation du format |

Les noms de modèles doivent correspondre exactement à ceux de `config/pricing.json`. Les modèles inconnus continuent d'avoir leurs jetons comptabilisés, mais aucune valeur équivalente en API n'est calculée pour eux, et le tarif d'aucun autre modèle ne leur est appliqué. La base de données tarifaires peut stocker des tarifs différents selon la date d'effet ; les enregistrements historiques utilisent le tarif qui était en vigueur ce jour-là.

## Génération en ligne de commande

```bash
python3 src/ai_usage_report.py --days 30
```

Le résultat est écrit dans `outputs/ai-usage-report.html`. Le bouton « Actualiser les données locales » en haut à droite communique avec le point de terminaison d'actualisation locale que l'application de bureau expose sur `127.0.0.1:17653` ; ce port n'est lié qu'à l'interface locale (loopback) et n'est jamais exposé au réseau local ni à Internet.

## Barre de menus macOS et zone de notification Windows

Un clic gauche sur l'icône de la barre de menus ouvre ou réutilise immédiatement le rapport existant sans l'actualiser. Lors de la première installation, un rapport initial est créé uniquement s'il n'en existe aucun. Ensuite, les données sont actualisées une fois par jour à 03:00, heure locale. Si cette actualisation a été manquée, elle est exécutée 15 minutes après le prochain lancement, sauf si une actualisation a déjà réussi ce jour-là. « Actualiser maintenant » reste disponible et compte comme l'actualisation du jour en cas de succès. La vérification de version conserve son intervalle de 24 heures.

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

`config/model_id_map.json` relie les noms locaux aux identifiants exacts d'OpenRouter. Environ une fois par semaine, `scripts/fetch_pricing.py` récupère les prix courants et ne met à jour les fichiers de prix et le manifeste vérifié qu'en cas de changement. Les modèles provenant d'OpenRouter restent actualisables après la création d'un historique daté : un changement clôt la période courante et en ouvre une nouvelle le jour même, sans modifier les tarifs appliqués aux jours passés. Les entrées gérées depuis une autre source déclarée ne sont pas écrasées. Un nouveau modèle conserve ses jetons mais reste sans prix jusqu'à validation de sa correspondance et de son tarif public.

L'onglet de détail de chaque fournisseur affiche aussi son taux de succès du cache pour la période, ainsi qu'un coût estimé si la même utilisation avait tourné sur [DeepSeek](https://www.deepseek.com/). Chaque modèle est associé à un niveau DeepSeek V4 Flash ou Pro selon sa capacité (voir `config/deepseek_tier_map.json`), en utilisant les tarifs publics propres à DeepSeek (également tenus à jour via OpenRouter) et la répartition réelle succès/échec du cache pour cette période — pas un ratio estimé. Les modèles haut de gamme sans véritable équivalent chez DeepSeek sont tout de même comparés au niveau Pro, délibérément en faveur de DeepSeek, afin que la comparaison ne soit jamais exagérée.

## Diagnostics anonymes

Les diagnostics anonymes sont désactivés par défaut et ne sont envoyés qu'après activation explicite dans les paramètres. Les champs autorisés se limitent à : la version de l'application, le système d'exploitation, la langue, le module en erreur, le type d'erreur, une trace de pile anonymisée et l'état des adaptateurs. Ne sont jamais envoyés : le contenu des conversations, les invites, les réponses, les noms d'utilisateur, les chemins de fichiers locaux, les clés API, les détails d'abonnement, le détail des jetons ou les journaux bruts. Le `telemetry_endpoint` sera renseigné une fois le service de réception des diagnostics publié.

## Publications automatiques

`.github/workflows/release.yml` exécute les tests après la publication d'un tag de version, construit les artefacts macOS et Windows, génère les sommes de contrôle SHA-256 et crée une GitHub Release. Des mises à jour entièrement automatiques nécessitent en plus une adresse de dépôt GitHub, un Developer ID macOS, des identifiants de notarisation et un certificat de signature de code Windows.

## Licence

Ce projet est publié sous licence [PolyForm Noncommercial 1.0.0](LICENSE) — libre d'utilisation, d'étude, de modification et de partage pour tout usage non commercial. L'usage commercial n'est pas autorisé. Des questions sur la licence, ou sur un cas d'usage particulier ? Ouvrez une [Issue](../../issues). Le code tiers réutilisé doit néanmoins voir sa licence, sa mention de droits d'auteur et son origine consignées dans `THIRD_PARTY_NOTICES.md`.
