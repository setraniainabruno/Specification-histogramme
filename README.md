# HistoSpec — Spécification d'histogramme (FastAPI)

Application web pédagogique de traitement d'image construite avec **FastAPI**,
centrée sur la **spécification d'histogramme** (histogram matching) et
enrichie de fonctionnalités connexes directement inspirées du support de
cours *"Analyse d'Image"* (Axe Génie des Procédés, Ecole des Mines de
Saint-Étienne) : seuillage, morphologie mathématique et mesures
granulométriques.

## Fonctionnalités

| Domaine | Fonctionnalités |
|---|---|
| Histogramme | Calcul, statistiques (moyenne, écart-type, entropie, asymétrie...) |
| Histogramme | **Égalisation** (mise à plat) | cas particulier de la spécification |
| Histogramme | **Spécification par image de référence** (matching CDF) |
| Histogramme | **Spécification par profil théorique** (gaussien, exponentiel, bimodal, uniforme) | 
| Images couleur | Upload conserve la couleur (RVB) ; égalisation et spécification appliquées **canal par canal** (R, V, B indépendants) |
| Seuillage | Seuillage manuel (bornes basse/haute) et automatique (Otsu) | 
| Morphologie | Érosion, dilatation, ouverture, fermeture | 
| Morphologie | Gradient morphologique, chapeau haut de forme |
| Morphologie | Squelette (amincissements successifs, Zhang-Suen) |
| Mesures | Dénombrement (composantes connexes) |
| Mesures | Granulométrie en nombre, compacité, diamètre équivalent |
| Mesures | Paramètres de forme (circularité) |

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
├── package.json
├── package-lock.json
├── tailwind.input.css
├── tailwind.config.js
├── Dockerfile
├── docker-compose.yaml
├── .dockerignore
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

## Cloner le projet

```bash
git clone https://github.com/setraniainabruno/Specification-histogramme.git
cd Specification-histogramme
```

## Installation et Lancement locale (Sans Docker)

```bash
npm install
npx tailwindcss -i ./tailwind.input.css -o ./app/static/css/tailwind.css --minify
```
```bash
python -m venv .venv
.venv\Scripts\activate #windows
pip install -r requirements.txt
```

```bash
uvicorn app.main:app --reload
```

## Installation et Lancement avec Docker
```bash
docker compose up -d --build
```

## Accéder à l'application
http://localhost:8000

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
