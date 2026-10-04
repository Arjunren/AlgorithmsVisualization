from __future__ import annotations

from collections import deque
from heapq import heappop, heappush
from itertools import count
from typing import Iterable

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH=64 * 1024,  # protect the demo endpoint from oversized JSON bodies
    JSON_SORT_KEYS=False,
)

MAX_ROWS = 40
MAX_COLS = 40
ALGORITHMS = {"bfs", "dfs", "astar"}

Coord = tuple[int, int]


def parse_coord(value: object, name: str, rows: int, cols: int) -> Coord:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    ):
        raise ValueError(f"{name} must be [row, col] with integer values.")

    row, col = value
    if not (0 <= row < rows and 0 <= col < cols):
        raise ValueError(f"{name} is outside the grid.")
    return row, col


def parse_payload(payload: object) -> tuple[str, int, int, Coord, Coord, set[Coord]]:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    algorithm = payload.get("algorithm")
    rows = payload.get("rows")
    cols = payload.get("cols")

    if algorithm not in ALGORITHMS:
        raise ValueError("algorithm must be one of: bfs, dfs, astar.")
    if not isinstance(rows, int) or isinstance(rows, bool) or not (2 <= rows <= MAX_ROWS):
        raise ValueError(f"rows must be an integer between 2 and {MAX_ROWS}.")
    if not isinstance(cols, int) or isinstance(cols, bool) or not (2 <= cols <= MAX_COLS):
        raise ValueError(f"cols must be an integer between 2 and {MAX_COLS}.")

    start = parse_coord(payload.get("start"), "start", rows, cols)
    goal = parse_coord(payload.get("goal"), "goal", rows, cols)
    if start == goal:
        raise ValueError("start and goal must be different cells.")

    raw_walls = payload.get("walls", [])
    if not isinstance(raw_walls, list):
        raise ValueError("walls must be an array of coordinates.")
    if len(raw_walls) > rows * cols:
        raise ValueError("Too many wall entries.")

    walls: set[Coord] = set()
    for index, wall in enumerate(raw_walls):
        coord = parse_coord(wall, f"walls[{index}]", rows, cols)
        walls.add(coord)

    if start in walls or goal in walls:
        raise ValueError("start and goal cannot be walls.")

    return algorithm, rows, cols, start, goal, walls


def neighbors(node: Coord, rows: int, cols: int, walls: set[Coord]) -> Iterable[Coord]:
    row, col = node
    # Fixed order keeps demonstrations deterministic.
    for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):
        nr, nc = row + dr, col + dc
        nxt = (nr, nc)
        if 0 <= nr < rows and 0 <= nc < cols and nxt not in walls:
            yield nxt


def reconstruct_path(parent: dict[Coord, Coord | None], goal: Coord) -> list[Coord]:
    if goal not in parent:
        return []

    path: list[Coord] = []
    current: Coord | None = goal
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


def bfs(rows: int, cols: int, start: Coord, goal: Coord, walls: set[Coord]):
    frontier = deque([start])
    parent: dict[Coord, Coord | None] = {start: None}
    visited_order: list[Coord] = []

    while frontier:
        node = frontier.popleft()
        visited_order.append(node)
        if node == goal:
            break

        for nxt in neighbors(node, rows, cols, walls):
            if nxt not in parent:
                parent[nxt] = node
                frontier.append(nxt)

    return visited_order, reconstruct_path(parent, goal)


def dfs(rows: int, cols: int, start: Coord, goal: Coord, walls: set[Coord]):
    stack = [start]
    parent: dict[Coord, Coord | None] = {start: None}
    seen: set[Coord] = {start}
    visited_order: list[Coord] = []

    while stack:
        node = stack.pop()
        visited_order.append(node)
        if node == goal:
            break

        # Reverse so the first logical neighbor is processed first with a LIFO stack.
        items = list(neighbors(node, rows, cols, walls))
        for nxt in reversed(items):
            if nxt not in seen:
                seen.add(nxt)
                parent[nxt] = node
                stack.append(nxt)

    return visited_order, reconstruct_path(parent, goal)


def manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(rows: int, cols: int, start: Coord, goal: Coord, walls: set[Coord]):
    sequence = count()
    open_heap: list[tuple[int, int, int, Coord]] = []
    heappush(open_heap, (manhattan(start, goal), 0, next(sequence), start))

    parent: dict[Coord, Coord | None] = {start: None}
    g_score: dict[Coord, int] = {start: 0}
    closed: set[Coord] = set()
    visited_order: list[Coord] = []

    while open_heap:
        _, current_g, _, node = heappop(open_heap)
        if node in closed:
            continue
        if current_g != g_score.get(node):
            continue

        closed.add(node)
        visited_order.append(node)
        if node == goal:
            break

        for nxt in neighbors(node, rows, cols, walls):
            if nxt in closed:
                continue

            tentative_g = current_g + 1
            if tentative_g < g_score.get(nxt, 10**9):
                g_score[nxt] = tentative_g
                parent[nxt] = node
                f_score = tentative_g + manhattan(nxt, goal)
                heappush(open_heap, (f_score, tentative_g, next(sequence), nxt))

    return visited_order, reconstruct_path(parent, goal)


SEARCHERS = {"bfs": bfs, "dfs": dfs, "astar": astar}


@app.after_request
def add_security_headers(response):
    # Tailwind CDN is used for this educational demo. For production, compile Tailwind locally
    # and tighten script-src/style-src so unsafe-inline is unnecessary.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.tailwindcss.com 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/search")
def search():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    try:
        algorithm, rows, cols, start, goal, walls = parse_payload(request.get_json(silent=True))
        visited, path = SEARCHERS[algorithm](rows, cols, start, goal, walls)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "algorithm": algorithm,
            "found": bool(path),
            "visited": [list(node) for node in visited],
            "path": [list(node) for node in path],
            "metrics": {
                "visited_nodes": len(visited),
                "path_length": max(0, len(path) - 1) if path else None,
            },
        }
    )


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Request body is too large."}), 413


@app.errorhandler(500)
def internal_error(_error):
    # Avoid exposing stack traces/internal details to clients.
    return jsonify({"error": "Unexpected server error."}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
