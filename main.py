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
        # either (0--> surface rendering, 1--> ray-casting rendering)
        self.rendering_mode = None

        # put the QOpenGLWidget in a vertical layout
        layout = QVBoxLayout(self.ui.render_area)
        self.vtk_widget = self.create_vtk_widget()  # create a custom VTK widget
        # add this widget to the vertical layout
        layout.addWidget(self.vtk_widget)

        self.ui.Import_button.clicked.connect(self.browse)
        self.ui.clear_button.clicked.connect(self.clear_output)

        self.volume_renderer = VolumeRenderer(self.vtk_widget, self)

        self.ui.IsoValue.setText(
            # displaying the initial value of the iso Value (0)
            f"Iso Value: {self.volume_renderer.iso_value}")

        self.ui.SurfaceButton.toggled.connect(
            self.handle_radio_button_toggled)
        self.ui.RayCastButton.toggled.connect(
            self.handle_radio_button_toggled)

        self.ui.SurfaceButton.setChecked(True)

    def create_vtk_widget(self):
        """
        Create and return a VTK (Visualization Toolkit) widget.

        This function initializes a VTK widget using the QVTKRenderWindowInteractor class
        and configures it for rendering. The widget is intended for use within a graphical
        user interface (GUI) and assumes the existence of a parent widget named 'render_area'
        (accessible through self.ui.render_area).

        Returns:
        QVTKRenderWindowInteractor: The configured VTK widget.

        """

        vtk_widget = QVTKRenderWindowInteractor(self.ui.render_area)
        vtk_widget.Initialize()
        return vtk_widget

    def browse(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select DICOM Folder")

        if not self.has_dicom_files(folder_path):
            return
        else:
            if self.volume_renderer.visualize_flag:  # there is an existing visualization
                self.clear_output()
            dicom_reader = self.load_dicom_series(
                folder_path)  # A VTK DICOM image reader

            if dicom_reader:
                self.volume_renderer.volume = dicom_reader  # the volume to be rendered
                # compute all the possible iso-values that exists in the render
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
        """
        Load a DICOM series from the specified directory using VTK.

        Parameters:
            directory (str): The path to the directory containing the DICOM series.

        Returns:
            vtk.vtkDICOMImageReader: A VTK DICOM image reader instance containing the
            loaded DICOM series.
        """
        reader = vtk.vtkDICOMImageReader()
        reader.SetDirectoryName(directory)
        reader.Update()
        return reader

    def has_dicom_files(self, directory):
        """
        Check if the specified directory contains DICOM files.

        Parameters:
            directory (str): The path to the directory to be checked.

        Returns:
            bool: True if DICOM files are found in the directory, False otherwise.

        """
        if directory:
            dicom_files = [file for file in os.listdir(
                directory) if file.lower().endswith('.dcm')]
            return bool(dicom_files)
        else:
            self.show_error_message(
                "DICOM files not found")
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
        # overwrite the existing VolumeRenderer object
        self.volume_renderer = VolumeRenderer(self.vtk_widget, self)
        self.ui.IsoValueSlider.setValue(0)  # reset the slider value
        # rendering the render window (refresh after clearing)
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
