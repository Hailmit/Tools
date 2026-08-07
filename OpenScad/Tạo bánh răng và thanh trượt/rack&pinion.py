# -*- coding: utf-8 -*-
"""
FREECAD PARAMETRIC RACK & PINION — SPUR / HELICAL V5

Nâng cấp từ bản Auto/Manual Teeth V4:
- Chọn loại răng:
    + Spur / răng thẳng
    + Helical / răng xéo
- Với helical:
    + nhập góc xoắn beta;
    + chọn hướng xoắn Right / Left;
    + rack tự nghiêng răng tương thích với pinion;
    + dùng hệ normal module tiêu chuẩn:
          m_t = m_n / cos(beta)
          alpha_t = atan(tan(alpha_n) / cos(beta))
          d = z * m_t
          D_out = d + 2*m_n
      =>  m_n = D_out / (z/cos(beta) + 2)
- Spur là trường hợp beta = 0°, nên toàn bộ công thức quay về V4.

Input:
    1) Đường kính ngoài pinion [mm]
    2) Tổng chiều dài rack [mm]
    3) Loại răng Spur / Helical
    4) Nếu Helical: góc xoắn beta và hướng xoắn
    5) Chế độ số răng Auto / Manual

Quan hệ tương thích bắt buộc:
    m_n rack = m_n pinion
    alpha_n rack = alpha_n pinion
    p_t rack = pi * m_t
    helix rack được dịch theo Z đồng bộ với twist của pinion

Ghi chú hình học:
- Góc áp lực nhập là góc áp lực pháp tuyến alpha_n = 20°.
- Pinion helical được tạo bằng loft nhiều tiết diện involute đã xoay dần theo Z.
- Rack helical được tạo bằng oblique extrusion rồi cắt về đúng chiều dài tổng thể.
- Chân răng pinion nối từ vòng chân tới involute, không mô phỏng trochoid dao cắt.
- Mục tiêu là hình học CAD/B-Rep và lắp ráp; không thay thế kiểm tra tải ISO/AGMA.

Chạy trong FreeCAD Python Console:
    exec(open(r"C:/duong_dan/rack_pinion_freecad_spur_helical_v5.py",
              encoding="utf-8").read())

Hoặc đổi/giữ đuôi .FCMacro và chạy từ Macro manager.

| Nhu cầu                               | Nên chọn       |
| ------------------------------------- | -------------- |
| Prototype, cơ cấu đơn giản            | **Răng thẳng** |
| Tốc độ thấp–trung bình                | **Răng thẳng** |
| Muốn dễ chế tạo/in 3D                 | **Răng thẳng** |
| Không muốn tải dọc trục               | **Răng thẳng** |
| Chạy nhanh                            | **Răng xéo**   |
| Muốn ít rung, ít tiếng “cạch cạch”    | **Răng xéo**   |
| Tải lớn, cần nhiều răng cùng chia tải | **Răng xéo**   |
| Chuyển động tuyến tính rất mượt       | **Răng xéo**   |


"""

import math
import os
import traceback
from datetime import datetime

import FreeCAD as App
import Part


# ============================================================
# QT COMPATIBILITY
# ============================================================


def load_qt():
    """Tương thích PySide, PySide2 và PySide6."""
    try:
        from PySide import QtCore, QtGui
        try:
            from PySide import QtWidgets
        except ImportError:
            QtWidgets = QtGui
        return QtCore, QtGui, QtWidgets
    except ImportError:
        pass

    try:
        from PySide2 import QtCore, QtGui, QtWidgets
        return QtCore, QtGui, QtWidgets
    except ImportError:
        pass

    from PySide6 import QtCore, QtGui, QtWidgets
    return QtCore, QtGui, QtWidgets


QtCore, QtGui, QtWidgets = load_qt()


def qt_dialog_accepted():
    value = getattr(QtWidgets.QDialog, "Accepted", None)
    if value is not None:
        return value
    return QtWidgets.QDialog.DialogCode.Accepted


def qt_dialog_buttons():
    box = QtWidgets.QDialogButtonBox
    ok_button = getattr(box, "Ok", None)
    cancel_button = getattr(box, "Cancel", None)
    if ok_button is None:
        ok_button = box.StandardButton.Ok
    if cancel_button is None:
        cancel_button = box.StandardButton.Cancel
    return ok_button | cancel_button


def qt_text_selectable_by_mouse():
    value = getattr(QtCore.Qt, "TextSelectableByMouse", None)
    if value is not None:
        return value
    return QtCore.Qt.TextInteractionFlag.TextSelectableByMouse


# ============================================================
# DEFAULTS AND DESIGN RULES
# ============================================================

DEFAULT_PINION_OUTER_DIAMETER = 60.0
DEFAULT_RACK_TOTAL_LENGTH = 200.0
DEFAULT_TEETH_MODE = "auto"
DEFAULT_MANUAL_PINION_TEETH = 24
DEFAULT_GEAR_TYPE = "spur"
DEFAULT_HELIX_ANGLE_DEG = 20.0
DEFAULT_HELIX_HAND = "right"

PARAMETER_PATH = (
    "User parameter:BaseApp/Preferences/Mod/RackPinionSpurHelicalV5"
)
DOCUMENT_BASE_NAME = "RackAndPinion_SpurHelical"
OUTPUT_FOLDER_NAME = "RackAndPinion_Output"

NORMAL_PRESSURE_ANGLE_DEG = 20.0
AUTO_MIN_PINION_TEETH = 18
AUTO_MAX_PINION_TEETH = 60
MANUAL_MIN_PINION_TEETH = 18
MANUAL_MAX_PINION_TEETH = 200
PREFERRED_PINION_TEETH = 24

MIN_HELIX_ANGLE_DEG = 1.0
MAX_HELIX_ANGLE_DEG = 45.0

MIN_RACK_PITCH_COUNT = 4.0
MAX_RACK_PITCH_COUNT = 2000.0

INVOLUTE_SAMPLES = 16
BACKLASH_RATIO = 0.04
MIN_BACKLASH_MM = 0.01
FACE_WIDTH_FACTOR = 8.0
RACK_BASE_FACTOR = 3.0
MIN_RIM_RADIAL_FACTOR = 2.0

HELICAL_MIN_LOFT_SECTIONS = 5
HELICAL_MAX_LOFT_SECTIONS = 9
HELICAL_TARGET_TWIST_STEP_DEG = 5.0

PREFERRED_MODULES = (
    0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80,
    1.00, 1.25, 1.50, 2.00, 2.50, 3.00, 4.00,
    5.00, 6.00, 8.00, 10.00, 12.00, 16.00, 20.00,
)


# ============================================================
# SMALL HELPERS
# ============================================================


def normalize_gear_type(value):
    return "helical" if str(value).lower() == "helical" else "spur"


def normalize_helix_hand(value):
    return "left" if str(value).lower() == "left" else "right"


def helix_hand_sign(hand):
    # Quy ước nội bộ:
    # right: tiết diện pinion quay + quanh Z khi z tăng.
    # left : ngược lại.
    return 1.0 if normalize_helix_hand(hand) == "right" else -1.0


def effective_helix_angle_deg(gear_type, helix_angle_deg):
    if normalize_gear_type(gear_type) == "spur":
        return 0.0
    return float(helix_angle_deg)


