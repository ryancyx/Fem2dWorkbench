import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root

    width: 1280
    height: 800
    visible: true
    title: "Fem2dWorkbench"
    color: "#f3f4f6"

    function numberValue(field) {
        return Number(field.text)
    }

    function intValue(field) {
        return parseInt(field.text)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            height: 54
            color: "#1f2937"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                spacing: 14

                Text {
                    text: "Fem2dWorkbench"
                    color: "white"
                    font.pixelSize: 20
                    font.bold: true
                }

                Text {
                    text: "Rectangle solve workflow"
                    color: "#d1d5db"
                    font.pixelSize: 14
                }

                Item { Layout.fillWidth: true }

                Button {
                    text: "Create project"
                    onClicked: bridge.createDefaultProject(
                        numberValue(widthField),
                        numberValue(heightField),
                        numberValue(youngField),
                        numberValue(poissonField),
                        numberValue(thicknessField),
                        numberValue(qyField)
                    )
                }

                Button {
                    text: "Solve"
                    onClicked: bridge.solveCurrentProject(
                        intValue(nxField),
                        intValue(nyField)
                    )
                }

                Button {
                    text: "Export"
                    enabled: bridge.hasSolution
                    onClicked: bridge.exportResults("outputs/latest")
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                color: "#ffffff"
                border.color: "#d1d5db"

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 14
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: 10

                        Text {
                            text: "Inputs"
                            color: "#111827"
                            font.pixelSize: 18
                            font.bold: true
                        }

                        LabeledField { id: widthField; label: "width"; text: "2.0" }
                        LabeledField { id: heightField; label: "height"; text: "1.0" }
                        LabeledField { id: nxField; label: "nx"; text: "4" }
                        LabeledField { id: nyField; label: "ny"; text: "2" }
                        LabeledField { id: youngField; label: "young_modulus"; text: "210000000000" }
                        LabeledField { id: poissonField; label: "poisson_ratio"; text: "0.3" }
                        LabeledField { id: thicknessField; label: "thickness"; text: "0.01" }
                        LabeledField { id: qyField; label: "right edge qy"; text: "-1000" }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: "#e5e7eb"
                        }

                        Button {
                            Layout.fillWidth: true
                            text: "Create default project"
                            onClicked: bridge.createDefaultProject(
                                numberValue(widthField),
                                numberValue(heightField),
                                numberValue(youngField),
                                numberValue(poissonField),
                                numberValue(thicknessField),
                                numberValue(qyField)
                            )
                        }

                        Button {
                            Layout.fillWidth: true
                            text: "Solve"
                            onClicked: bridge.solveCurrentProject(
                                intValue(nxField),
                                intValue(nyField)
                            )
                        }

                        Button {
                            Layout.fillWidth: true
                            text: "Export results"
                            enabled: bridge.hasSolution
                            onClicked: bridge.exportResults("outputs/latest")
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#f9fafb"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 14

                    Text {
                        text: "Result summary"
                        color: "#111827"
                        font.pixelSize: 18
                        font.bold: true
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 4
                        rowSpacing: 8
                        columnSpacing: 18

                        SummaryItem { label: "Nodes"; value: String(bridge.nodeCount) }
                        SummaryItem { label: "Elements"; value: String(bridge.elementCount) }
                        SummaryItem { label: "Max displacement"; value: bridge.maxDisplacement }
                        SummaryItem { label: "Max displacement node"; value: bridge.maxDisplacementNodeId }
                        SummaryItem { label: "Max Von Mises"; value: bridge.maxVonMises }
                        SummaryItem { label: "Max Von Mises element"; value: bridge.maxVonMisesElementId }
                        SummaryItem { label: "Warnings"; value: String(bridge.warningCount) }
                    }

                    SplitView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        orientation: Qt.Vertical

                        GroupBox {
                            title: "Node displacement preview"
                            SplitView.fillWidth: true
                            SplitView.preferredHeight: 260

                            TextArea {
                                anchors.fill: parent
                                readOnly: true
                                font.family: "Consolas"
                                font.pixelSize: 12
                                wrapMode: TextArea.NoWrap
                                text: bridge.nodeRowsPreview
                            }
                        }

                        GroupBox {
                            title: "Element result preview"
                            SplitView.fillWidth: true
                            SplitView.fillHeight: true

                            TextArea {
                                anchors.fill: parent
                                readOnly: true
                                font.family: "Consolas"
                                font.pixelSize: 12
                                wrapMode: TextArea.NoWrap
                                text: bridge.elementRowsPreview
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 34
            color: "#e5e7eb"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 14
                text: bridge.statusText
                color: "#374151"
                font.pixelSize: 13
            }
        }
    }

    component LabeledField: ColumnLayout {
        property alias text: input.text
        property string label: ""

        Layout.fillWidth: true
        spacing: 4

        Text {
            text: parent.label
            color: "#374151"
            font.pixelSize: 13
        }

        TextField {
            id: input
            Layout.fillWidth: true
            selectByMouse: true
        }
    }

    component SummaryItem: ColumnLayout {
        property string label: ""
        property string value: ""

        Layout.fillWidth: true
        spacing: 2

        Text {
            text: parent.label
            color: "#6b7280"
            font.pixelSize: 12
        }

        Text {
            text: parent.value === "" ? "-" : parent.value
            color: "#111827"
            font.pixelSize: 15
            font.bold: true
        }
    }
}
