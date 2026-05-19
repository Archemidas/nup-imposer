"""Main application window."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..core import apply_preset_to_settings
from ..core.color import (
    ColorSettings,
    ProfileInfo,
    RenderingIntent,
    list_installed_profiles,
)
from ..core.exporters import export_multichannel_tiff, export_pdf, export_tiff
from ..core.image_loader import LoadedImage, load_image
from ..core.imposition import ImpositionLayout, compute_layout
from ..core.ink_channels import InkSet, InkSetRegistry, get_default_ink_registry
from ..core.paper_sizes import PAPER_SIZES, custom_paper_size, get_paper_size
from ..core.presets import PresetRegistry, get_default_registry
from ..core.tac import estimate_tac
from ..version import __version__
from .preview_widget import PreviewWidget


WORKFLOW_LABELS = {
    "all": "All workflows",
    "inkjet": "Inkjet",
    "laser": "Laser",
    "commercial": "Commercial offset",
    "sublimation": "Sublimation",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Nup Imposer v{__version__}")
        self.resize(1220, 840)

        self.loaded_image: Optional[LoadedImage] = None
        self.current_layout: Optional[ImpositionLayout] = None
        self.color_settings = ColorSettings()
        self._installed_profiles: List[ProfileInfo] = []
        self.preset_registry: PresetRegistry = get_default_registry()
        self.ink_registry: InkSetRegistry = get_default_ink_registry()
        self.selected_ink_set: Optional[InkSet] = None

        self._build_ui()
        self._build_menu()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready - open an image to begin")

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # Left: controls
        controls_col = QVBoxLayout()
        controls_col.addWidget(self._build_input_group())
        controls_col.addWidget(self._build_paper_group())
        controls_col.addWidget(self._build_layout_group())
        controls_col.addWidget(self._build_preset_group())
        controls_col.addWidget(self._build_color_group())
        controls_col.addWidget(self._build_ink_tac_group())
        controls_col.addWidget(self._build_output_group())
        controls_col.addStretch(1)

        # Right: preview
        self.preview = PreviewWidget()

        root.addLayout(controls_col, 0)
        root.addWidget(self.preview, 1)

    def _build_input_group(self) -> QGroupBox:
        box = QGroupBox("Input Image")
        layout = QVBoxLayout(box)

        row = QHBoxLayout()
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Choose JPG / TIFF / PSD / PDF...")
        self.input_path_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_input)
        row.addWidget(self.input_path_edit, 1)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        self.info_label = QLabel("No image loaded.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #555;")
        layout.addWidget(self.info_label)

        return box

    def _build_paper_group(self) -> QGroupBox:
        box = QGroupBox("Output Paper")
        form = QFormLayout(box)

        self.paper_combo = QComboBox()
        for name in PAPER_SIZES:
            self.paper_combo.addItem(name)
        self.paper_combo.addItem("Custom...")
        self.paper_combo.currentTextChanged.connect(self._on_paper_changed)
        form.addRow("Preset:", self.paper_combo)

        self.custom_w = QDoubleSpinBox()
        self.custom_w.setRange(1.0, 60.0)
        self.custom_w.setValue(8.5)
        self.custom_w.setSuffix(" in")
        self.custom_w.setDecimals(3)
        self.custom_w.setEnabled(False)
        form.addRow("Custom width:", self.custom_w)

        self.custom_h = QDoubleSpinBox()
        self.custom_h.setRange(1.0, 60.0)
        self.custom_h.setValue(11.0)
        self.custom_h.setSuffix(" in")
        self.custom_h.setDecimals(3)
        self.custom_h.setEnabled(False)
        form.addRow("Custom height:", self.custom_h)

        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Auto (best fit)", "Portrait", "Landscape"])
        form.addRow("Orientation:", self.orientation_combo)

        return box

    def _build_layout_group(self) -> QGroupBox:
        box = QGroupBox("Imposition")
        form = QFormLayout(box)

        self.n_combo = QComboBox()
        for n in (1, 2, 3, 4, 6, 8, 9, 10, 12, 16, 20, 25):
            self.n_combo.addItem(f"{n}-up", n)
        self.n_combo.setCurrentText("4-up")

        form.addRow("Copies:", self.n_combo)

        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0.0, 5.0)
        self.margin_spin.setValue(0.25)
        self.margin_spin.setSuffix(" in")
        self.margin_spin.setDecimals(3)
        form.addRow("Margin:", self.margin_spin)

        self.gutter_spin = QDoubleSpinBox()
        self.gutter_spin.setRange(0.0, 5.0)
        self.gutter_spin.setValue(0.125)
        self.gutter_spin.setSuffix(" in")
        self.gutter_spin.setDecimals(3)
        form.addRow("Gutter:", self.gutter_spin)

        self.preview_btn = QPushButton("Calculate Layout")
        self.preview_btn.clicked.connect(self._on_calculate_layout)
        form.addRow("", self.preview_btn)

        return box

    def _build_preset_group(self) -> QGroupBox:
        """Quick-preset picker (printer + paper + ink combos)."""
        box = QGroupBox("Quick Preset")
        form = QFormLayout(box)

        self.workflow_combo = QComboBox()
        for key, label in WORKFLOW_LABELS.items():
            self.workflow_combo.addItem(label, key)
        self.workflow_combo.currentIndexChanged.connect(self._on_workflow_filter_changed)
        form.addRow("Workflow:", self.workflow_combo)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(280)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        form.addRow("Preset:", self.preset_combo)

        self.preset_notes = QLabel("")
        self.preset_notes.setWordWrap(True)
        self.preset_notes.setStyleSheet("color: #666; font-size: 11px; padding: 4px;")
        form.addRow("", self.preset_notes)

        # Populate after construction so signals don't fire on empty state
        self._populate_preset_combo("all")

        return box

    def _populate_preset_combo(self, workflow: str) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("(no preset)", None)
        presets = (self.preset_registry.all() if workflow == "all"
                   else self.preset_registry.by_workflow(workflow))
        for preset in presets:
            self.preset_combo.addItem(preset.label, preset.id)
        self.preset_combo.blockSignals(False)
        # Trigger refresh of notes for the (no preset) default
        self._on_preset_changed()

    def _build_color_group(self) -> QGroupBox:
        box = QGroupBox("Color Management")
        form = QFormLayout(box)

        self.dest_profile_combo = QComboBox()
        self.dest_profile_combo.addItem("(None - preserve embedded)", None)
        self.dest_profile_combo.addItem("Browse for ICC profile...", "__browse__")
        self.dest_profile_combo.currentIndexChanged.connect(self._on_dest_profile_changed)
        form.addRow("Destination:", self.dest_profile_combo)

        self.scan_btn = QPushButton("Scan installed profiles")
        self.scan_btn.clicked.connect(self._on_scan_profiles)
        form.addRow("", self.scan_btn)

        self.intent_combo = QComboBox()
        for intent in RenderingIntent:
            self.intent_combo.addItem(intent.label, intent)
        self.intent_combo.currentIndexChanged.connect(self._on_intent_changed)
        form.addRow("Rendering intent:", self.intent_combo)

        self.bpc_check = QCheckBox("Black point compensation")
        self.bpc_check.setChecked(True)
        self.bpc_check.toggled.connect(self._on_bpc_changed)
        form.addRow("", self.bpc_check)

        self.mirror_check = QCheckBox("Mirror output (sublimation)")
        self.mirror_check.setToolTip(
            "Flip the imposed sheet horizontally before saving - required for "
            "heat-press transfer printing."
        )
        self.mirror_check.toggled.connect(self._on_mirror_toggled)
        form.addRow("", self.mirror_check)

        self.soft_proof_check = QCheckBox("Soft-proof preview")
        self.soft_proof_check.setToolTip(
            "Show how the print will look on screen, simulating the destination profile."
        )
        self.soft_proof_check.toggled.connect(self._on_soft_proof_toggled)
        form.addRow("", self.soft_proof_check)

        self.gamut_check_box = QCheckBox("Gamut warning (out-of-gamut)")
        self.gamut_check_box.setToolTip(
            "Highlight pixels that cannot be reproduced by the destination profile."
        )
        self.gamut_check_box.toggled.connect(self._on_gamut_check_toggled)
        form.addRow("", self.gamut_check_box)

        return box

    def _build_ink_tac_group(self) -> QGroupBox:
        """Ink Set / TAC group (phase 4)."""
        box = QGroupBox("Ink Set / TAC")
        form = QFormLayout(box)

        self.ink_set_combo = QComboBox()
        self.ink_set_combo.setMinimumWidth(280)
        self.ink_set_combo.addItem("(None — standard TIFF export)", None)
        for ink_set in self.ink_registry.all():
            label = f"{ink_set.label} ({ink_set.n_channels}-ch)"
            self.ink_set_combo.addItem(label, ink_set.id)
        self.ink_set_combo.currentIndexChanged.connect(self._on_ink_set_changed)
        form.addRow("Ink set:", self.ink_set_combo)

        self.tac_limit_label = QLabel("—")
        self.tac_limit_label.setStyleSheet("color: #555;")
        form.addRow("TAC limit:", self.tac_limit_label)

        self.tac_check_btn = QPushButton("Check TAC…")
        self.tac_check_btn.setEnabled(False)
        self.tac_check_btn.clicked.connect(self._on_check_tac)
        form.addRow("", self.tac_check_btn)

        self.tac_result_label = QLabel("")
        self.tac_result_label.setWordWrap(True)
        self.tac_result_label.setStyleSheet("font-size: 11px; color: #333;")
        form.addRow("", self.tac_result_label)

        return box

    def _build_output_group(self) -> QGroupBox:
        box = QGroupBox("Output")
        form = QFormLayout(box)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 2400)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSuffix(" DPI")
        form.addRow("Resolution:", self.dpi_spin)

        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "TIFF (Photoshop)", "PDF (Acrobat)", "Both",
            "Multi-channel TIFF (DeviceN / RIP)",
        ])
        form.addRow("Format:", self.format_combo)

        self.preserve_icc = QCheckBox("Embed ICC profile")
        self.preserve_icc.setChecked(True)
        form.addRow("", self.preserve_icc)

        self.export_btn = QPushButton("Export...")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)
        form.addRow("", self.export_btn)

        return box

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_browse_input)
        file_menu.addAction(open_action)

        export_action = QAction("&Export...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # ----------------------------------------------------------- callbacks

    def _on_browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.jpg *.jpeg *.png *.tif *.tiff *.psd *.pdf)",
        )
        if not path:
            return
        try:
            self.loaded_image = load_image(path)
        except Exception as e:
            QMessageBox.critical(self, "Load failed", str(e))
            return
        self.input_path_edit.setText(path)
        img = self.loaded_image
        self.info_label.setText(
            f"<b>{Path(path).name}</b><br>"
            f"{img.width_px} x {img.height_px} px @ {img.dpi_x:.0f} DPI<br>"
            f"{img.width_in:.2f} x {img.height_in:.2f} inches<br>"
            f"Mode: {img.mode}    ICC: {'yes' if img.icc_profile else 'no'}"
        )
        self.statusBar().showMessage(f"Loaded {Path(path).name}")
        # Enable TAC check if an ink set is already selected
        if self.selected_ink_set is not None:
            self.tac_check_btn.setEnabled(True)
        self._on_calculate_layout()

    def _on_paper_changed(self, text: str) -> None:
        is_custom = text == "Custom..."
        self.custom_w.setEnabled(is_custom)
        self.custom_h.setEnabled(is_custom)

    def _resolve_paper(self):
        text = self.paper_combo.currentText()
        if text == "Custom...":
            return custom_paper_size(self.custom_w.value(), self.custom_h.value())
        return get_paper_size(text)

    def _on_calculate_layout(self) -> None:
        if not self.loaded_image:
            return
        paper = self._resolve_paper()
        n = self.n_combo.currentData()
        orientation_text = self.orientation_combo.currentText()
        if orientation_text.startswith("Portrait"):
            orientation = "portrait"
        elif orientation_text.startswith("Landscape"):
            orientation = "landscape"
        else:
            orientation = None

        try:
            self.current_layout = compute_layout(
                paper=paper,
                n=n,
                source_aspect=self.loaded_image.aspect,
                margin_in=self.margin_spin.value(),
                gutter_in=self.gutter_spin.value(),
                paper_orientation=orientation,
            )
        except Exception as e:
            QMessageBox.critical(self, "Layout failed", str(e))
            return

        self.preview.set_layout(self.current_layout, self.loaded_image, self.color_settings)
        layout = self.current_layout
        self.statusBar().showMessage(
            f"{layout.rows} x {layout.cols} on {layout.paper.name} "
            f"({layout.paper.width_in:.2f} x {layout.paper.height_in:.2f} in), "
            f"cell {layout.cell_width_in:.2f} x {layout.cell_height_in:.2f} in"
            f"{', rotated' if layout.source_rotated else ''}"
        )
        self.export_btn.setEnabled(True)

    # ------------------------------------------------------- color callbacks

    def _on_scan_profiles(self) -> None:
        """Populate the destination combo with profiles found in system dirs."""
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        try:
            self._installed_profiles = list_installed_profiles()
        except Exception as e:
            QMessageBox.warning(self, "Scan failed", str(e))
            self._installed_profiles = []
        finally:
            self.scan_btn.setEnabled(True)

        # Remember current selection
        current = self.dest_profile_combo.currentData()
        self.dest_profile_combo.blockSignals(True)
        self.dest_profile_combo.clear()
        self.dest_profile_combo.addItem("(None - preserve embedded)", None)
        for prof in self._installed_profiles:
            label = f"{prof.name}  [{prof.color_space}, {prof.device_class}]"
            self.dest_profile_combo.addItem(label, str(prof.path))
        self.dest_profile_combo.addItem("Browse for ICC profile...", "__browse__")
        # Restore selection if possible
        idx = self.dest_profile_combo.findData(current)
        if idx >= 0:
            self.dest_profile_combo.setCurrentIndex(idx)
        self.dest_profile_combo.blockSignals(False)
        self.scan_btn.setText(f"Rescan ({len(self._installed_profiles)} found)")

    def _on_dest_profile_changed(self) -> None:
        data = self.dest_profile_combo.currentData()
        if data == "__browse__":
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Choose destination ICC profile",
                "",
                "ICC profiles (*.icc *.icm);;All files (*)",
            )
            if not path:
                # Revert to None
                self.dest_profile_combo.setCurrentIndex(0)
                return
            # Insert as a new item just before the Browse entry
            insert_idx = self.dest_profile_combo.count() - 1
            self.dest_profile_combo.insertItem(insert_idx, Path(path).name, path)
            self.dest_profile_combo.setCurrentIndex(insert_idx)
            self.color_settings.dest_profile_path = Path(path)
        elif data is None:
            self.color_settings.dest_profile_path = None
        else:
            self.color_settings.dest_profile_path = Path(data)
        self.color_settings.dest_profile_bytes = None
        self._refresh_preview_color()

    def _on_intent_changed(self) -> None:
        self.color_settings.intent = self.intent_combo.currentData()
        if self.color_settings.soft_proof_enabled:
            self._refresh_preview_color()

    def _on_bpc_changed(self, checked: bool) -> None:
        self.color_settings.black_point_compensation = checked
        if self.color_settings.soft_proof_enabled:
            self._refresh_preview_color()

    def _on_soft_proof_toggled(self, checked: bool) -> None:
        self.color_settings.soft_proof_enabled = checked
        if checked and not self.color_settings.has_destination():
            QMessageBox.information(
                self,
                "Pick a destination",
                "Soft-proof needs a destination ICC profile. Select one from the "
                "Destination dropdown (Scan installed profiles, or Browse...).",
            )
        self._refresh_preview_color()

    def _on_gamut_check_toggled(self, checked: bool) -> None:
        self.color_settings.gamut_check = checked
        if self.color_settings.soft_proof_enabled:
            self._refresh_preview_color()

    def _on_mirror_toggled(self, checked: bool) -> None:
        self.color_settings.mirror_output = checked

    # ----------------------------------------------------- preset callbacks

    def _on_workflow_filter_changed(self) -> None:
        workflow = self.workflow_combo.currentData()
        self._populate_preset_combo(workflow)

    def _on_preset_changed(self) -> None:
        preset_id = self.preset_combo.currentData()
        if preset_id is None:
            self.preset_notes.setText("")
            return

        preset = self.preset_registry.find(preset_id)
        if preset is None:
            self.preset_notes.setText("")
            return

        # Apply preset to settings
        apply_preset_to_settings(preset, self.color_settings)

        # Reflect in the Color Management widgets
        # Intent combo
        for i in range(self.intent_combo.count()):
            if self.intent_combo.itemData(i) == preset.default_intent:
                self.intent_combo.blockSignals(True)
                self.intent_combo.setCurrentIndex(i)
                self.intent_combo.blockSignals(False)
                break
        # BPC
        self.bpc_check.blockSignals(True)
        self.bpc_check.setChecked(preset.default_bpc)
        self.bpc_check.blockSignals(False)
        # Mirror
        self.mirror_check.blockSignals(True)
        self.mirror_check.setChecked(preset.mirror_output)
        self.mirror_check.blockSignals(False)
        # Destination profile - find if resolved
        path = self.color_settings.dest_profile_path
        if path is not None:
            label = path.name
            # Add it to the combo if not already present
            idx = self.dest_profile_combo.findData(str(path))
            if idx < 0:
                insert_idx = self.dest_profile_combo.count() - 1
                self.dest_profile_combo.insertItem(insert_idx, label, str(path))
                idx = insert_idx
            self.dest_profile_combo.blockSignals(True)
            self.dest_profile_combo.setCurrentIndex(idx)
            self.dest_profile_combo.blockSignals(False)

        # Notes
        note = (
            f"<b>{preset.printer}</b>  /  {preset.paper}<br>"
            f"<i>{preset.ink_set}</i><br>"
        )
        if path is not None:
            note += f"Profile: <code>{path.name}</code><br>"
        else:
            note += (
                "<span style='color:#a60;'>Profile not found on this system - "
                "use Browse... in Destination to pick the matching ICC, or print "
                "with these settings via the driver.</span><br>"
            )
        if preset.notes:
            note += f"<br>{preset.notes}"
        self.preset_notes.setText(note)
        self.statusBar().showMessage(f"Applied preset: {preset.label}")
        self._refresh_preview_color()

    def _refresh_preview_color(self) -> None:
        if self.current_layout and self.loaded_image:
            self.preview.set_layout(self.current_layout, self.loaded_image, self.color_settings)

    # -------------------------------------------------- ink set / TAC callbacks

    def _on_ink_set_changed(self) -> None:
        ink_id = self.ink_set_combo.currentData()
        if ink_id is None:
            self.selected_ink_set = None
            self.tac_limit_label.setText("—")
            self.tac_check_btn.setEnabled(False)
            self.tac_result_label.setText("")
            return
        ink_set = self.ink_registry.find(ink_id)
        self.selected_ink_set = ink_set
        if ink_set is not None:
            self.tac_limit_label.setText(
                f"{ink_set.tac_limit:.0f}%  ({ink_set.n_channels} channels)"
            )
            self.tac_check_btn.setEnabled(self.loaded_image is not None)
            self.tac_result_label.setText("")

    def _on_check_tac(self) -> None:
        if not self.loaded_image or self.selected_ink_set is None:
            return

        try:
            img = self.loaded_image.pil_image.copy()
            # Apply color settings if a destination is set
            if self.color_settings.has_destination():
                from ..core.color import apply_transform, ensure_source_profile
                src = ensure_source_profile(self.loaded_image.icc_profile, img.mode)
                dest = self.color_settings.dest_source()
                img = apply_transform(
                    img, src, dest,
                    intent=self.color_settings.intent,
                    black_point_compensation=self.color_settings.black_point_compensation,
                )
            result = estimate_tac(img, tac_limit=self.selected_ink_set.tac_limit)
        except Exception as e:
            QMessageBox.warning(self, "TAC check failed", str(e))
            return

        # Display inline
        color = "#a00" if result.exceeds_limit else "#080"
        self.tac_result_label.setText(
            f"<span style='color:{color};'>"
            f"Avg {result.average_pct:.1f}%  &nbsp; "
            f"P95 {result.p95_pct:.1f}%  &nbsp; "
            f"Max {result.max_pct:.1f}%"
            + (f"  &nbsp; <b>⚠ {result.fraction_over*100:.1f}% over limit</b>"
               if result.exceeds_limit else "  &nbsp; ✓ OK")
            + "</span>"
        )
        # Also show detail dialog
        QMessageBox.information(self, "TAC Estimation", result.summary())

    # ------------------------------------------------------------ export

    def _on_export(self) -> None:
        if not (self.loaded_image and self.current_layout):
            QMessageBox.warning(self, "No layout", "Load an image and calculate the layout first.")
            return

        in_path = Path(self.input_path_edit.text())
        n = self.current_layout.n
        paper_short = self.current_layout.paper.name.split()[0].lower()
        default_name = f"{in_path.stem}_{n}up_{paper_short}"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to...",
            str(in_path.with_name(default_name)),
            "TIFF (*.tif);;PDF (*.pdf);;All files (*)",
        )
        if not path:
            return

        out_base = Path(path)
        if out_base.suffix.lower() in (".tif", ".tiff", ".pdf"):
            out_base = out_base.with_suffix("")

        fmt = self.format_combo.currentText()
        dpi = self.dpi_spin.value()
        preserve = self.preserve_icc.isChecked()

        try:
            if fmt.startswith("Multi-channel"):
                ink_set = self.selected_ink_set
                if ink_set is None:
                    QMessageBox.warning(
                        self, "No ink set",
                        "Select an ink set in the Ink Set / TAC group before exporting "
                        "multi-channel TIFF.",
                    )
                    return
                out_tiff = out_base.with_suffix(".tif")
                _, is_single = export_multichannel_tiff(
                    self.loaded_image, self.current_layout,
                    out_tiff, ink_set=ink_set, output_dpi=dpi,
                    color_settings=self.color_settings,
                )
                if not is_single:
                    QMessageBox.information(
                        self, "Exported as separate channels",
                        f"Multi-channel TIFF writer not available — wrote {ink_set.n_channels} "
                        f"individual channel files to:\n{out_base.parent}",
                    )
            else:
                if fmt.startswith("TIFF") or fmt == "Both":
                    out_tiff = out_base.with_suffix(".tif")
                    export_tiff(
                        self.loaded_image, self.current_layout,
                        out_tiff, output_dpi=dpi, preserve_icc=preserve,
                        color_settings=self.color_settings,
                    )
                if fmt.startswith("PDF") or fmt == "Both":
                    out_pdf = out_base.with_suffix(".pdf")
                    export_pdf(
                        self.loaded_image, self.current_layout,
                        out_pdf, output_dpi=dpi, preserve_icc=preserve,
                        color_settings=self.color_settings,
                    )
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))
            return

        self.statusBar().showMessage(f"Exported to {out_base.parent}")
        QMessageBox.information(self, "Done", f"Files written to:\n{out_base.parent}")

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About Nup Imposer",
            f"<b>Nup Imposer v{__version__}</b><br>"
            "N-up image imposition for print production.<br>"
            "ICC color management via lcms2.<br><br>"
            "Source: github.com/Archemidas/nup-imposer<br>"
            "MIT License",
        )