def validate_helix_settings(gear_type, helix_angle_deg):
    gear_type = normalize_gear_type(gear_type)
    beta = float(helix_angle_deg)
    if gear_type == "helical":
        if beta < MIN_HELIX_ANGLE_DEG or beta > MAX_HELIX_ANGLE_DEG:
            raise ValueError(
                "Góc xoắn beta của helical phải nằm trong {:.1f}° ... {:.1f}°."
                .format(MIN_HELIX_ANGLE_DEG, MAX_HELIX_ANGLE_DEG)
            )


# ============================================================
# GUI
# ============================================================


class RackPinionInputDialog(QtWidgets.QDialog):
    """Hộp thoại nhập kích thước, loại răng và chế độ số răng."""

    def __init__(
        self,
        pinion_outer_diameter,
        rack_total_length,
        teeth_mode,
        manual_pinion_teeth,
        gear_type,
        helix_angle_deg,
        helix_hand,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle("Rack & Pinion — Spur / Helical V5")
        self.setModal(True)
        self.setMinimumWidth(560)

        form = QtWidgets.QFormLayout()

        self.pinion_diameter = QtWidgets.QDoubleSpinBox()
        self.pinion_diameter.setRange(5.01, 100000.0)
        self.pinion_diameter.setDecimals(3)
        self.pinion_diameter.setSingleStep(1.0)
        self.pinion_diameter.setSuffix(" mm")
        self.pinion_diameter.setValue(pinion_outer_diameter)
        self.pinion_diameter.setToolTip(
            "Đường kính đỉnh răng mục tiêu của pinion."
        )

        self.rack_length = QtWidgets.QDoubleSpinBox()
        self.rack_length.setRange(5.01, 1000000.0)
        self.rack_length.setDecimals(3)
        self.rack_length.setSingleStep(10.0)
        self.rack_length.setSuffix(" mm")
        self.rack_length.setValue(rack_total_length)
        self.rack_length.setToolTip(
            "Chiều dài tổng thể rack theo phương chuyển động X."
        )

        self.gear_type = QtWidgets.QComboBox()
        self.gear_type.addItem("Răng thẳng (Spur)", "spur")
        self.gear_type.addItem("Răng xéo (Helical)", "helical")
        gear_index = self.gear_type.findData(normalize_gear_type(gear_type))
        self.gear_type.setCurrentIndex(max(gear_index, 0))

        self.helix_angle = QtWidgets.QDoubleSpinBox()
        self.helix_angle.setRange(MIN_HELIX_ANGLE_DEG, MAX_HELIX_ANGLE_DEG)
        self.helix_angle.setDecimals(2)
        self.helix_angle.setSingleStep(1.0)
        self.helix_angle.setSuffix(" deg")
        self.helix_angle.setValue(helix_angle_deg)
        self.helix_angle.setToolTip(
            "Góc xoắn beta tại vòng chia. Thường dùng khoảng 15°–30°."
        )

        self.helix_hand = QtWidgets.QComboBox()
        self.helix_hand.addItem("Phải (Right-hand)", "right")
        self.helix_hand.addItem("Trái (Left-hand)", "left")
        hand_index = self.helix_hand.findData(normalize_helix_hand(helix_hand))
        self.helix_hand.setCurrentIndex(max(hand_index, 0))
        self.helix_hand.setToolTip(
            "Rack sẽ tự nghiêng răng theo đúng hướng để ăn khớp với pinion."
        )

        self.teeth_mode = QtWidgets.QComboBox()
        self.teeth_mode.addItem("Tự động chọn số răng", "auto")
        self.teeth_mode.addItem("Nhập tay số răng", "manual")
        mode_index = self.teeth_mode.findData(teeth_mode)
        if mode_index < 0:
            mode_index = 0
        self.teeth_mode.setCurrentIndex(mode_index)

        self.pinion_teeth = QtWidgets.QSpinBox()
        self.pinion_teeth.setRange(
            MANUAL_MIN_PINION_TEETH,
            MANUAL_MAX_PINION_TEETH,
        )
        self.pinion_teeth.setSingleStep(1)
        self.pinion_teeth.setValue(manual_pinion_teeth)
        self.pinion_teeth.setToolTip(
            "Giữ giới hạn >= {} răng để macro bảo thủ với undercut."
            .format(MANUAL_MIN_PINION_TEETH)
        )

        form.addRow("Đường kính ngoài pinion:", self.pinion_diameter)
        form.addRow("Tổng chiều dài rack:", self.rack_length)
        form.addRow("Loại răng:", self.gear_type)
        form.addRow("Góc xoắn beta:", self.helix_angle)
        form.addRow("Hướng xoắn pinion:", self.helix_hand)
        form.addRow("Chế độ số răng:", self.teeth_mode)
        form.addRow("Số răng pinion:", self.pinion_teeth)

        self.preview = QtWidgets.QLabel()
        self.preview.setWordWrap(True)
        self.preview.setTextInteractionFlags(qt_text_selectable_by_mouse())

        note = QtWidgets.QLabel(
            "Spur: beta = 0°. Helical: dùng normal module m_n và normal "
            "pressure angle 20°. Rack tự đổi transverse pitch, góc răng và "
            "độ nghiêng theo đúng pinion."
        )
        note.setWordWrap(True)

        buttons = QtWidgets.QDialogButtonBox(qt_dialog_buttons())
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.preview)
        layout.addWidget(note)
        layout.addWidget(buttons)

        self.gear_type.currentIndexChanged.connect(self.update_state_and_preview)
        self.helix_angle.valueChanged.connect(self.update_preview)
        self.helix_hand.currentIndexChanged.connect(self.update_preview)
        self.teeth_mode.currentIndexChanged.connect(self.update_state_and_preview)
        self.pinion_diameter.valueChanged.connect(self.update_preview)
        self.rack_length.valueChanged.connect(self.update_preview)
        self.pinion_teeth.valueChanged.connect(self.update_preview)

        self.update_state_and_preview()
        self.pinion_diameter.setFocus()
        self.pinion_diameter.selectAll()

    def selected_mode(self):
        mode = self.teeth_mode.currentData()
        if mode not in ("auto", "manual"):
            return "auto"
        return str(mode)

    def selected_gear_type(self):
        return normalize_gear_type(self.gear_type.currentData())

    def selected_helix_hand(self):
        return normalize_helix_hand(self.helix_hand.currentData())

    def update_state_and_preview(self, *args):
        is_helical = self.selected_gear_type() == "helical"
        self.helix_angle.setEnabled(is_helical)
        self.helix_hand.setEnabled(is_helical)
        self.pinion_teeth.setEnabled(self.selected_mode() == "manual")
        self.update_preview()

    def update_preview(self, *args):
        diameter = float(self.pinion_diameter.value())
        rack_length = float(self.rack_length.value())
        gear_type = self.selected_gear_type()
        helix_angle = float(self.helix_angle.value())
        helix_hand = self.selected_helix_hand()
        mode = self.selected_mode()
        manual_teeth = int(self.pinion_teeth.value())

        try:
            design = resolve_pinion_design(
                diameter,
                rack_length,
                mode,
                manual_teeth,
                gear_type,
                helix_angle,
                helix_hand,
            )

            mode_text = "AUTO" if design["teeth_mode"] == "auto" else "MANUAL"
            type_text = "HELICAL" if design["gear_type"] == "helical" else "SPUR"

            if design["gear_type"] == "helical":
                extra = (
                    "beta = {:.2f}° {}; m_n = {:.6f} mm; m_t = {:.6f} mm; "
                    "alpha_t = {:.3f}°; "
                ).format(
                    design["helix_angle_deg"],
                    design["helix_hand"].upper(),
                    design["normal_module"],
                    design["transverse_module"],
                    design["transverse_pressure_angle_deg"],
                )
            else:
                extra = "m = {:.6f} mm; ".format(design["normal_module"])

            self.preview.setText(
                "<b>Kết quả dự kiến:</b> "
                "{} / {}; z = {}; {}"
                "p_t = {:.6f} mm; rack ≈ {:.3f} bước răng; "
                "module chuẩn gần nhất = {:.4f} mm (sai lệch {:.3f}%)."
                .format(
                    type_text,
                    mode_text,
                    design["teeth"],
                    extra,
                    design["transverse_circular_pitch"],
                    design["rack_pitch_count"],
                    design["nearest_standard_module"],
                    design["module_deviation_percent"],
                )
            )
        except Exception as exc:
            self.preview.setText("<b>Input chưa hợp lệ:</b> {}".format(str(exc)))

    def values(self):
        return {
            "outer_diameter": float(self.pinion_diameter.value()),
            "rack_length": float(self.rack_length.value()),
            "gear_type": self.selected_gear_type(),
            "helix_angle_deg": float(self.helix_angle.value()),
            "helix_hand": self.selected_helix_hand(),
            "teeth_mode": self.selected_mode(),
            "manual_teeth": int(self.pinion_teeth.value()),
        }


