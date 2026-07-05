#!/bin/bash
# ---------------------------------------------------------------------------
# setup_sadtalker.sh
# ---------------------------------------------------------------------------
# Installe SadTalker (outil open-source gratuit, sans clé API, sans carte)
# qui anime une photo réelle (bouche + tête) à partir d'un fichier audio.
#
# IMPORTANT : utilisez une version de Python 3.8 à 3.11 (PAS 3.13/3.14, qui
# ont supprimé des modules dont dépendent les librairies de Machine Learning
# utilisées ici). Sur votre Mac, vous avez déjà Python 3.11.5 via pyenv :
#   ~/.pyenv/versions/3.11.5/bin/python3
#
# Utilisation :
#   chmod +x setup_sadtalker.sh
#   PYTHON=~/.pyenv/versions/3.11.5/bin/python3 ./setup_sadtalker.sh
# ---------------------------------------------------------------------------

set -e

PYTHON="${PYTHON:-python3}"

echo "Interpreteur Python utilise : $($PYTHON --version)"

if [ ! -d "SadTalker" ]; then
    echo "Clonage de SadTalker..."
    git clone https://github.com/OpenTalker/SadTalker.git
else
    echo "SadTalker deja clone, on passe."
fi

cd SadTalker

echo "Creation d'un environnement virtuel dedie (sadtalker_env)..."
# --system-site-packages : reutilise les paquets deja installes sur le systeme
# (torch, numpy, etc. si presents) pour eviter de les retelecharger et
# economiser de l'espace disque.
$PYTHON -m venv --system-site-packages ../sadtalker_env
source ../sadtalker_env/bin/activate

echo "Installation des dependances (cela peut prendre plusieurs minutes)..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Telechargement des modeles pre-entraines (~2 Go, une seule fois)..."
bash scripts/download_models.sh

echo ""
echo "Installation terminee."
echo "Pour generer une video, utilisez ensuite :"
echo "  source sadtalker_env/bin/activate"
echo "  python3 create_avatar_video_photo.py --image votre_photo.jpg"
