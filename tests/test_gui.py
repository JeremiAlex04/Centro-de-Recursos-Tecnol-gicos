import pytest
from recursos.gui import RecursosDesktopApp


def test_gui_instantiation():
    try:
        app = RecursosDesktopApp()
        assert len(app.tools) == 13
        assert app.sidebar is not None
        assert app.main_area is not None
        assert app.cards_scroll is not None
        app.destroy()
    except Exception as e:
        if "no display name" in str(e).lower() or "couldn't connect to display" in str(e).lower():
            pytest.skip("Entorno sin soporte de display gráfico")
        else:
            raise
