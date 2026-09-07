# HistoSpec — Spécification d'histogramme (FastAPI)

Application web pédagogique de traitement d'image construite avec **FastAPI**,
centrée sur la **spécification d'histogramme** (histogram matching) et
enrichie de fonctionnalités connexes directement inspirées du support de
cours *"Analyse d'Image"* (Axe Génie des Procédés, Ecole des Mines de
Saint-Étienne) : seuillage, morphologie mathématique et mesures
granulométriques.

## Fonctionnalités

| Domaine | Fonctionnalités | Référence dans le cours |
|---|---|---|
| Histogramme | Calcul, statistiques (moyenne, écart-type, entropie, asymétrie...) | §2.2, §5.5, §5.6 |
| Histogramme | **Égalisation** (mise à plat) | cas particulier de la spécification |
| Histogramme | **Spécification par image de référence** (matching CDF) | — |
| Histogramme | **Spécification par profil théorique** (gaussien, exponentiel, bimodal, uniforme) | — |
| Images couleur | Upload conserve la couleur (RVB) ; égalisation et spécification appliquées **canal par canal** (R, V, B indépendants) | — |
| Seuillage | Seuillage manuel (bornes basse/haute) et automatique (Otsu) | §3.1 |
| Morphologie | Érosion, dilatation, ouverture, fermeture | §3.2.2.1, §3.2.2.3 |
| Morphologie | Gradient morphologique, chapeau haut de forme | §3.5.2 |
| Morphologie | Squelette (amincissements successifs, Zhang-Suen) | §3.2.2.5 |
| Mesures | Dénombrement (composantes connexes) | §5.2 |
| Mesures | Granulométrie en nombre, compacité, diamètre équivalent | §5.3, §5.3.4 |
| Mesures | Paramètres de forme (circularité) | §5.4 |

## Architecture

```
histospec/
├── app/
│   ├── main.py                  # point d'entrée FastAPI
│   ├── schemas.py                # modèles Pydantic (requêtes/réponses)
│   ├── routers/
│   │   ├── images.py             # upload / récupération PNG / stats
│   │   ├── histogram.py          # égalisation, spécification, seuillage
│   │   ├── morphology.py         # érosion, dilatation, gradient, squelette...
│   │   └── measurements.py       # dénombrement, granulométrie
│   ├── services/
│   │   ├── histogram_service.py  # algorithmes histogramme (numpy pur)
│   │   ├── morphology_service.py # algorithmes morphologiques (numpy pur)
│   │   ├── measurement_service.py# composantes connexes, mesures
│   │   └── store.py              # cache mémoire des images de session
│   ├── templates/index.html      # interface web (SPA légère, Tailwind CSS)
│   └── static/                   # CSS (Tailwind précompilé) + JS (fetch API, Chart.js embarqué)
├── requirements.txt
└── README.md
```

## Interface web

L'interface (`app/templates/index.html`) est stylée avec **Tailwind CSS**,
compilé à l'avance en un fichier statique (`app/static/css/tailwind.css`) —
il n'y a donc **aucune dépendance à un CDN externe** au chargement de la
page : l'application fonctionne hors-ligne (utile en salle de TP sans
accès internet garanti). Chart.js est embarqué de la même façon
(`app/static/js/vendor/chart.umd.min.js`).

Si vous modifiez les classes Tailwind dans `index.html` ou `app.js` et
que le rendu ne suit pas, il faut recompiler le CSS :

```bash
npm install -D tailwindcss@3
npx tailwindcss -i ./tailwind.input.css -o app/static/css/tailwind.css --minify
```

(un `tailwind.config.js` type est fourni ci-dessous à placer à la racine
du projet si vous ne l'avez pas conservé) :

```js
module.exports = {
  content: ["app/templates/**/*.html", "app/static/js/*.js"],
  theme: {
    extend: {
      colors: {
        ink: "#0b0e14", panel: "#10141c", panel2: "#161b26", line: "#232a3a",
        amber: { DEFAULT: "#e7a94c", dim: "#8a6a3a" },
        teal: { DEFAULT: "#4fc9b8", dim: "#2f6d64" },
        rose: { DEFAULT: "#e2687e", dim: "#7a3844" },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Consolas", "Menlo", "monospace"],
      },
    },
  },
};
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate #windows
pip install -r requirements.txt
```

## Lancement

```bash
uvicorn app.main:app --reload
```

- Interface web : http://127.0.0.1:8000/
- Documentation interactive (Swagger) : http://127.0.0.1:8000/docs
- Documentation alternative (ReDoc) : http://127.0.0.1:8000/redoc

## Utilisation rapide (API)

```bash
# 1. Uploader une image
curl -F "file=@mon_image.png" http://127.0.0.1:8000/api/images/upload
# -> {"image_id": "abcdef123456", ...}

# 2. Spécifier son histogramme selon un profil gaussien
curl -X POST http://127.0.0.1:8000/api/histogram/specify/profile \
     -H "Content-Type: application/json" \
     -d '{"image_id": "abcdef123456", "profile": "gaussian", "mean": 128, "std": 35}'

# 3. Récupérer l'image résultat
curl http://127.0.0.1:8000/api/images/<result_image_id>/png -o resultat.png
```

## Principe de la spécification d'histogramme

1. Calcul de l'histogramme et de la fonction de répartition cumulée
   (CDF) de l'image source.
2. Calcul de la CDF de la distribution cible (image de référence ou
   profil théorique).
3. Construction d'une table de correspondance (LUT) associant à chaque
   niveau de gris source le niveau de la cible dont la CDF est la plus
   proche.
4. Application de la LUT à l'image, pixel par pixel.

L'égalisation d'histogramme est un cas particulier de cette méthode où
la distribution cible est uniforme.

## Images couleur

Une image chargée en couleur (RVB) est conservée telle quelle : le
serveur garde à la fois le tableau couleur (H×L×3) et sa luminance 2D
(pondération ITU-R BT.601, `0.299 R + 0.587 V + 0.114 B`).

- **Égalisation et spécification d'histogramme** (par profil ou par
  référence) s'appliquent **indépendamment à chacun des trois canaux**
  R, V, B, puis les canaux traités sont recombinés — le résultat reste
  une image couleur. Si l'image de référence est elle-même couleur,
  chaque canal est mis en correspondance avec le canal de même nom
  (R→R, V→V, B→B) ; si elle est en niveaux de gris, les trois canaux de
  la source sont mis en correspondance avec cette même distribution de
  luminance.
- **Seuillage et morphologie mathématique** n'ont de sens que sur une
  image binaire / en niveaux de gris : sur une source couleur, ils
  s'appliquent toujours à sa luminance et produisent un résultat en
  niveaux de gris (l'API renvoie une note explicite dans ce cas).
- Une image déjà en niveaux de gris continue de suivre exactement le
  comportement d'origine (aucun changement de résultat).

## Limites connues / pistes d'évolution

- Le stockage des images est en mémoire (dictionnaire Python) : il est
  réinitialisé à chaque redémarrage du serveur et ne convient pas à un
  déploiement multi-worker sans adaptation (Redis, disque partagé...).
- Les algorithmes morphologiques et de granulométrie sont implémentés
  "from scratch" en numpy à des fins pédagogiques ; pour de grandes
  images ou une utilisation intensive, une librairie optimisée (OpenCV,
  scikit-image) serait plus performante.

## Licence

Projet pédagogique fourni tel quel, sans garantie.
