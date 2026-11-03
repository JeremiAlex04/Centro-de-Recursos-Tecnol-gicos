from recursos.catalog import load_catalog
from recursos.gui.app import USO_ESCENARIOS, RecursosApp
from recursos.models import Category


def test_uso_escenarios_cover_tools():
    tools = load_catalog()
    tool_ids = {t.id for t in tools}
    # Asegurar que todas las herramientas tienen su escenario de uso documentado
    for t_id in tool_ids:
        assert t_id in USO_ESCENARIOS, f"Falta escenario para herramienta {t_id}"
        assert "💡 Cuándo usarlo" in USO_ESCENARIOS[t_id]


def test_gui_app_instantiation_headless():
    app = RecursosApp()
    try:
        assert len(app.all_tools) == 13
        assert app.current_category is None

        # Test filtro de categoria
        app._select_category(Category.drivers)
        assert app.current_category == Category.drivers
        assert all(t.category == Category.drivers for t in app.filtered_tools)

        # Test busqueda
        app.search_entry.delete(0, "end")
        app.search_entry.insert(0, "wifi")
        app._filter_and_refresh()
        assert len(app.filtered_tools) > 0
        assert any(t.id == "driver-booster" for t in app.filtered_tools)
    finally:
        app.destroy()
