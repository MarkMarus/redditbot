from error import Ui_MainWindow as ErrWindow

from PyQt5.QtWidgets import QMainWindow, QApplication


class Error(QMainWindow):
    def __init__(self):
        super(Error, self).__init__()

        self.ui = ErrWindow()
        self.ui.setupUi(self)

        self.setFixedSize(403, 200)


if __name__ == "__main__":
    app = QApplication([])
    win = Error()
    win.show()
    app.exec_()