def main_window():
    try:
        import FreeCADGui as Gui
        return Gui.getMainWindow()
    except Exception:
        return None


def show_error(title, message):
    try:
        QtWidgets.QMessageBox.critical(main_window(), title, message)
    except Exception:
        App.Console.PrintError("{}: {}\n".format(title, message))


def show_warning(title, message):
    try:
        QtWidgets.QMessageBox.warning(main_window(), title, message)
    except Exception:
        App.Console.PrintWarning("{}: {}\n".format(title, message))


def show_information(title, message):
    try:
        QtWidgets.QMessageBox.information(main_window(), title, message)
    except Exception:
        App.Console.PrintMessage("{}: {}\n".format(title, message))


def get_user_inputs():
    """Đọc cấu hình gần nhất, mở GUI và kiểm tra thiết kế."""
    params = App.ParamGet(PARAMETER_PATH)

    diameter = params.GetFloat(
        "PinionOuterDiameter", DEFAULT_PINION_OUTER_DIAMETER
    )
    rack_length = params.GetFloat(
        "RackTotalLength", DEFAULT_RACK_TOTAL_LENGTH
    )
    teeth_mode = params.GetString("TeethMode", DEFAULT_TEETH_MODE)
    manual_teeth = params.GetInt(
        "ManualPinionTeeth", DEFAULT_MANUAL_PINION_TEETH
    )
    gear_type = params.GetString("GearType", DEFAULT_GEAR_TYPE)
    helix_angle_deg = params.GetFloat(
        "HelixAngleDeg", DEFAULT_HELIX_ANGLE_DEG
    )
    helix_hand = params.GetString("HelixHand", DEFAULT_HELIX_HAND)

    while True:
        dialog = RackPinionInputDialog(
            diameter,
            rack_length,
            teeth_mode,
            manual_teeth,
            gear_type,
            helix_angle_deg,
            helix_hand,
            main_window(),
        )

        if hasattr(dialog, "exec"):
            result = dialog.exec()
        else:
            result = dialog.exec_()

        if result != qt_dialog_accepted():
            return None

        values = dialog.values()

        try:
            design = resolve_pinion_design(
                values["outer_diameter"],
                values["rack_length"],
                values["teeth_mode"],
                values["manual_teeth"],
                values["gear_type"],
                values["helix_angle_deg"],
                values["helix_hand"],
            )
        except ValueError as exc:
            show_warning("Input không khả thi", str(exc))
            diameter = values["outer_diameter"]
            rack_length = values["rack_length"]
            teeth_mode = values["teeth_mode"]
            manual_teeth = values["manual_teeth"]
            gear_type = values["gear_type"]
            helix_angle_deg = values["helix_angle_deg"]
            helix_hand = values["helix_hand"]
            continue

        params.SetFloat("PinionOuterDiameter", values["outer_diameter"])
        params.SetFloat("RackTotalLength", values["rack_length"])
        params.SetString("TeethMode", values["teeth_mode"])
        params.SetInt("ManualPinionTeeth", values["manual_teeth"])
        params.SetString("GearType", values["gear_type"])
        params.SetFloat("HelixAngleDeg", values["helix_angle_deg"])
        params.SetString("HelixHand", values["helix_hand"])

        return design


# ============================================================
# GEOMETRY AND DESIGN
# ============================================================


def polar(radius, angle_rad):
    return App.Vector(
        radius * math.cos(angle_rad),
        radius * math.sin(angle_rad),
        0.0,
    )


def involute_angle(radius, base_radius):
    """Hàm involute inv(phi) = tan(phi) - phi."""
    ratio = max(radius / base_radius, 1.0)
    parameter = math.sqrt(max(ratio * ratio - 1.0, 0.0))
    return parameter - math.atan(parameter)


def safe_refine(shape):
    """Xóa splitter dư; giữ shape gốc nếu refine thất bại."""
    try:
        refined = shape.removeSplitter()
        if not refined.isNull() and refined.isValid():
            return refined
    except Exception:
        pass
    return shape


def validate_base_inputs(outer_diameter, rack_length):
    if outer_diameter <= 5.0:
        raise ValueError("Đường kính pinion phải lớn hơn 5 mm.")
    if rack_length <= 5.0:
        raise ValueError("Chiều dài rack phải lớn hơn 5 mm.")


def nearest_preferred_module(module):
    return min(
        PREFERRED_MODULES,
        key=lambda standard: abs(math.log(module / standard)),
    )


