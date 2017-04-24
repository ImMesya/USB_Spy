from PyQt5.QtWidgets import (QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout, QDialog, QRadioButton)
from PyQt5.QtGui import (QIcon)
from PyQt5.QtNetwork import QNetworkInterface

class Interfaces(QDialog):
	def __init__(self, lang):
		super(Interfaces, self).__init__()

		self.check = 0
		self.language = lang
		self.createIntList()

		self.setWindowIcon(QIcon('icon.ico'))
		self.setWindowTitle(lang['SecondTitle'])

	def createIntList(self):

		Vlayout = QVBoxLayout()

		okBtn = QPushButton('OK')
		okBtn.clicked.connect(self.onOkBtn)
		okBtn.setFixedSize(100, 25)
		Hlayout = QHBoxLayout()
		Hlayout.addWidget(okBtn)

		self.checks = []

		for interfaces in QNetworkInterface().allInterfaces():
			for ipadd in interfaces.interfaceFromName(interfaces.name()).addressEntries():
				c = QRadioButton(self.language['InterfacesList'].format(interfaces.humanReadableName(), ipadd.ip().toString(), 	interfaces.hardwareAddress()))
				Vlayout.addWidget(c)
				self.checks.append(c)

		Vlayout.addLayout(Hlayout)
		self.setLayout(Vlayout)

	def onOkBtn(self):
		for i in self.checks:
			if i.isChecked():
				ipadd = i.text().replace('IP: ', '').split(',')
				self.check = 1
				global IPADD
				IPADD = ipadd[1][1:]
				self.close()


		if self.check == 0:
			QMessageBox.information(self, self.language['SecondTitle'], self.language['warnInts'])

	def closeEvent(self, event):
		if self.check == 0:
			QMessageBox.information(self, self.language['SecondTitle'], self.language['cancelInts'])
			event.ignore()
