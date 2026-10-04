# BFS / DFS / A* Search Visualizer

Interactive grid-search visualizer built with Python Flask, HTML, Tailwind CSS, and vanilla JavaScript.

## Features

- BFS (shortest path on an unweighted grid)
- DFS (depth-first traversal; not guaranteed shortest)
- A* with Manhattan-distance heuristic
- Click/drag wall editing
- Move start and goal cells
- Random wall generation
- Animated exploration and final path
- Server-side input validation and grid-size limits
- Basic security headers
- Unit/API tests

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
flask --app app run --debug
```

Open: http://127.0.0.1:5000

## Tests

```bash
pytest -q
```

## Production notes

This project intentionally uses the Tailwind CDN for a zero-build educational demo. For production, compile Tailwind locally, serve static assets with hashed filenames, tighten the CSP, run Flask behind a production WSGI server/reverse proxy, disable debug mode, and add rate limiting if the API is internet-facing.