def evaluate_teeth_design(
    outer_diameter,
    rack_length,
    teeth,
    teeth_mode,
    gear_type,
    helix_angle_deg,
    helix_hand,
):
    """
    Tính thiết kế từ D_out và z theo hệ normal module.

    Spur:
        beta = 0
        m_t = m_n
        D_out = m_n * (z + 2)

    Helical:
        m_t = m_n / cos(beta)
        d = z * m_t
        D_out = d + 2*m_n
              = m_n * (z/cos(beta) + 2)
    """
    validate_base_inputs(outer_diameter, rack_length)

    teeth = int(teeth)
    if teeth < MANUAL_MIN_PINION_TEETH:
        raise ValueError(
            "Số răng phải >= {} cho phạm vi bảo thủ của macro này."
            .format(MANUAL_MIN_PINION_TEETH)
        )
    if teeth > MANUAL_MAX_PINION_TEETH:
        raise ValueError(
            "Số răng phải <= {} để giới hạn độ nặng B-Rep."
            .format(MANUAL_MAX_PINION_TEETH)
        )

    gear_type = normalize_gear_type(gear_type)
    helix_hand = normalize_helix_hand(helix_hand)
    validate_helix_settings(gear_type, helix_angle_deg)

    beta_deg = effective_helix_angle_deg(gear_type, helix_angle_deg)
    beta = math.radians(beta_deg)
    cos_beta = math.cos(beta)

    if cos_beta <= 1e-9:
        raise ValueError("Góc xoắn làm cos(beta) quá nhỏ.")

    normal_module = outer_diameter / (teeth / cos_beta + 2.0)
    if normal_module <= 0.0:
        raise ValueError("Normal module tính được không hợp lệ.")

    transverse_module = normal_module / cos_beta

    alpha_n = math.radians(NORMAL_PRESSURE_ANGLE_DEG)
    alpha_t = math.atan(math.tan(alpha_n) / cos_beta)
    alpha_t_deg = math.degrees(alpha_t)

    normal_circular_pitch = math.pi * normal_module
    transverse_circular_pitch = math.pi * transverse_module
    rack_pitch_count = rack_length / transverse_circular_pitch

    if rack_pitch_count < MIN_RACK_PITCH_COUNT:
        raise ValueError(
            "Rack chỉ dài {:.3f} bước răng theo phương X; yêu cầu tối thiểu {:.0f}. "
            "Hãy tăng chiều dài rack, tăng số răng hoặc giảm D_out."
            .format(rack_pitch_count, MIN_RACK_PITCH_COUNT)
        )

    if rack_pitch_count > MAX_RACK_PITCH_COUNT:
        raise ValueError(
            "Rack có {:.1f} bước răng, vượt giới hạn {:.0f}. "
            "Hãy chia rack thành nhiều đoạn, giảm số răng hoặc tăng D_out."
            .format(rack_pitch_count, MAX_RACK_PITCH_COUNT)
        )

    nearest_module = nearest_preferred_module(normal_module)
    module_deviation_percent = (
        abs(normal_module - nearest_module) / nearest_module * 100.0
    )

    return {
        "outer_diameter": float(outer_diameter),
        "rack_length": float(rack_length),
        "teeth": teeth,
        "teeth_mode": str(teeth_mode),
        "gear_type": gear_type,
        "helix_angle_deg": beta_deg,
        "helix_hand": helix_hand,
        # Giữ alias module để tương thích tư duy/code V4.
        "module": normal_module,
        "normal_module": normal_module,
        "transverse_module": transverse_module,
        "nearest_standard_module": nearest_module,
        "module_deviation_percent": module_deviation_percent,
        "normal_pressure_angle_deg": NORMAL_PRESSURE_ANGLE_DEG,
        "transverse_pressure_angle_deg": alpha_t_deg,
        "normal_circular_pitch": normal_circular_pitch,
        "transverse_circular_pitch": transverse_circular_pitch,
        # circular_pitch theo hướng chuyển động rack X.
        "circular_pitch": transverse_circular_pitch,
        "rack_pitch_count": rack_pitch_count,
    }


def choose_pinion_teeth(
    outer_diameter,
    rack_length,
    gear_type,
    helix_angle_deg,
    helix_hand,
):
    """Tự chọn z, ưu tiên normal module gần dãy module chuẩn."""
    validate_base_inputs(outer_diameter, rack_length)
    validate_helix_settings(gear_type, helix_angle_deg)

    feasible = []
    all_counts = []

    for teeth in range(AUTO_MIN_PINION_TEETH, AUTO_MAX_PINION_TEETH + 1):
        try:
            design = evaluate_teeth_design(
                outer_diameter,
                rack_length,
                teeth,
                "auto",
                gear_type,
                helix_angle_deg,
                helix_hand,
            )
        except ValueError:
            # Tính count thô để báo lỗi hữu ích nếu có thể.
            beta = math.radians(
                effective_helix_angle_deg(gear_type, helix_angle_deg)
            )
            cos_beta = math.cos(beta)
            if cos_beta > 1e-9:
                mn = outer_diameter / (teeth / cos_beta + 2.0)
                mt = mn / cos_beta
                if mt > 0.0:
                    all_counts.append(rack_length / (math.pi * mt))
            continue

        all_counts.append(design["rack_pitch_count"])

        module_error = abs(
            math.log(
                design["normal_module"]
                / design["nearest_standard_module"]
            )
        )
        tooth_count_penalty = (
            abs(teeth - PREFERRED_PINION_TEETH)
            / PREFERRED_PINION_TEETH
            * 0.08
        )
        rack_margin_penalty = max(
            0.0, 6.0 - design["rack_pitch_count"]
        ) * 0.02

        score = module_error + tooth_count_penalty + rack_margin_penalty
        feasible.append((score, design))

    if not feasible:
        if all_counts:
            min_count = min(all_counts)
            max_count = max(all_counts)
            if max_count < MIN_RACK_PITCH_COUNT:
                raise ValueError(
                    "Rack quá ngắn so với pinion: chỉ đạt tối đa "
                    "{:.2f} bước răng; yêu cầu tối thiểu {:.0f}."
                    .format(max_count, MIN_RACK_PITCH_COUNT)
                )
            if min_count > MAX_RACK_PITCH_COUNT:
                raise ValueError(
                    "Rack vượt {:.0f} bước răng, quá nặng cho B-Rep."
                    .format(MAX_RACK_PITCH_COUNT)
                )
        raise ValueError("Không tìm được cấu hình rack–pinion khả thi.")

    feasible.sort(key=lambda item: item[0])
    return feasible[0][1]


def resolve_pinion_design(
    outer_diameter,
    rack_length,
    teeth_mode,
    manual_teeth,
    gear_type,
    helix_angle_deg,
    helix_hand,
):
    if teeth_mode == "manual":
        return evaluate_teeth_design(
            outer_diameter,
            rack_length,
            manual_teeth,
            "manual",
            gear_type,
            helix_angle_deg,
            helix_hand,
        )

    return choose_pinion_teeth(
        outer_diameter,
        rack_length,
        gear_type,
        helix_angle_deg,
        helix_hand,
    )


def make_bspline_edge(points):
    curve = Part.BSplineCurve()
    curve.interpolate(points)
    edge = curve.toShape()
    if edge.isNull():
        raise RuntimeError("Không tạo được B-spline involute.")
    return edge


