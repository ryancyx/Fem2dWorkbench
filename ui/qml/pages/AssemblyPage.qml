import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    ColumnLayout {
        anchors.fill: parent
        spacing: 14

        PageHeader {
            title: "装配"
            subtitle: "当前求解链仅支持单矩形零件实例。多零件装配是 UI 工作流占位。"
            badge: "单实例"
        }

        ParameterCard {
            Layout.fillWidth: true
            title: "当前装配"
            rows: [
                { label: "模式", value: "单零件实例" },
                { label: "实例", value: "instance_1" },
                { label: "零件", value: "part_rectangle" },
                { label: "平移", value: "(0, 0)" },
                { label: "旋转", value: "0" }
            ]
        }

        IndustrialPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                Label {
                    text: "规划工作流"
                    color: "#111827"
                    font.bold: true
                    font.pixelSize: 15
                }

                Repeater {
                    model: [
                        "1. 创建多个零件",
                        "2. 分配材料截面",
                        "3. 添加零件实例",
                        "4. 定位装配实例",
                        "5. 对几何边施加载荷和约束"
                    ]

                    delegate: Label {
                        required property string modelData
                        Layout.fillWidth: true
                        text: modelData
                        color: "#5F6B7A"
                        font.pixelSize: 13
                    }
                }

                StatusPill {
                    text: "多零件装配规划中"
                    tone: "amber"
                }
            }
        }
    }
}
