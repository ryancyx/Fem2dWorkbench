import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property real youngModulus: 210000000000
    property real poissonRatio: 0.3
    property real thickness: 0.01
    signal editParameters()
    signal createProject()

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        PageHeader {
            title: "属性 / 材料"
            subtitle: "材料定义和截面厚度会在编译阶段合并为求解器材料。"
            badge: "平面应力"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 14

            ParameterCard {
                Layout.fillWidth: true
                title: "材料"
                rows: [
                    { label: "材料", value: "steel" },
                    { label: "弹性模量", value: String(root.youngModulus) },
                    { label: "泊松比", value: String(root.poissonRatio) }
                ]
            }

            ParameterCard {
                Layout.fillWidth: true
                title: "截面"
                rows: [
                    { label: "截面 ID", value: "sec_plate" },
                    { label: "厚度", value: String(root.thickness) },
                    { label: "平面模式", value: "应力" }
                ]
            }
        }

        InfoCard {
            Layout.fillWidth: true
            title: "限制"
            body: "当前版本只支持平面应力和 CST 三角形单元。材料厚度保存在截面定义中。"
        }

        RowLayout {
            SecondaryButton { text: "编辑材料参数"; onClicked: root.editParameters() }
            PrimaryButton { text: "创建/更新工程"; onClicked: root.createProject() }
        }

        Item { Layout.fillHeight: true }
    }
}
