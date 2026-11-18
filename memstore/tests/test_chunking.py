from memstore.chunking import MAX_CHARS, split_body


def test_parts_never_exceed_the_limit_and_split_tables_repeat_their_header():
    table = "| Stage | Cost |\n| :--- | :--- |\n" + "\n".join(f"| row {i} | ${i}.00 |" for i in range(80))
    parts = split_body("intro\n\n" + table)
    assert len(parts) > 2
    assert all(len(p) <= MAX_CHARS + 60 for p in parts)
    for part in parts[1:]:
        assert part.startswith("| Stage | Cost |\n| :--- | :--- |")


def test_one_oversized_line_is_split_by_width():
    parts = split_body("x" * (MAX_CHARS * 2 + 5))
    assert len(parts) == 3 and "".join(parts) == "x" * (MAX_CHARS * 2 + 5)
