#!/usr/bin/env python3
"""
create_avatar_video_free.py
============================

Génère une vidéo (~10 secondes) d'un avatar simple qui "parle" en français,
100% GRATUIT, SANS CLÉ API, SANS COMPTE, SANS CARTE BANCAIRE.

Comment ça marche (tout tourne en local sur votre machine) :
1. La voix française est générée avec "edge-tts" — un outil open-source qui
   utilise le moteur de synthèse vocale gratuit de Microsoft Edge. Aucune
   inscription, aucune clé, aucune limite de crédit.
2. Un avatar très simple (visage dessiné, façon "smiley") est généré par le
   script lui-même avec Pillow — donc pas besoin d'avoir déjà une image
   d'avatar.
3. La bouche de l'avatar s'ouvre et se ferme automatiquement en fonction du
   volume de la voix (analyse de l'amplitude audio), frame par frame.
4. Tout est assemblé en vidéo .mp4 avec moviepy.

Ce n'est PAS un avatar photoréaliste (type D-ID/HeyGen/Synthesia) : le
rendu est volontairement simple ("cartoon"), mais gratuit à 100% et sans
aucune limite d'usage.

--------------------------------------------------------------------------
INSTALLATION (une seule fois)
--------------------------------------------------------------------------
1. Installer ffmpeg (nécessaire pour l'audio et la vidéo) :
   - macOS   : brew install ffmpeg
   - Debian/Ubuntu : sudo apt-get install ffmpeg

2. Installer les librairies Python :
   pip install edge-tts pydub pillow numpy moviepy --break-system-packages

--------------------------------------------------------------------------
UTILISATION
--------------------------------------------------------------------------
   python3 create_avatar_video_free.py

Options :
   python3 create_avatar_video_free.py --text "Votre texte ici" --output ma_video.mp4

Le fichier vidéo est généré dans le dossier courant.
"""

import argparse
import asyncio
import sys
import tempfile
import os

import numpy as np
from PIL import Image, ImageDraw

try:
    from moviepy.editor import ImageSequenceClip, AudioFileClip
except ImportError:
    from moviepy import ImageSequenceClip, AudioFileClip

try:
    import edge_tts
except ImportError:
    sys.exit("Le module 'edge-tts' n'est pas installé. Faites : pip install edge-tts --break-system-packages")

try:
    from pydub import AudioSegment
except ImportError:
    sys.exit("Le module 'pydub' n'est pas installé. Faites : pip install pydub --break-system-packages")


# --------------------------------------------------------------------------
# Paramètres par défaut
# --------------------------------------------------------------------------

DEFAULT_TEXT = (
    "Bonjour, je suis l'assistant intelligence artificielle de md.Groupe. "
    "Nous créons des agents IA sur mesure pour automatiser vos contenus, "
    "vos analyses et vos échanges clients."
)
VOICE = "fr-FR-DeniseNeural"   # voix française gratuite (edge-tts / Microsoft Edge)
FPS = 24
WIDTH, HEIGHT = 720, 720
FACE_COLOR = (255, 213, 170)
OUTLINE_COLOR = (40, 30, 20)
BG_COLOR = (17, 17, 20)
ACCENT_COLOR = (239, 35, 60)   # rouge md.Groupe, utilisé pour le noeud papillon


