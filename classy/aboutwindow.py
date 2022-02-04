from PyQt5 import QtWidgets, QtCore


class AboutWindow(QtWidgets.QDialog):
   def __init__(self):
      super(AboutWindow, self).__init__()

      self.setFixedSize(260, 120)
      self.setWindowTitle('About Classy')

      layout = QtWidgets.QVBoxLayout(self)
      aboutLabel = QtWidgets.QLabel('Classy\n\nRicBent, Treeki', self)
      aboutLabel.setAlignment(QtCore.Qt.AlignCenter)
      layout.addWidget(aboutLabel)

      self.show()
