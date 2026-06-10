from app.pipeline.privacy import hash_candidate_identifier


def test_candidate_identifier_hash_is_stable_and_normalized() -> None:
    assert hash_candidate_identifier(" Candidate@Example.com ") == hash_candidate_identifier(
        "candidate@example.com"
    )
    assert "candidate@example.com" not in hash_candidate_identifier("candidate@example.com")

