import QtQuick
import QtQuick.Controls
//import Manipulador_IA
//import QtQuick.Studio.DesignEffects
import QtQuick.Layouts
//import QtQuick.Studio.Components
import QtCharts
import QtGraphs
import QtMultimedia
import QtQuick.Timeline
import QtQuick.VectorImage
import QtQuick.Window
//import Qt.SafeRenderer
//import QtQuick.Studio.LogicHelper
import QtQuick3D
//import QtInsightTracker
import QtQuick.VirtualKeyboard
import QtQuick.VirtualKeyboard.Components
import QtQuick.VirtualKeyboard.Layouts
import QtQuick.VirtualKeyboard.Settings
import QtQuick.VirtualKeyboard.Styles
import QtQuick3D.AssetUtils
import QtQuick3D.Effects
import QtQuick3D.Helpers
import QtQuick3D.Particles3D
//import QtQuick3D.Physics
//import QtQuick3D.Physics.Helpers
import QtQuick3D.SpatialAudio
import QtQuick3D.Xr
//import SimulinkConnector

Rectangle {
    id: rectangle
    width: Constants.width
    height: Constants.height
    color: "#eaeaea"

    border.width: 1

    Header {}

    CameraView {}

    ControlPanel {}

    StatusPanel {}

    LogPanel {}

    /*SLConnector {
        root: rectangle
    }*/

    Item {
        id: __materialLibrary__
    }
}