def make_pinion_profile_wire(
    normal_module,
    transverse_module,
    teeth,
    transverse_pressure_angle_deg,
    total_backlash_transverse,
):
    """Tạo wire tiết diện ngang XY của pinion spur/helical."""
    pressure_angle = math.radians(transverse_pressure_angle_deg)

    pitch_radius = transverse_module * teeth / 2.0
    outer_radius = pitch_radius + normal_module
    root_radius = pitch_radius - 1.25 * normal_module
    base_radius = pitch_radius * math.cos(pressure_angle)
    circular_pitch = math.pi * transverse_module

    if root_radius <= 0.0:
        raise ValueError("Bán kính chân răng pinion <= 0.")
    if base_radius <= 0.0:
        raise ValueError("Bán kính cơ sở pinion <= 0.")

    member_thinning = total_backlash_transverse / 2.0
    tooth_thickness_pitch = circular_pitch / 2.0 - member_thinning
    half_tooth_angle_pitch = tooth_thickness_pitch / (2.0 * pitch_radius)

    inv_pitch = involute_angle(pitch_radius, base_radius)
    inv_outer = involute_angle(outer_radius, base_radius)

    flank_start_radius = max(root_radius, base_radius)
    inv_start = involute_angle(flank_start_radius, base_radius)

    half_angle_start = half_tooth_angle_pitch + inv_pitch - inv_start
    half_angle_outer = half_tooth_angle_pitch + inv_pitch - inv_outer

    if half_angle_start <= 0.0:
        raise ValueError("Biên dạng chân răng pinion bị đảo.")
    if half_angle_outer <= 0.0:
        raise ValueError("Đỉnh răng pinion bị nhọn hoặc đảo biên dạng.")

    tooth_pitch_angle = 2.0 * math.pi / teeth
    root_gap_angle = tooth_pitch_angle - 2.0 * half_angle_start
    if root_gap_angle <= 0.0:
        raise ValueError("Biên dạng chân răng pinion tự giao nhau.")

    start_parameter = math.sqrt(
        max((flank_start_radius / base_radius) ** 2 - 1.0, 0.0)
    )
    outer_parameter = math.sqrt(
        max((outer_radius / base_radius) ** 2 - 1.0, 0.0)
    )
    involute_parameters = [
        start_parameter
        + (outer_parameter - start_parameter) * index / INVOLUTE_SAMPLES
        for index in range(INVOLUTE_SAMPLES + 1)
    ]

    centers = [index * tooth_pitch_angle for index in range(teeth)]
    root_left_points = [
        polar(root_radius, center - half_angle_start)
        for center in centers
    ]
    root_right_points = [
        polar(root_radius, center + half_angle_start)
        for center in centers
    ]

    edges = []

    for tooth_index, center_angle in enumerate(centers):
        root_left = root_left_points[tooth_index]
        root_right = root_right_points[tooth_index]
        next_root_left = root_left_points[(tooth_index + 1) % teeth]

        left_flank_points = []
        right_flank_points = []

        for parameter in involute_parameters:
            radius = base_radius * math.sqrt(1.0 + parameter ** 2)
            inv_value = parameter - math.atan(parameter)
            half_angle = half_tooth_angle_pitch + inv_pitch - inv_value
            left_flank_points.append(
                polar(radius, center_angle - half_angle)
            )
            right_flank_points.append(
                polar(radius, center_angle + half_angle)
            )

        left_base = left_flank_points[0]
        right_base = right_flank_points[0]
        left_outer = left_flank_points[-1]
        right_outer = right_flank_points[-1]

        if (left_base - root_left).Length > 1e-9:
            edges.append(Part.makeLine(root_left, left_base))

        edges.append(make_bspline_edge(left_flank_points))

        outer_mid = polar(outer_radius, center_angle)
        edges.append(Part.Arc(left_outer, outer_mid, right_outer).toShape())

        edges.append(make_bspline_edge(list(reversed(right_flank_points))))

        if (root_right - right_base).Length > 1e-9:
            edges.append(Part.makeLine(right_base, root_right))

        next_left_angle = center_angle + tooth_pitch_angle - half_angle_start
        root_mid_angle = (
            center_angle + half_angle_start + next_left_angle
        ) / 2.0
        root_mid = polar(root_radius, root_mid_angle)
        edges.append(
            Part.Arc(root_right, root_mid, next_root_left).toShape()
        )

    wire = Part.Wire(edges)
    if not wire.isClosed():
        raise RuntimeError("Wire pinion không kín.")
    return wire


def transformed_wire_copy(wire, z_value, rotation_deg):
    section = wire.copy()
    section.Placement = App.Placement(
        App.Vector(0.0, 0.0, z_value),
        App.Rotation(App.Vector(0.0, 0.0, 1.0), rotation_deg),
    )
    return section


def helical_loft_section_count(total_twist_deg):
    intervals = int(
        math.ceil(abs(total_twist_deg) / HELICAL_TARGET_TWIST_STEP_DEG)
    )
    sections = intervals + 1
    sections = max(HELICAL_MIN_LOFT_SECTIONS, sections)
    sections = min(HELICAL_MAX_LOFT_SECTIONS, sections)
    return sections


def make_pinion_shape(
    normal_module,
    transverse_module,
    teeth,
    transverse_pressure_angle_deg,
    total_backlash_transverse,
    face_width,
    bore_diameter,
    gear_type,
    helix_angle_deg,
    helix_hand,
):
    """Tạo pinion spur hoặc helical."""
    wire = make_pinion_profile_wire(
        normal_module=normal_module,
        transverse_module=transverse_module,
        teeth=teeth,
        transverse_pressure_angle_deg=transverse_pressure_angle_deg,
        total_backlash_transverse=total_backlash_transverse,
    )

    gear_type = normalize_gear_type(gear_type)

    if gear_type == "spur":
        face = Part.Face(wire)
        if face.isNull():
            raise RuntimeError("Không tạo được mặt pinion spur.")
        pinion = face.extrude(App.Vector(0.0, 0.0, face_width))
        total_twist_deg = 0.0
    else:
        beta = math.radians(float(helix_angle_deg))
        pitch_radius = transverse_module * teeth / 2.0
        sign = helix_hand_sign(helix_hand)

        total_twist_rad = sign * face_width * math.tan(beta) / pitch_radius
        total_twist_deg = math.degrees(total_twist_rad)
        section_count = helical_loft_section_count(total_twist_deg)

        sections = []
        for index in range(section_count):
            fraction = index / float(section_count - 1)
            z_value = face_width * fraction
            # Twist đối xứng quanh mặt phẳng giữa để phase tại z=b/2 = 0.
            rotation_deg = total_twist_deg * (fraction - 0.5)
            sections.append(
                transformed_wire_copy(wire, z_value, rotation_deg)
            )

        try:
            pinion = Part.makeLoft(sections, True, False)
        except Exception as exc:
            raise RuntimeError(
                "Loft pinion helical thất bại. Hãy thử giảm beta hoặc face width. "
                "Chi tiết: {}".format(exc)
            )

        if pinion.isNull():
            raise RuntimeError("Loft pinion helical trả về shape rỗng.")

    bore = Part.makeCylinder(
        bore_diameter / 2.0,
        face_width + 2.0,
        App.Vector(0.0, 0.0, -1.0),
    )
    result = safe_refine(pinion.cut(bore))
    return result, total_twist_deg


def append_unique(points, point, tolerance=1e-10):
    if not points or (point - points[-1]).Length > tolerance:
        points.append(point)


def clip_monotonic_polyline_x(points, x_min, x_max):
    """Cắt polyline có x không giảm vào khoảng [x_min, x_max]."""
    clipped = []

    for start, end in zip(points[:-1], points[1:]):
        dx = end.x - start.x

        if end.x < x_min or start.x > x_max:
            continue

        if abs(dx) <= 1e-14:
            if x_min <= start.x <= x_max:
                append_unique(clipped, start)
                append_unique(clipped, end)
            continue

        t0 = max(0.0, (x_min - start.x) / dx)
        t1 = min(1.0, (x_max - start.x) / dx)

        if t0 > t1:
            continue

        clipped_start = App.Vector(
            start.x + dx * t0,
            start.y + (end.y - start.y) * t0,
            0.0,
        )
        clipped_end = App.Vector(
            start.x + dx * t1,
            start.y + (end.y - start.y) * t1,
            0.0,
        )

        append_unique(clipped, clipped_start)
        append_unique(clipped, clipped_end)

    if len(clipped) < 2:
        raise RuntimeError("Không cắt được biên dạng rack.")

    clipped[0] = App.Vector(x_min, clipped[0].y, 0.0)
    clipped[-1] = App.Vector(x_max, clipped[-1].y, 0.0)
    return clipped


def rack_vertical_limits(normal_module, base_thickness):
    addendum = normal_module
    dedendum = 1.25 * normal_module
    root_y = -dedendum
    tip_y = addendum
    bottom_y = root_y - base_thickness
    return bottom_y, root_y, tip_y


