from app import app, astar, bfs, dfs


def test_bfs_finds_shortest_path():
    visited, path = bfs(5, 5, (0, 0), (0, 4), set())
    assert visited
    assert path[0] == (0, 0)
    assert path[-1] == (0, 4)
    assert len(path) - 1 == 4


def test_astar_finds_shortest_path_around_wall():
    walls = {(0, 1), (0, 2), (0, 3)}
    _, path = astar(5, 5, (0, 0), (0, 4), walls)
    assert path[0] == (0, 0)
    assert path[-1] == (0, 4)
    assert len(path) - 1 == 6


def test_dfs_returns_valid_path():
    _, path = dfs(4, 4, (0, 0), (3, 3), {(1, 1), (2, 1)})
    assert path[0] == (0, 0)
    assert path[-1] == (3, 3)


def test_api_rejects_invalid_algorithm():
    client = app.test_client()
    response = client.post(
        "/api/search",
        json={
            "algorithm": "dijkstra",
            "rows": 10,
            "cols": 10,
            "start": [0, 0],
            "goal": [9, 9],
            "walls": [],
        },
    )
    assert response.status_code == 400
    assert "algorithm" in response.get_json()["error"]


def test_api_success():
    client = app.test_client()
    response = client.post(
        "/api/search",
        json={
            "algorithm": "astar",
            "rows": 10,
            "cols": 10,
            "start": [0, 0],
            "goal": [9, 9],
            "walls": [],
        },
    )
    data = response.get_json()
    assert response.status_code == 200
    assert data["found"] is True
    assert data["metrics"]["path_length"] == 18
