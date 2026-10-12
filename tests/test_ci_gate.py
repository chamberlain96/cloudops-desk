def test_ci_blocks_a_broken_change():
    assert 200 == 500, "Intentional failure to verify the CI gate"