async def generate_speech(text: str, voice: str, output_mp3: str) -> None:
    """Génère la voix française avec edge-tts (gratuit, sans clé API)."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_mp3)


def compute_mouth_amplitudes(mp3_path: str, fps: int):
    """Découpe l'audio en tranches (une par frame vidéo) et calcule le volume
    (RMS) de chaque tranche, normalisé entre 0 (silence) et 1 (fort)."""
    audio = AudioSegment.from_file(mp3_path)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    duration = audio.duration_seconds
    frame_count = max(1, int(duration * fps))
    samples_per_frame = max(1, len(samples) // frame_count)

    amplitudes = []
    for i in range(frame_count):
        start = i * samples_per_frame
        end = start + samples_per_frame
        chunk = samples[start:end]
        rms = np.sqrt(np.mean(chunk ** 2)) if len(chunk) else 0.0
        amplitudes.append(rms)

    amplitudes = np.array(amplitudes)
    max_amp = amplitudes.max() if amplitudes.max() > 0 else 1.0
    normalized = np.clip(amplitudes / max_amp, 0, 1)
    return normalized, duration


def draw_avatar_frame(mouth_openness: float, blink: bool) -> Image.Image:
    """Dessine une frame de l'avatar (visage simple + bouche qui bouge)."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    cx, cy = WIDTH // 2, HEIGHT // 2
    head_radius = 220

    # Tête
    draw.ellipse(
        [cx - head_radius, cy - head_radius, cx + head_radius, cy + head_radius],
        fill=FACE_COLOR, outline=OUTLINE_COLOR, width=6,
    )

    # Yeux
    eye_y = cy - 60
    eye_h = 8 if blink else 34
    for ex in (cx - 85, cx + 85):
        draw.ellipse([ex - 26, eye_y - eye_h, ex + 26, eye_y + eye_h], fill=(30, 30, 30))

    # Sourcils
    for ex in (cx - 85, cx + 85):
        draw.line([ex - 30, eye_y - 55, ex + 30, eye_y - 62], fill=OUTLINE_COLOR, width=6)

    # Bouche (hauteur variable selon l'amplitude audio = "lip-sync" simplifié)
    mouth_w = 100
    min_h, max_h = 6, 55
    mouth_h = min_h + mouth_openness * (max_h - min_h)
    mouth_y = cy + 90
    draw.ellipse(
        [cx - mouth_w, mouth_y - mouth_h, cx + mouth_w, mouth_y + mouth_h],
        fill=(120, 40, 40), outline=OUTLINE_COLOR, width=4,
    )

    # Petit noeud papillon "md.Groupe" pour la touche finale
    draw.polygon(
        [(cx - 60, cy + head_radius - 10), (cx, cy + head_radius + 30), (cx - 60, cy + head_radius + 70)],
        fill=ACCENT_COLOR,
    )
    draw.polygon(
        [(cx + 60, cy + head_radius - 10), (cx, cy + head_radius + 30), (cx + 60, cy + head_radius + 70)],
        fill=ACCENT_COLOR,
    )

    return img


def build_video(amplitudes, duration: float, audio_path: str, output_path: str, fps: int):
    frames = []
    blink_every = int(fps * 2.5)  # un clignement toutes les ~2.5 secondes

    for i, amp in enumerate(amplitudes):
        blink = (i % blink_every) in (0, 1)
        frame_img = draw_avatar_frame(mouth_openness=float(amp), blink=blink)
        frames.append(np.array(frame_img))

    clip = ImageSequenceClip(frames, fps=fps)
    audio_clip = AudioFileClip(audio_path)

    # Compatibilité moviepy 1.x (set_audio/set_duration) et 2.x (with_audio/with_duration)
    clip = clip.set_audio(audio_clip) if hasattr(clip, "set_audio") else clip.with_audio(audio_clip)
    clip = clip.set_duration(duration) if hasattr(clip, "set_duration") else clip.with_duration(duration)

    clip.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac", logger=None)


def main():
    parser = argparse.ArgumentParser(description="Génère une vidéo d'avatar parlant en français, 100% gratuit.")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Texte à faire prononcer par l'avatar.")
    parser.add_argument("--voice", default=VOICE, help="Voix edge-tts à utiliser (ex: fr-FR-DeniseNeural, fr-FR-HenriNeural).")
    parser.add_argument("--output", default="avatar_video_fr.mp4", help="Nom du fichier vidéo de sortie.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp_dir:
        mp3_path = os.path.join(tmp_dir, "speech.mp3")

        print("1/3 — Génération de la voix française (edge-tts)...")
        asyncio.run(generate_speech(args.text, args.voice, mp3_path))

        print("2/3 — Analyse de l'audio pour synchroniser la bouche...")
        amplitudes, duration = compute_mouth_amplitudes(mp3_path, FPS)

        print(f"3/3 — Génération de la vidéo ({duration:.1f}s)...")
        build_video(amplitudes, duration, mp3_path, args.output, FPS)

    print(f"Terminé ! Vidéo générée : {args.output}")


if __name__ == "__main__":
    main()
