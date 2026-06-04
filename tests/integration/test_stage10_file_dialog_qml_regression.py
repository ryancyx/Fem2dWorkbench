from pathlib import Path


def test_main_workbench_uses_file_dialogs_for_project_open_and_save():
    qml_path = Path("ui/qml/MainWorkbench.qml")
    assert qml_path.exists(), "MainWorkbench.qml should exist"

    qml_text = qml_path.read_text(encoding="utf-8")

    required_snippets = [
        "import QtQuick.Dialogs",
        "FileDialog",
        "openProjectDialog",
        "saveProjectDialog",
        "fileMode: FileDialog.OpenFile",
        "fileMode: FileDialog.SaveFile",
        "nameFilters",
        "fileUrlToLocalPath",
        "ensureProjectFileSuffix",
        "bridge.loadProject",
        "bridge.saveCurrentProject",
        "打开工程",
        "保存工程",
        "另存为",
        "openProjectDialog.open()",
        "saveProjectDialog.open()",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing project file dialog QML snippet: {snippet}"

    assert 'MenuItem { text: "打开工程"; onTriggered: bridge.loadProject("outputs/latest/current_project.f2dw.json") }' not in qml_text
    assert 'MenuItem { text: "保存工程"; onTriggered: bridge.saveCurrentProject("outputs/latest/current_project.f2dw.json") }' not in qml_text
