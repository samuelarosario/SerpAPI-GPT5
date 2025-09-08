import re, os, pathlib

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / 'DB' / 'current_schema.sql'

def test_schema_footer_single_tables_line():
    text = SCHEMA_PATH.read_text(encoding='utf-8')
    tables_lines = re.findall(r'^-- Tables: \d+$', text, flags=re.MULTILINE)
    assert len(tables_lines) == 1, f"Expected exactly one '-- Tables:' line, found {len(tables_lines)}: {tables_lines}"


def test_schema_footer_checksum_placeholder_present():
    text = SCHEMA_PATH.read_text(encoding='utf-8')
    assert '-- Schema Checksum:' in text, 'Checksum line missing from schema footer'
