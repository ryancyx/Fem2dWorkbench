import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        PageHeader {
            title: "分析步"
            subtitle: "定义求解类型和基本假设。"
            badge: "静力线性"
        }

        ParameterCard {
            Layout.fillWidth: true
            title: "分析步配置"
            rows: [
                { label: "分析步 ID", value: "step_static" },
                { label: "分析类型", value: "static_linear" },
                { label: "变形假设", value: "小变形" },
                { label: "材料模型", value: "线弹性" },
                { label: "单元", value: "CST 三角形" }
            ]
        }

        InfoCard {
            Layout.fillWidth: true
            title: "求解路径"
            body: "工程对象会先编译为 FEMModel，再通过静力线性求解入口进入求解器。UI 不直接调用编译器或求解器。"
        }

        Item { Layout.fillHeight: true }
    }
}
