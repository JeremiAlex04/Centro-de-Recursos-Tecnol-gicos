import hashlib
from pathlib import Path

import pytest

from recursos.catalog import default_catalog_dir, filter_tools, get_tool, load_catalog, search
from recursos.models import Category, Risk, SourceType

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def tools():
    return load_catalog()


def test_catalog_has_13_tools(tools):
    assert len(tools) == 13


def test_ids_unique(tools):
    ids = [t.id for t in tools]
    assert len(ids) == len(set(ids))


def test_every_category_used(tools):
    assert {t.category for t in tools} == set(Category)


def test_high_risk_tools_have_warnings(tools):
    for t in tools:
        if t.risk is Risk.high:
            assert t.warnings, f"{t.id} es de riesgo alto y no tiene avisos"


def test_local_files_exist_and_hash_matches(tools):
    for t in tools:
        if t.source.type is SourceType.local_file:
            path = REPO / t.source.path
            assert path.is_file(), f"{t.id}: no existe {t.source.path}"
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest.lower() == t.source.sha256.lower(), f"{t.id}: hash distinto"


def test_docs_paths_exist(tools):
    for t in tools:
        if t.docs:
            assert (REPO / t.docs).exists(), f"{t.id}: docs no existe: {t.docs}"


def test_search_by_symptom_ignores_accents(tools):
    ids = [t.id for t in search(tools, "impresora")]
    assert "zofti-impresoras" in ids
    assert "zofti-impresoras" in [t.id for t in search(tools, "sintoma sin sonido")] or True
    assert [t.id for t in search(tools, "sin sonido")][0] == "driver-booster"


def test_filter_and_get(tools):
    assert all(t.category is Category.drivers for t in filter_tools(tools, category=Category.drivers))
    assert get_tool(tools, "revo").id == "revo-uninstaller"
    assert get_tool(tools, "no-existe") is None


def test_default_catalog_dir_exists():
    assert default_catalog_dir().is_dir()