def make_rack_profile_face(
    normal_module,
    transverse_module,
    profile_length,
    transverse_pressure_angle_deg,
    total_backlash_transverse,
    base_thickness,
):
    """Tạo tiết diện rack trong mặt phẳng transverse XY."""
    pressure_angle = math.radians(transverse_pressure_angle_deg)
    circular_pitch = math.pi * transverse_module
    addendum = normal_module
    dedendum = 1.25 * normal_module

    member_thinning = total_backlash_transverse / 2.0
    tooth_thickness_pitch = circular_pitch / 2.0 - member_thinning
    half_width_pitch = tooth_thickness_pitch / 2.0

    half_width_tip = half_width_pitch - addendum * math.tan(pressure_angle)
    half_width_root = half_width_pitch + dedendum * math.tan(pressure_angle)

    if half_width_tip <= 0.0:
        raise ValueError("Đỉnh răng rack bị nhọn hoặc đảo biên dạng.")

    root_y = -dedendum
    tip_y = addendum
    bottom_y = root_y - base_thickness

    x_min = -profile_length / 2.0
    x_max = profile_length / 2.0

    extended_min = x_min - circular_pitch
    extended_max = x_max + circular_pitch
    first_index = int(
        math.floor((extended_min - half_width_root) / circular_pitch)
    ) - 1
    last_index = int(
        math.ceil((extended_max + half_width_root) / circular_pitch)
    ) + 1

    top_boundary = [App.Vector(extended_min, root_y, 0.0)]

    for index in range(first_index, last_index + 1):
        center_x = index * circular_pitch
        tooth_points = (
            App.Vector(center_x - half_width_root, root_y, 0.0),
            App.Vector(center_x - half_width_tip, tip_y, 0.0),
            App.Vector(center_x + half_width_tip, tip_y, 0.0),
            App.Vector(center_x + half_width_root, root_y, 0.0),
        )

        if tooth_points[-1].x < extended_min:
            continue
        if tooth_points[0].x > extended_max:
            break

        for point in tooth_points:
            append_unique(top_boundary, point)

    append_unique(top_boundary, App.Vector(extended_max, root_y, 0.0))
    top_boundary.sort(key=lambda point: point.x)

    clipped_top = clip_monotonic_polyline_x(
        top_boundary,
        x_min,
        x_max,
    )

    polygon_points = [
        App.Vector(x_min, bottom_y, 0.0),
        App.Vector(x_max, bottom_y, 0.0),
    ]
    polygon_points.extend(reversed(clipped_top))
    polygon_points.append(polygon_points[0])

    wire = Part.makePolygon(polygon_points)
    if not wire.isClosed():
        raise RuntimeError("Wire rack không kín.")

    face = Part.Face(wire)
    if face.isNull():
        raise RuntimeError("Không tạo được mặt rack.")

    return face


def make_rack_shape(
    normal_module,
    transverse_module,
    rack_length,
    transverse_pressure_angle_deg,
    total_backlash_transverse,
    face_width,
    base_thickness,
    gear_type,
    helix_angle_deg,
    helix_hand,
):
    """Tạo rack spur hoặc rack helical tương thích."""
    gear_type = normalize_gear_type(gear_type)

    if gear_type == "spur":
        face = make_rack_profile_face(
            normal_module=normal_module,
            transverse_module=transverse_module,
            profile_length=rack_length,
            transverse_pressure_angle_deg=transverse_pressure_angle_deg,
            total_backlash_transverse=total_backlash_transverse,
            base_thickness=base_thickness,
        )
        return safe_refine(
            face.extrude(App.Vector(0.0, 0.0, face_width))
        ), 0.0

    beta = math.radians(float(helix_angle_deg))
    sign = helix_hand_sign(helix_hand)
    total_shift = sign * face_width * math.tan(beta)

    # Profile phải dài hơn để sau oblique extrusion vẫn cắt được về đúng L.
    circular_pitch = math.pi * transverse_module
    extended_length = (
        rack_length + abs(total_shift) + 4.0 * circular_pitch
    )

    face = make_rack_profile_face(
        normal_module=normal_module,
        transverse_module=transverse_module,
        profile_length=extended_length,
        transverse_pressure_angle_deg=transverse_pressure_angle_deg,
        total_backlash_transverse=total_backlash_transverse,
        base_thickness=base_thickness,
    )

    # Symmetric shift: tại z=b/2, phase rack = 0 giống pinion.
    start_face = face.copy()
    start_face.translate(App.Vector(-0.5 * total_shift, 0.0, 0.0))
    swept = start_face.extrude(
        App.Vector(total_shift, 0.0, face_width)
    )

    bottom_y, _root_y, tip_y = rack_vertical_limits(
        normal_module,
        base_thickness,
    )
    y_margin = max(1e-6, normal_module * 1e-5)
    clip_box = Part.makeBox(
        rack_length,
        (tip_y - bottom_y) + 2.0 * y_margin,
        face_width,
        App.Vector(
            -rack_length / 2.0,
            bottom_y - y_margin,
            0.0,
        ),
    )

    rack = safe_refine(swept.common(clip_box))
    return rack, total_shift


def validate_single_solid(shape, label):
    if shape.isNull():
        raise RuntimeError("{} là shape rỗng.".format(label))
    if not shape.isValid():
        raise RuntimeError("{} có B-Rep không hợp lệ.".format(label))
    if len(shape.Solids) != 1:
        raise RuntimeError("{} không phải một solid đơn.".format(label))
    if shape.Volume <= 0.0:
        raise RuntimeError("{} có thể tích không hợp lệ.".format(label))


def placed_copy(shape, placement):
    """Bake rigid placement vào B-Rep để xuất assembly ổn định."""
    result = shape.copy()
    matrix = placement.toMatrix()

    try:
        result.transformShape(matrix, True, False)
    except TypeError:
        try:
            result.transformShape(matrix, True)
        except Exception:
            result.transformGeometry(matrix)
    except Exception:
        result.transformGeometry(matrix)

    result.Placement = App.Placement()
    return result


def interference_volume(first_shape, second_shape):
    common = first_shape.common(second_shape)
    if common.isNull():
        return 0.0
    return float(common.Volume)


# ============================================================
# FREECAD DOCUMENT AND FILE OUTPUT
# ============================================================


def unique_document_name(base_name):
    existing = set(App.listDocuments().keys())
    if base_name not in existing:
        return base_name

    index = 2
    while "{}_{}".format(base_name, index) in existing:
        index += 1
    return "{}_{}".format(base_name, index)


def writable_output_root():
    standard_paths = QtCore.QStandardPaths

    desktop_enum = getattr(standard_paths, "DesktopLocation", None)
    documents_enum = getattr(standard_paths, "DocumentsLocation", None)

    if desktop_enum is None:
        desktop_enum = standard_paths.StandardLocation.DesktopLocation
    if documents_enum is None:
        documents_enum = standard_paths.StandardLocation.DocumentsLocation

    candidates = [
        standard_paths.writableLocation(desktop_enum),
        standard_paths.writableLocation(documents_enum),
        os.path.expanduser("~"),
    ]

    for candidate in candidates:
        if candidate and os.path.isdir(candidate):
            return candidate

    return os.getcwd()


def unique_output_path(directory, stem, extension):
    candidate = os.path.join(directory, stem + extension)
    if not os.path.exists(candidate):
        return candidate

    index = 2
    while True:
        candidate = os.path.join(
            directory,
            "{}_{}{}".format(stem, index, extension),
        )
        if not os.path.exists(candidate):
            return candidate
        index += 1


def export_step_shape(shape, path):
    shape.exportStep(path)
    if not os.path.isfile(path) or os.path.getsize(path) <= 0:
        raise RuntimeError("Xuất STEP thất bại: {}".format(path))


def add_read_only_property(obj, property_type, name, group, value):
    obj.addProperty(property_type, name, group)
    setattr(obj, name, value)
    obj.setEditorMode(name, 1)


