from PySide6 import QtWidgets, QtCore


class AboutWindow(QtWidgets.QDialog):
   def __init__(self):
      super(AboutWindow, self).__init__()

      self.setFixedSize(340, 260)
      self.setWindowTitle('About Classy')

      layout = QtWidgets.QVBoxLayout(self)
      aboutLabel = QtWidgets.QLabel(
         (
            '<span style="font-size:16pt; font-weight:bold;">Classy</span><br>'
            '<span style="font-size:8pt; color:#555; font-weight:bold;">31-Mar-2026</span><br><br>'
            '<span style="font-size:10pt;">The plugin is located on the menu bar.</span><br><br><br>'
            '<span style="font-size:12pt; font-weight:bold;">Credits:</span><br><br>'
            '<span style="font-size:10pt;">RicBent</span><br>'
            '<span style="font-size:10pt;">Treeki</span><br><br>'
            '<span style="font-size:10pt; color:#555">github.com/RicBent/Classy</span>'
         ),
         parent=self
      )
      aboutLabel.setAlignment(QtCore.Qt.AlignCenter)
      layout.addWidget(aboutLabel)

      self.show()
