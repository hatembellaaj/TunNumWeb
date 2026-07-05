#!/usr/bin/env python3
"""
create_avatar_video.py
=======================

Génère une courte vidéo (~10 secondes) d'un avatar qui parle en français,
via l'API D-ID (https://www.d-id.com/).

Pourquoi D-ID ?
- API simple (une seule requête HTTP pour créer le "talk").
- Génère la voix ET l'animation labiale en une seule fois (pas besoin de
  faire de la synthèse vocale à part).
- Un compte gratuit offre des crédits d'essai, suffisant pour tester
  quelques vidéos de 10 secondes.
- Pas besoin de GPU local (tout se passe côté cloud D-ID).

--------------------------------------------------------------------------
ÉTAPE 1 — Obtenir une clé API D-ID
--------------------------------------------------------------------------
1. Créez un compte sur https://studio.d-id.com/ (essai gratuit disponible).
2. Allez dans "API keys" (menu du compte) et générez une clé.
3. Copiez la clé, elle ressemble à : "xxxxxxx@yyyy.com:zzzzzzzzzzzzzzzz"
   ou juste un token — D-ID l'utilise comme identifiant en Basic Auth.

--------------------------------------------------------------------------
ÉTAPE 2 — Configurer la clé
--------------------------------------------------------------------------
Ne mettez jamais la clé en dur dans le code. Définissez-la comme variable
d'environnement avant de lancer le script :

    export DID_API_KEY="votre_cle_api_d-id"

--------------------------------------------------------------------------
ÉTAPE 3 — Installer les dépendances
--------------------------------------------------------------------------
    pip install requests --break-system-packages

--------------------------------------------------------------------------
ÉTAPE 4 — Lancer le script
--------------------------------------------------------------------------
    python3 create_avatar_video.py

Par défaut, le script utilise une image d'avatar de démonstration fournie
publiquement par D-ID (utile pour tester sans avoir votre propre photo).
Pour utiliser votre propre avatar, passez l'URL (ou déposez l'image dans un
hébergeur public type imgur/S3) via --source-url, ou modifiez la variable
SOURCE_IMAGE_URL ci-dessous.

Le résultat (fichier .mp4) est téléchargé dans le dossier courant.
"""

import os
import sys
import time
import argparse
import requests

# --------------------------------------------------------------------------
# Configuration par défaut — modifiable en argument de ligne de commande
# --------------------------------------------------------------------------

# Texte prononcé par l'avatar (~10 secondes à un débit naturel en français)
DEFAULT_SCRIPT_TEXT = (
    "Bonjour, je suis l'assistant intelligence artificielle de md.Groupe. "
    "Nous créons des agents IA sur mesure pour automatiser vos contenus, "
    "vos analyses et vos échanges clients."
)

# Image d'avatar par défaut (photo de démonstration publique fournie par D-ID)
DEFAULT_SOURCE_IMAGE_URL = "https://d-id-public-bucket.s3.amazonaws.com/alice.jpg"

# Voix française (Microsoft Azure Neural via D-ID)
DEFAULT_VOICE_ID = "fr-FR-DeniseNeural"

API_BASE_URL = "https://api.d-id.com"
OUTPUT_FILENAME = "avatar_video_fr.mp4"
POLL_INTERVAL_SECONDS = 3
POLL_TIMEOUT_SECONDS = 120


def get_api_key() -> str:
    api_key = os.environ.get("DID_API_KEY")
    if not api_key:
        sys.exit(
            "Erreur : la variable d'environnement DID_API_KEY n'est pas définie.\n"
            "Faites : export DID_API_KEY=\"votre_cle_api_d-id\""
        )
    return api_key


def create_talk(api_key: str, text: str, source_url: str, voice_id: str) -> str:
    """Envoie la demande de génération à D-ID et renvoie l'ID du job."""
    url = f"{API_BASE_URL}/talks"
    payload = {
        "source_url": source_url,
        "script": {
            "type": "text",
            "input": text,
            "provider": {
                "type": "microsoft",
                "voice_id": voice_id,
            },
        },
        "config": {
            "fluent": True,
            "pad_audio": 0,
        },
    }

    response = requests.post(url, json=payload, auth=(api_key, ""))
    if response.status_code not in (200, 201):
        sys.exit(f"Erreur lors de la création du talk : {response.status_code} {response.text}")

    data = response.json()
    talk_id = data.get("id")
    if not talk_id:
        sys.exit(f"Réponse inattendue de l'API : {data}")

    print(f"Talk créé avec l'ID : {talk_id}")
    return talk_id


def poll_talk(api_key: str, talk_id: str) -> str:
    """Interroge l'API jusqu'à ce que la vidéo soit prête, renvoie l'URL du résultat."""
    url = f"{API_BASE_URL}/talks/{talk_id}"
    start_time = time.time()

    while time.time() - start_time < POLL_TIMEOUT_SECONDS:
        response = requests.get(url, auth=(api_key, ""))
        response.raise_for_status()
        data = response.json()
        status = data.get("status")
        print(f"Statut : {status}...")

        if status == "done":
            return data["result_url"]
        if status == "error":
            sys.exit(f"Échec de la génération : {data}")

        time.sleep(POLL_INTERVAL_SECONDS)

    sys.exit("Timeout : la vidéo n'a pas été générée dans le délai imparti.")


def download_video(result_url: str, output_path: str) -> None:
    response = requests.get(result_url, stream=True)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Vidéo téléchargée : {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Génère une vidéo d'avatar parlant en français via D-ID.")
    parser.add_argument("--text", default=DEFAULT_SCRIPT_TEXT, help="Texte à faire prononcer par l'avatar.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_IMAGE_URL, help="URL publique de l'image d'avatar.")
    parser.add_argument("--voice-id", default=DEFAULT_VOICE_ID, help="Voix Microsoft Azure à utiliser (ex: fr-FR-DeniseNeural).")
    parser.add_argument("--output", default=OUTPUT_FILENAME, help="Nom du fichier vidéo de sortie.")
    args = parser.parse_args()

    api_key = get_api_key()

    print("Texte à prononcer :", args.text)
    print("Image source :", args.source_url)
    print("Voix :", args.voice_id)

    talk_id = create_talk(api_key, args.text, args.source_url, args.voice_id)
    result_url = poll_talk(api_key, talk_id)
    download_video(result_url, args.output)


if __name__ == "__main__":
    main()
