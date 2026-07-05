#!/usr/bin/env python3
"""
create_avatar_video_photo.py
=============================

Génère une vidéo (~10 secondes) où VOTRE PHOTO parle en français,
100% gratuit, sans clé API, sans carte bancaire.

Pipeline :
1. La voix française est générée avec "edge-tts" (gratuit, sans compte).
2. L'audio est converti en .wav avec ffmpeg.
3. SadTalker (open-source) anime votre photo à partir de cet audio :
   bouche synchronisée + léger mouvement de tête.

--------------------------------------------------------------------------
PRÉREQUIS (à faire une seule fois)
--------------------------------------------------------------------------
1. Avoir installé SadTalker avec le script fourni :
       PYTHON=~/.pyenv/versions/3.11.5/bin/python3 ./setup_sadtalker.sh

2. Avoir ffmpeg installé :
       brew install ffmpeg

3. Activer l'environnement virtuel créé par le setup :
       source sadtalker_env/bin/activate

4. Installer edge-tts dans ce même environnement :
       pip install edge-tts

--------------------------------------------------------------------------
UTILISATION
--------------------------------------------------------------------------
   python3 create_avatar_video_photo.py --image chemin/vers/votre_photo.jpg

Options utiles :
   --text "Votre texte ici"      (texte prononcé, ~10 secondes par défaut)
   --voice fr-FR-HenriNeural      (voix masculine, au lieu de fr-FR-DeniseNeural)
   --sadtalker-dir ./SadTalker    (si le dossier SadTalker n'est pas à côté de ce script)
   --output-dir ./resultats       (dossier où sera écrite la vidéo finale)

La vidéo finale se trouve dans le dossier de résultats indiqué par SadTalker
à la fin de l'exécution (un sous-dossier horodaté contenant un .mp4).
"""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile

try:
    import edge_tts
except ImportError:
    sys.exit("Le module 'edge-tts' n'est pas installé dans cet environnement. Faites : pip install edge-tts")


DEFAULT_TEXT = (
    "Bonjour, je suis heureux de vous présenter les solutions d'intelligence "
    "artificielle de md.Groupe, conçues pour automatiser vos contenus et vos analyses."
)
DEFAULT_VOICE = "fr-FR-HenriNeural"  # voix masculine française (gratuite, edge-tts)


async def generate_speech(text: str, voice: str, output_mp3: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_mp3)


def convert_to_wav(mp3_path: str, wav_path: str) -> None:
    """Convertit le mp3 en wav avec ffmpeg (nécessaire pour SadTalker)."""
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, wav_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        sys.exit(
            "Erreur ffmpeg lors de la conversion mp3 -> wav.\n"
            "Vérifiez que ffmpeg est installé (brew install ffmpeg).\n"
            f"Détail : {result.stderr.decode(errors='ignore')}"
        )


def run_sadtalker(image_path: str, audio_wav_path: str, sadtalker_dir: str, output_dir: str) -> None:
    """Lance l'inférence SadTalker en sous-processus."""
    sadtalker_dir_abs = os.path.abspath(sadtalker_dir)
    inference_script = os.path.join(sadtalker_dir_abs, "inference.py")
    if not os.path.isfile(inference_script):
        sys.exit(
            f"Introuvable : {inference_script}\n"
            "Vérifiez que SadTalker a bien été installé avec setup_sadtalker.sh, "
            "et que --sadtalker-dir pointe vers le bon dossier."
        )

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        sys.executable, inference_script,
        "--driven_audio", os.path.abspath(audio_wav_path),
        "--source_image", os.path.abspath(image_path),
        "--result_dir", os.path.abspath(output_dir),
        "--still",
        "--preprocess", "full",
    ]

    print("Lancement de SadTalker (cela peut prendre plusieurs minutes sur CPU)...")
    print(" ".join(cmd))

    result = subprocess.run(cmd, cwd=sadtalker_dir_abs)
    if result.returncode != 0:
        sys.exit("SadTalker a rencontré une erreur (voir les logs ci-dessus).")


def main():
    parser = argparse.ArgumentParser(description="Anime une photo pour créer une vidéo qui parle en français.")
    parser.add_argument("--image", required=True, help="Chemin vers la photo (visage de face, bien éclairé).")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Texte à faire prononcer.")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Voix edge-tts (ex: fr-FR-DeniseNeural, fr-FR-HenriNeural).")
    parser.add_argument("--sadtalker-dir", default="./SadTalker", help="Dossier où SadTalker est installé.")
    parser.add_argument("--output-dir", default="./resultats", help="Dossier de sortie pour la vidéo générée.")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        sys.exit(f"Image introuvable : {args.image}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        mp3_path = os.path.join(tmp_dir, "speech.mp3")
        wav_path = os.path.join(tmp_dir, "speech.wav")

        print("1/3 — Génération de la voix française (edge-tts)...")
        asyncio.run(generate_speech(args.text, args.voice, mp3_path))

        print("2/3 — Conversion audio (mp3 -> wav)...")
        convert_to_wav(mp3_path, wav_path)

        print("3/3 — Animation de la photo avec SadTalker...")
        run_sadtalker(args.image, wav_path, args.sadtalker_dir, args.output_dir)

    print(f"Terminé ! Regardez dans le dossier : {args.output_dir}")


if __name__ == "__main__":
    main()
