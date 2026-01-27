
def test_list_papers_sorting(client, session):
    """Test sorting papers by journal and added date."""
    from src.db.models import Paper
    from datetime import datetime, timedelta

    # 1. Arrange: Create papers with different journals and creation dates
    p1 = Paper(
        bibcode="2021Test..1", 
        title="Paper 1", 
        journal="ApJ", 
        created_at=datetime.utcnow() - timedelta(days=10)
    )
    p2 = Paper(
        bibcode="2021Test..2", 
        title="Paper 2", 
        journal="MNRAS", 
        created_at=datetime.utcnow() - timedelta(days=5)
    )
    p3 = Paper(
        bibcode="2021Test..3", 
        title="Paper 3", 
        journal="AA", 
        created_at=datetime.utcnow()
    )
    session.add(p1)
    session.add(p2)
    session.add(p3)
    session.commit()

    # 2. Act & Assert: Sort by journal (asc) -> AA, ApJ, MNRAS
    response = client.get("/api/papers/?sort_by=journal&sort_order=asc")
    assert response.status_code == 200
    data = response.json()["papers"]
    assert len(data) == 3
    assert data[0]["bibcode"] == p3.bibcode
    assert data[1]["bibcode"] == p1.bibcode
    assert data[2]["bibcode"] == p2.bibcode

    # 3. Act & Assert: Sort by journal (desc) -> MNRAS, ApJ, AA
    response = client.get("/api/papers/?sort_by=journal&sort_order=desc")
    assert response.status_code == 200
    data = response.json()["papers"]
    assert data[0]["bibcode"] == p2.bibcode
    assert data[1]["bibcode"] == p1.bibcode
    assert data[2]["bibcode"] == p3.bibcode

    # 4. Act & Assert: Sort by created_at (asc) -> p1, p2, p3
    response = client.get("/api/papers/?sort_by=created_at&sort_order=asc")
    assert response.status_code == 200
    data = response.json()["papers"]
    assert data[0]["bibcode"] == p1.bibcode
    assert data[1]["bibcode"] == p2.bibcode
    assert data[2]["bibcode"] == p3.bibcode
