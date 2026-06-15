def test_get_board_returns_seeded_snapshot(client):
    res = client.get("/board")
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == 0
    data = body["data"]
    total = len(data["todo"]) + len(data["in_progress"]) + len(data["done"])
    assert total == 5
    assert any(t["title"] == "Pay rent" for t in data["done"])


def test_reset_board_restores_seed(client):
    client.post("/board/reset")
    res = client.get("/board")
    data = res.json()["data"]
    total = len(data["todo"]) + len(data["in_progress"]) + len(data["done"])
    assert total == 5


def test_start_agent_delegates_to_agent(client):
    res = client.post("/startAgent", json={
        "channelName": "todo-test", "rtcUid": 111, "userUid": 222,
    })
    assert res.status_code == 200
    assert res.json()["data"]["agent_id"] == "fake-agent-111"
    assert client.fake_agent.started[0][0] == "todo-test"


def test_stop_agent_delegates_to_agent(client):
    client.post("/stopAgent", json={"agentId": "fake-agent-111"})
    assert client.fake_agent.stopped == ["fake-agent-111"]


def test_get_config_returns_token(client):
    res = client.get("/get_config")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["app_id"] and data["token"] and data["channel_name"]
