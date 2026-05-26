import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string currentMode: "工程"
    property real modelWidth: 2.0
    property real modelHeight: 1.0
    property int meshNx: 4
    property int meshNy: 2
    property real youngModulus: 210000000000
    property real poissonRatio: 0.3
    property real thickness: 0.01
    property real edgeQy: -1000

    signal modeSelected(string modeName)
    signal editParameters()
    signal createProject()

    color: "#F8FAFC"
    border.color: "#D3DCE8"
    implicitWidth: 310

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PanelTitle {
            title: "工程导航"
            subtitle: "建模、分析与结果流程"
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                width: root.width
                spacing: 10

                IndustrialPanel {
                    Layout.fillWidth: true
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    Layout.topMargin: 12
                    height: 260

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        NavItem { indexText: "01"; title: "工程"; desc: "工程总览"; active: root.currentMode === "工程"; onClicked: root.modeSelected("工程") }
                        NavItem { indexText: "02"; title: "零件"; desc: "矩形几何"; active: root.currentMode === "零件"; onClicked: root.modeSelected("零件") }
                        NavItem { indexText: "03"; title: "属性"; desc: "材料和厚度"; active: root.currentMode === "属性"; onClicked: root.modeSelected("属性") }
                        NavItem { indexText: "04"; title: "装配"; desc: "单实例装配"; active: root.currentMode === "装配"; onClicked: root.modeSelected("装配") }
                        NavItem { indexText: "05"; title: "分析"; desc: "边界、载荷、网格、求解"; active: root.currentMode === "边界" || root.currentMode === "载荷" || root.currentMode === "网格" || root.currentMode === "求解"; onClicked: root.modeSelected("边界") }
                        NavItem { indexText: "06"; title: "结果"; desc: "查看和导出"; active: root.currentMode === "结果" || root.currentMode === "导出"; onClicked: root.modeSelected("结果") }
                    }
                }

                ParameterCard {
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    title: "当前参数"
                    rows: [
                        { label: "矩形尺寸", value: root.modelWidth + " × " + root.modelHeight },
                        { label: "弹性模量", value: String(root.youngModulus) },
                        { label: "泊松比", value: String(root.poissonRatio) },
                        { label: "厚度", value: String(root.thickness) },
                        { label: "网格划分", value: root.meshNx + " × " + root.meshNy },
                        { label: "右边界载荷", value: String(root.edgeQy) }
                    ]
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    spacing: 8

                    SecondaryButton { Layout.fillWidth: true; text: "编辑参数"; onClicked: root.editParameters() }
                    SecondaryButton { Layout.fillWidth: true; text: "创建工程"; onClicked: root.createProject() }
                }

                IndustrialPanel {
                    Layout.fillWidth: true
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    Layout.bottomMargin: 12
                    height: 184

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 7

                        SectionHeader { text: "模型树" }
                        TreeLine { text: "工程 / 矩形板分析"; strong: true }
                        TreeLine { text: "零件 / 矩形零件" }
                        TreeLine { text: "属性 / 钢材薄板属性" }
                        TreeLine { text: "装配 / 单零件实例" }
                        TreeLine { text: "约束 / 左边界固定" }
                        TreeLine { text: "载荷 / 右边界均布载荷" }
                        TreeLine { text: "网格 / 结构化 CST 网格" }
                    }
                }
            }
        }
    }

    component PanelTitle: Rectangle {
        property string title: ""
        property string subtitle: ""

        Layout.fillWidth: true
        height: 58
        color: "#F8FAFC"
        border.color: "#D3DCE8"

        Column {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 14
            spacing: 2

            Label { text: parent.parent.title; color: "#1F2937"; font.pixelSize: 16; font.bold: true }
            Label { text: parent.parent.subtitle; color: "#64748B"; font.pixelSize: 12 }
        }
    }

    component SectionHeader: Label {
        color: "#1F2937"
        font.pixelSize: 14
        font.bold: true
    }

    component TreeLine: Label {
        property bool strong: false

        Layout.fillWidth: true
        color: strong ? "#1F2937" : "#64748B"
        font.pixelSize: 12
        font.bold: strong
        elide: Text.ElideRight
    }

    component NavItem: Rectangle {
        id: item

        property string indexText: ""
        property string title: ""
        property string desc: ""
        property bool active: false

        signal clicked()

        Layout.fillWidth: true
        height: 38
        radius: 8
        color: active ? "#EAF2FF" : (mouse.containsMouse ? "#F8FAFC" : "transparent")
        border.color: active ? "#BFDBFE" : "transparent"

        Rectangle {
            visible: item.active
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: 22
            radius: 2
            color: "#2563EB"
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 8
            spacing: 8

            Rectangle {
                width: 28
                height: 22
                radius: 6
                color: item.active ? "#DBEAFE" : "#EEF2F7"
                border.color: item.active ? "#BFDBFE" : "#D3DCE8"

                Label {
                    anchors.centerIn: parent
                    text: item.indexText
                    color: item.active ? "#1D4ED8" : "#64748B"
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                Label {
                    text: item.title
                    color: item.active ? "#1D4ED8" : "#1F2937"
                    font.pixelSize: 12
                    font.bold: true
                }

                Label {
                    text: item.desc
                    color: "#64748B"
                    font.pixelSize: 10
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: item.clicked()
        }
    }
}
