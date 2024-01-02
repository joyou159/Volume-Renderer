import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QFileDialog, QWidget, QMessageBox
from PyQt5.uic import loadUi
import vtk
import os
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from VolumeRenderer import VolumeRenderer


class VTKMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the main window UI
        self.ui = loadUi('mainWindow.ui', self)
        self.resize(1200, 800)
        self.rendering_mode = None

        # Set up the layout
        layout = QVBoxLayout(self.ui.render_area)
        self.ui.Import_button.clicked.connect(self.browse)
        self.ui.clear_button.clicked.connect(self.clear_output)

        self.vtk_widget = self.create_vtk_widget()
        layout.addWidget(self.vtk_widget)

        self.volume_renderer = VolumeRenderer(self.vtk_widget, self)
        self.ui.IsoValue.setText(
            f"Iso Value: {self.volume_renderer.iso_value}")

        self.ui.SurfaceButton.toggled.connect(
            self.handle_radio_button_toggled)
        self.ui.RayCastButton.toggled.connect(
            self.handle_radio_button_toggled)

        # Set default radio button states
        self.ui.SurfaceButton.setChecked(True)
        # Initialize VolumeRenderer with the vtk_widget

    def create_vtk_widget(self):
        vtk_widget = QVTKRenderWindowInteractor(self.ui.render_area)
        vtk_widget.GetRenderWindow().Render()
        vtk_widget.Initialize()
        return vtk_widget

    def browse(self):

        folder_path = QFileDialog.getExistingDirectory(
            self, "Select DICOM Folder")

        if not self.has_dicom_files(folder_path):
            return
        else:
            if self.volume_renderer.visualize_flag:
                self.clear_output()
            dicom_reader = self.load_dicom_series(folder_path)
            if dicom_reader:
                self.volume_renderer.volume = dicom_reader
                self.volume_renderer.compute_intensity_values()
                if self.rendering_mode == 0:
                    # Surface Rendering
                    iso_value = self.volume_renderer.iso_value
                    self.volume_renderer.surface_rendering(
                        dicom_reader.GetOutput(), iso_value)
                elif self.rendering_mode == 1:
                    # Ray Casting Rendering
                    self.volume_renderer.ray_casting_rendering(
                        dicom_reader.GetOutput())

    def show_error_message(self, message):
        """
        Displays an error message to the user.

        Args:
            message (str): The error message to be displayed.

        Returns:
            None
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.exec()

    def load_dicom_series(self, directory):
        reader = vtk.vtkDICOMImageReader()
        reader.SetDirectoryName(directory)
        reader.Update()
        return reader

    def has_dicom_files(self, directory):
        if directory:
            dicom_files = [file for file in os.listdir(
                directory) if file.lower().endswith('.dcm')]
            return bool(dicom_files)
        else:
            self.show_error_message("DICOM files not found.")
            return False

    def handle_radio_button_toggled(self):
        """
        Handle the toggling of the output radio buttons.

        This function is called when the user toggles the output radio buttons.
        It updates the `output` variable based on the selected radio button.

        """
        if self.ui.SurfaceButton.isChecked():
            self.rendering_mode = 0
            self.ui.IsoValueSlider.setEnabled(True)
        elif self.ui.RayCastButton.isChecked():
            self.rendering_mode = 1

            self.ui.IsoValueSlider.setEnabled(False)

        self.volume_renderer.update_visualization()

    def clear_output(self):
        self.volume_renderer = VolumeRenderer(self.vtk_widget, self)
        self.ui.IsoValueSlider.setValue(0)
        self.volume_renderer.render_window.Render()

    def closeEvent(self, event):
        # Explicitly clean up VTK resources when the window is closed
        self.vtk_widget.GetRenderWindow().Finalize()
        self.vtk_widget.GetRenderWindow().SetInteractor(None)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VTKMainWindow()
    window.show()
    sys.exit(app.exec_())
