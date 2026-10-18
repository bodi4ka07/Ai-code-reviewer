async def test_project_crud(client, auth):
    created = await client.post("/projects/", json={"name": "api", "language": "JS"}, headers=auth)
    assert created.status_code == 201
    pid = created.json()["id"]
    assert created.json()["language"] == "javascript"  # псевдонім нормалізується

    assert len((await client.get("/projects/", headers=auth)).json()) == 1
    assert (await client.get(f"/projects/{pid}", headers=auth)).json()["name"] == "api"

    patched = await client.patch(f"/projects/{pid}", json={"name": "renamed"}, headers=auth)
    assert patched.json()["name"] == "renamed"
    assert patched.json()["language"] == "javascript"

    assert (await client.delete(f"/projects/{pid}", headers=auth)).status_code == 204
    assert (await client.get(f"/projects/{pid}", headers=auth)).status_code == 404


async def test_project_rejects_unsupported_language(client, auth):
    resp = await client.post("/projects/", json={"name": "x", "language": "cobol"}, headers=auth)
    assert resp.status_code == 422


async def test_project_accepts_other_language(client, auth):
    resp = await client.post("/projects/", json={"name": "x", "language": "other"}, headers=auth)
    assert resp.status_code == 201


async def test_cannot_access_foreign_project(client, auth, other_auth, project_id):
    assert (await client.get(f"/projects/{project_id}", headers=other_auth)).status_code == 404
    assert (await client.delete(f"/projects/{project_id}", headers=other_auth)).status_code == 404
    assert (await client.get(f"/projects/{project_id}/stats", headers=other_auth)).status_code == 404
    assert (await client.get(f"/projects/{project_id}/reviews", headers=other_auth)).status_code == 404
    assert (await client.get("/projects/", headers=other_auth)).json() == []


async def test_projects_require_auth(client):
    assert (await client.get("/projects/")).status_code == 401


async def test_stats_for_empty_project(client, auth, project_id):
    resp = await client.get(f"/projects/{project_id}/stats", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_reviews"] == 0
    assert body["average_score"] is None
    assert body["categories"] == []
    assert body["score_history"] == []


async def test_stats_aggregate(client, auth, project_id, session_factory):
    import uuid
    from datetime import datetime, timedelta

    from app.models.comment import CommentCategory, CommentSeverity, ReviewComment
    from app.models.review import Review, ReviewStatus

    now = datetime.utcnow()
    async with session_factory() as db:
        for score, days_ago in ((60, 2), (80, 1)):
            r = Review(
                project_id=uuid.UUID(project_id),
                code_snippet="x",
                status=ReviewStatus.DONE,
                overall_score=score,
                completed_at=now - timedelta(days=days_ago),
            )
            db.add(r)
            await db.flush()
            db.add(
                ReviewComment(
                    review_id=r.id,
                    category=CommentCategory.SECURITY,
                    severity=CommentSeverity.CRITICAL,
                    message="m",
                    suggestion="s",
                )
            )
        db.add(Review(project_id=uuid.UUID(project_id), code_snippet="x", status=ReviewStatus.FAILED))
        await db.commit()

    body = (await client.get(f"/projects/{project_id}/stats", headers=auth)).json()
    assert body["total_reviews"] == 3
    assert body["completed_reviews"] == 2
    assert body["average_score"] == 70.0
    assert (body["min_score"], body["max_score"]) == (60, 80)
    assert body["categories"] == [{"category": "security", "count": 2}]
    assert [p["score"] for p in body["score_history"]] == [60, 80]  # хронологічний порядок
