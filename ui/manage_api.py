# Form implementation generated from reading ui file 'manage_api.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_api_keys_list(object):
    def setupUi(self, api_keys_list):
        api_keys_list.setObjectName("api_keys_list")
        api_keys_list.resize(1088, 535)
        self.frame = QtWidgets.QFrame(parent=api_keys_list)
        self.frame.setGeometry(QtCore.QRect(39, 100, 900, 351))
        self.frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame.setObjectName("frame")
        self.list_apis_table = QtWidgets.QTableWidget(parent=self.frame)
        self.list_apis_table.setGeometry(QtCore.QRect(0, 0, 900, 351))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.list_apis_table.sizePolicy().hasHeightForWidth())
        self.list_apis_table.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.list_apis_table.setFont(font)
        self.list_apis_table.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.list_apis_table.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.list_apis_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_apis_table.setDragEnabled(True)
        self.list_apis_table.setAlternatingRowColors(True)
        self.list_apis_table.setGridStyle(QtCore.Qt.PenStyle.DashLine)
        self.list_apis_table.setRowCount(0)
        self.list_apis_table.setObjectName("list_apis_table")
        self.list_apis_table.setColumnCount(6)
        item = QtWidgets.QTableWidgetItem()
        self.list_apis_table.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.list_apis_table.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.list_apis_table.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.list_apis_table.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.list_apis_table.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.list_apis_table.setHorizontalHeaderItem(5, item)
        self.list_apis_table.horizontalHeader().setCascadingSectionResizes(False)
        self.list_apis_table.horizontalHeader().setDefaultSectionSize(150)
        self.list_apis_table.horizontalHeader().setSortIndicatorShown(True)
        self.list_apis_table.horizontalHeader().setStretchLastSection(False)
        self.frame_2 = QtWidgets.QFrame(parent=api_keys_list)
        self.frame_2.setGeometry(QtCore.QRect(40, 30, 621, 61))
        self.frame_2.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_2.setObjectName("frame_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.frame_2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(parent=self.frame_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(False)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.add_new_api = QtWidgets.QPushButton(parent=self.frame_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.add_new_api.setFont(font)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("../assets/new.svg"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.add_new_api.setIcon(icon)
        self.add_new_api.setIconSize(QtCore.QSize(28, 28))
        self.add_new_api.setObjectName("add_new_api")
        self.horizontalLayout.addWidget(self.add_new_api)

        self.retranslateUi(api_keys_list)
        QtCore.QMetaObject.connectSlotsByName(api_keys_list)

    def retranslateUi(self, api_keys_list):
        _translate = QtCore.QCoreApplication.translate
        api_keys_list.setWindowTitle(_translate("api_keys_list", "API Management Interface"))
        self.list_apis_table.setSortingEnabled(True)
        item = self.list_apis_table.horizontalHeaderItem(0)
        item.setText(_translate("api_keys_list", "Exchange"))
        item = self.list_apis_table.horizontalHeaderItem(1)
        item.setText(_translate("api_keys_list", "API KEY"))
        item = self.list_apis_table.horizontalHeaderItem(2)
        item.setText(_translate("api_keys_list", "API SECRET"))
        item = self.list_apis_table.horizontalHeaderItem(3)
        item.setText(_translate("api_keys_list", "Passphrase"))
        item = self.list_apis_table.horizontalHeaderItem(4)
        item.setText(_translate("api_keys_list", "UID"))
        item = self.list_apis_table.horizontalHeaderItem(5)
        item.setText(_translate("api_keys_list", "Action(s)"))
        self.label.setText(_translate("api_keys_list", "You can manage the entries of the api keys in this interface"))
        self.add_new_api.setText(_translate("api_keys_list", "Add new entry"))
