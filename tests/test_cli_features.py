import tempfile
from pathlib import Path
from typer.testing import CliRunner

from recursos import config
from recursos.cli import app

runner = CliRunner()


def test_doctor_command():
    res = runner.invoke(app, ["doctor"])
    assert "Verificando entorno" in res.output
    assert "Sistema Operativo" in res.output


def test_plugin_management():
    # Aseguramos que empiece deshabilitado
    config.set_plugin("activation", False)
    assert not config.plugin_enabled("activation")

    res = runner.invoke(app, ["plugin", "list"])
    assert "Deshabilitado" in res.output

    # Forzar habilitacion en config
    config.set_plugin("activation", True)
    assert config.plugin_enabled("activation")

    res = runner.invoke(app, ["plugin", "list"])
    assert "Habilitado" in res.output

    # Deshabilitar por CLI
    res = runner.invoke(app, ["plugin", "disable", "activation"])
    assert "deshabilitado" in res.output
    assert not config.plugin_enabled("activation")


def test_run_dry_run_local_file():
    res = runner.invoke(app, ["run", "revo-uninstaller", "--dry-run"])
    assert res.exit_code == 0
    assert "dry-run" in res.output.lower()
    assert "Revo Uninstaller Pro" in res.output


def test_install_dry_run():
    res = runner.invoke(app, ["install", "driver-booster", "--dry-run"])
    assert res.exit_code == 0
    assert "IObit Driver Booster" in res.output


def test_run_activation_fails_if_plugin_disabled():
    config.set_plugin("activation", False)
    res = runner.invoke(app, ["run", "mas", "--dry-run"])
    assert res.exit_code == 1
    assert "desactivadas por defecto" in res.output


def test_docs_build_flag():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "TEST_CATALOG.md"
        res = runner.invoke(app, ["docs", "--build", "-o", str(target)])
        assert res.exit_code == 0
        assert target.is_file()
        content = target.read_text(encoding="utf-8")
        assert "Catalogo de herramientas (generado)" in content
        assert "IObit Driver Booster" in content


def test_clean_command():
    res = runner.invoke(app, ["clean"])
    assert res.exit_code == 0
    assert "Cache temporal limpiada" in res.output