def create_document(
    rack_shape,
    pinion_shape,
    pinion_placement,
    calculated,
):
    document_name = unique_document_name(DOCUMENT_BASE_NAME)
    doc = App.newDocument(document_name)
    doc.Label = "Rack & Pinion Spur / Helical"

    rack_obj = doc.addObject("Part::Feature", "Rack")
    rack_obj.Label = "Rack"
    rack_obj.Shape = rack_shape

    pinion_obj = doc.addObject("Part::Feature", "Pinion")
    pinion_obj.Label = "Pinion"
    pinion_obj.Shape = pinion_shape
    pinion_obj.Placement = pinion_placement

    info = doc.addObject("App::FeaturePython", "CalculatedParameters")
    info.Label = "Calculated Parameters"

    add_read_only_property(
        info, "App::PropertyLength",
        "PinionOuterDiameter", "Input",
        calculated["outer_diameter"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "RackTotalLength", "Input",
        calculated["rack_length"],
    )
    add_read_only_property(
        info, "App::PropertyString",
        "GearType", "Input",
        calculated["gear_type"],
    )
    add_read_only_property(
        info, "App::PropertyString",
        "PinionTeethMode", "Input",
        calculated["teeth_mode"],
    )
    add_read_only_property(
        info, "App::PropertyInteger",
        "PinionTeeth", "Calculated",
        calculated["teeth"],
    )
    add_read_only_property(
        info, "App::PropertyAngle",
        "HelixAngle", "Helical",
        calculated["helix_angle_deg"],
    )
    add_read_only_property(
        info, "App::PropertyString",
        "HelixHand", "Helical",
        calculated["helix_hand"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "NormalModule", "Calculated",
        calculated["normal_module"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "TransverseModule", "Calculated",
        calculated["transverse_module"],
    )
    # Alias Module = normal module cho tương thích bản cũ.
    add_read_only_property(
        info, "App::PropertyLength",
        "Module", "Calculated",
        calculated["normal_module"],
    )
    add_read_only_property(
        info, "App::PropertyAngle",
        "NormalPressureAngle", "Calculated",
        calculated["normal_pressure_angle_deg"],
    )
    add_read_only_property(
        info, "App::PropertyAngle",
        "TransversePressureAngle", "Calculated",
        calculated["transverse_pressure_angle_deg"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "PitchDiameter", "Calculated",
        calculated["pitch_diameter"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "RootDiameter", "Calculated",
        calculated["root_diameter"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "NormalCircularPitch", "Calculated",
        calculated["normal_circular_pitch"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "TransverseCircularPitch", "RackCompatibility",
        calculated["transverse_circular_pitch"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "BacklashNormal", "Calculated",
        calculated["backlash_normal"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "BacklashTransverse", "Calculated",
        calculated["backlash_transverse"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "FaceWidth", "Calculated",
        calculated["face_width"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "BoreDiameter", "Calculated",
        calculated["bore_diameter"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "RackBaseThickness", "Calculated",
        calculated["rack_base_thickness"],
    )
    add_read_only_property(
        info, "App::PropertyFloat",
        "RackPitchCount", "Calculated",
        calculated["rack_pitch_count"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "NearestPreferredNormalModule", "Calculated",
        calculated["nearest_standard_module"],
    )
    add_read_only_property(
        info, "App::PropertyFloat",
        "ModuleDeviationPercent", "Calculated",
        calculated["module_deviation_percent"],
    )
    add_read_only_property(
        info, "App::PropertyAngle",
        "PinionTwistAcrossFace", "Helical",
        calculated["pinion_twist_deg"],
    )
    add_read_only_property(
        info, "App::PropertyLength",
        "RackShiftAcrossFace", "Helical",
        abs(calculated["rack_shift"]),
    )
    add_read_only_property(
        info, "App::PropertyVolume",
        "AssemblyInterferenceVolume", "Validation",
        calculated["interference_volume"],
    )
    add_read_only_property(
        info, "App::PropertyString",
        "DesignScope", "Validation",
        "Spur/helical rack-pinion; normal-system helical geometry; B-Rep CAD model, not ISO/AGMA load optimization",
    )

    doc.recompute()

    try:
        import FreeCADGui as Gui

        rack_obj.ViewObject.ShapeColor = (0.72, 0.78, 0.84)
        pinion_obj.ViewObject.ShapeColor = (0.86, 0.72, 0.52)
        info.ViewObject.Visibility = False

        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    except Exception:
        pass

    return doc, rack_obj, pinion_obj


# ============================================================
# MAIN
# ============================================================


def run():
    design = get_user_inputs()
    if design is None:
        App.Console.PrintMessage("Đã hủy tạo Rack & Pinion.\n")
        return None

    outer_diameter = design["outer_diameter"]
    rack_length = design["rack_length"]
    teeth = design["teeth"]
    teeth_mode = design["teeth_mode"]
    gear_type = design["gear_type"]
    helix_angle_deg = design["helix_angle_deg"]
    helix_hand = design["helix_hand"]

    normal_module = design["normal_module"]
    transverse_module = design["transverse_module"]
    nearest_standard_module = design["nearest_standard_module"]
    module_deviation_percent = design["module_deviation_percent"]
    rack_pitch_count = design["rack_pitch_count"]

    normal_pressure_angle_deg = design["normal_pressure_angle_deg"]
    transverse_pressure_angle_deg = design["transverse_pressure_angle_deg"]
    normal_circular_pitch = design["normal_circular_pitch"]
    transverse_circular_pitch = design["transverse_circular_pitch"]

    pitch_diameter = transverse_module * teeth
    pitch_radius = pitch_diameter / 2.0
    root_diameter = pitch_diameter - 2.5 * normal_module

    # Backlash chuẩn đặt ở normal plane, đổi sang transverse để dựng profile XY.
    backlash_normal = max(
        BACKLASH_RATIO * normal_module,
        MIN_BACKLASH_MM,
    )
    beta = math.radians(helix_angle_deg)
    cos_beta = math.cos(beta)
    backlash_transverse = backlash_normal / cos_beta

    face_width = FACE_WIDTH_FACTOR * normal_module
    rack_base_thickness = RACK_BASE_FACTOR * normal_module

    maximum_bore = (
        root_diameter - 2.0 * MIN_RIM_RADIAL_FACTOR * normal_module
    )
    minimum_bore = 1.5 * normal_module
    if maximum_bore <= minimum_bore:
        raise ValueError(
            "Không còn đủ vành chân răng cho lỗ trục theo quy tắc hiện tại."
        )

    bore_diameter = min(0.25 * outer_diameter, maximum_bore)
    bore_diameter = max(bore_diameter, minimum_bore)

    if bore_diameter >= root_diameter:
        raise ValueError("Lỗ trục vượt đường kính chân răng.")

    pinion_shape, pinion_twist_deg = make_pinion_shape(
        normal_module=normal_module,
        transverse_module=transverse_module,
        teeth=teeth,
        transverse_pressure_angle_deg=transverse_pressure_angle_deg,
        total_backlash_transverse=backlash_transverse,
        face_width=face_width,
        bore_diameter=bore_diameter,
        gear_type=gear_type,
        helix_angle_deg=helix_angle_deg,
        helix_hand=helix_hand,
    )

    rack_shape, rack_shift = make_rack_shape(
        normal_module=normal_module,
        transverse_module=transverse_module,
        rack_length=rack_length,
        transverse_pressure_angle_deg=transverse_pressure_angle_deg,
        total_backlash_transverse=backlash_transverse,
        face_width=face_width,
        base_thickness=rack_base_thickness,
        gear_type=gear_type,
        helix_angle_deg=helix_angle_deg,
        helix_hand=helix_hand,
    )

    validate_single_solid(pinion_shape, "Pinion")
    validate_single_solid(rack_shape, "Rack")

    # Pitch line rack tại y=0; tâm pinion cách pitch line đúng r=d/2.
    # Phase được căn ở mặt phẳng giữa z = face_width/2.
    gear_rotation_deg = -90.0 - 180.0 / teeth
    pinion_placement = App.Placement(
        App.Vector(0.0, pitch_radius, 0.0),
        App.Rotation(
            App.Vector(0.0, 0.0, 1.0),
            gear_rotation_deg,
        ),
    )

    pinion_assembly_shape = placed_copy(
        pinion_shape,
        pinion_placement,
    )

    overlap_volume = interference_volume(
        rack_shape,
        pinion_assembly_shape,
    )
    # Helical loft có thể tạo sai số B-Rep lớn hơn spur một chút.
    overlap_tolerance = max(
        1e-7,
        normal_module ** 3 * (1e-6 if gear_type == "helical" else 1e-7),
    )
    if overlap_volume > overlap_tolerance:
        raise RuntimeError(
            "Rack và pinion bị giao thoa {:.6g} mm³; vượt dung sai {:.6g} mm³. "
            "Nếu là helical, hãy thử giảm beta hoặc tăng backlash."
            .format(overlap_volume, overlap_tolerance)
        )

    calculated = {
        "outer_diameter": outer_diameter,
        "rack_length": rack_length,
        "teeth_mode": teeth_mode,
        "gear_type": gear_type,
        "helix_angle_deg": helix_angle_deg,
        "helix_hand": helix_hand if gear_type == "helical" else "none",
        "teeth": teeth,
        "normal_module": normal_module,
        "transverse_module": transverse_module,
        "nearest_standard_module": nearest_standard_module,
        "module_deviation_percent": module_deviation_percent,
        "rack_pitch_count": rack_pitch_count,
        "normal_pressure_angle_deg": normal_pressure_angle_deg,
        "transverse_pressure_angle_deg": transverse_pressure_angle_deg,
        "normal_circular_pitch": normal_circular_pitch,
        "transverse_circular_pitch": transverse_circular_pitch,
        "pitch_diameter": pitch_diameter,
        "root_diameter": root_diameter,
        "backlash_normal": backlash_normal,
        "backlash_transverse": backlash_transverse,
        "face_width": face_width,
        "rack_base_thickness": rack_base_thickness,
        "bore_diameter": bore_diameter,
        "pinion_twist_deg": pinion_twist_deg,
        "rack_shift": rack_shift,
        "interference_volume": overlap_volume,
    }

    doc, rack_obj, pinion_obj = create_document(
        rack_shape,
        pinion_shape,
        pinion_placement,
        calculated,
    )

    output_dir = os.path.join(
        writable_output_root(),
        OUTPUT_FOLDER_NAME,
    )
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if gear_type == "helical":
        type_tag = "HELICAL_b{:.1f}_{}".format(
            helix_angle_deg,
            helix_hand.upper(),
        )
    else:
        type_tag = "SPUR"

    dimension_tag = (
        "{}_{}_D{:.3f}_L{:.3f}_z{}_mn{:.4f}_{}"
        .format(
            type_tag,
            teeth_mode.upper(),
            outer_diameter,
            rack_length,
            teeth,
            normal_module,
            timestamp,
        )
        .replace(".", "p")
    )

    pinion_step = unique_output_path(
        output_dir,
        "Pinion_" + dimension_tag,
        ".step",
    )
    rack_step = unique_output_path(
        output_dir,
        "Rack_" + dimension_tag,
        ".step",
    )
    assembly_step = unique_output_path(
        output_dir,
        "RackAndPinion_Assembly_" + dimension_tag,
        ".step",
    )
    fcstd_path = unique_output_path(
        output_dir,
        "RackAndPinion_" + dimension_tag,
        ".FCStd",
    )

    assembly_shape = Part.makeCompound(
        [rack_shape, pinion_assembly_shape]
    )

    export_step_shape(pinion_shape, pinion_step)
    export_step_shape(rack_shape, rack_step)
    export_step_shape(assembly_shape, assembly_step)

    doc.recompute()
    doc.saveAs(fcstd_path)

    message = (
        "\n=== RACK & PINION SPUR / HELICAL V5 ===\n"
        "Gear type          : {}\n"
        "Teeth mode         : {}\n"
        "D_out pinion       : {:.4f} mm\n"
        "Rack length        : {:.4f} mm\n"
        "Pinion teeth z     : {}\n"
        "Helix beta         : {:.3f} deg\n"
        "Helix hand         : {}\n"
        "Normal module m_n  : {:.6f} mm\n"
        "Transverse m_t     : {:.6f} mm\n"
        "Module chuẩn gần   : {:.4f} mm\n"
        "Sai lệch module    : {:.3f} %\n"
        "Normal alpha_n     : {:.3f} deg\n"
        "Transverse alpha_t : {:.3f} deg\n"
        "Pitch diameter     : {:.4f} mm\n"
        "Normal pitch p_n   : {:.4f} mm\n"
        "Rack pitch p_t     : {:.4f} mm\n"
        "Backlash normal    : {:.4f} mm\n"
        "Backlash transv.   : {:.4f} mm\n"
        "Face width         : {:.4f} mm\n"
        "Bore diameter      : {:.4f} mm\n"
        "Pinion face twist  : {:.4f} deg\n"
        "Rack face shift    : {:.4f} mm\n"
        "Rack pitch count   : {:.3f}\n"
        "Interference volume: {:.6g} mm^3\n"
        "Output folder      : {}\n"
        "==========================================\n"
    ).format(
        gear_type.upper(),
        teeth_mode.upper(),
        outer_diameter,
        rack_length,
        teeth,
        helix_angle_deg,
        helix_hand.upper() if gear_type == "helical" else "NONE",
        normal_module,
        transverse_module,
        nearest_standard_module,
        module_deviation_percent,
        normal_pressure_angle_deg,
        transverse_pressure_angle_deg,
        pitch_diameter,
        normal_circular_pitch,
        transverse_circular_pitch,
        backlash_normal,
        backlash_transverse,
        face_width,
        bore_diameter,
        pinion_twist_deg,
        abs(rack_shift),
        rack_pitch_count,
        overlap_volume,
        output_dir,
    )

    App.Console.PrintMessage(message)

    if gear_type == "helical":
        type_summary = (
            "HELICAL beta={:.1f}° {}"
            .format(helix_angle_deg, helix_hand.upper())
        )
    else:
        type_summary = "SPUR"

    show_information(
        "Rack & Pinion hoàn tất",
        "Đã tạo {} pinion z={} ở chế độ {}.\n"
        "Rack đã tự đồng bộ normal module {:.6f} mm, "
        "transverse pitch {:.6f} mm và góc áp lực tương thích.\n\n"
        "Thư mục:\n{}"
        .format(
            type_summary,
            teeth,
            teeth_mode.upper(),
            normal_module,
            transverse_circular_pitch,
            output_dir,
        ),
    )

    return doc


def main():
    try:
        return run()
    except Exception as exc:
        App.Console.PrintError(traceback.format_exc() + "\n")
        show_error("Rack & Pinion — lỗi", str(exc))
        return None


main()
