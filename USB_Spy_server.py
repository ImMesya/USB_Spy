from PyQt5.QtWidgets import (QWidget, QAction, QApplication, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QMenu, QPushButton, QSpinBox, QSystemTrayIcon, QTextEdit, QVBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QAbstractItemView, QCheckBox, QTreeWidget, QTreeWidgetItem, QMainWindow, QFileSystemModel, QTreeView)
from PyQt5.QtNetwork import (QTcpServer, QTcpSocket, QHostAddress, QUdpSocket, QNetworkInterface)
from PyQt5.QtCore import (QObject, QByteArray, QDataStream, QIODevice, QAbstractItemModel, QModelIndex, QXmlStreamWriter, QXmlStreamReader, QFile)
from PyQt5.QtGui import QIcon
from os import system, path, walk
import logging as log
from lang_dict import russian, english, ukraine

"""
USB_SPY - Server
Application receive information from USB_SPY - client about plugged in/out USB flash drives
"""

__author__ = 'Ruslan Messian Ovcharenko'
__version__ = '1.2'

class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()
        log.info('Starting application')
        self.configuration()

        self.createSettingsGroupBox()
        self.createUsersGroupBox()
        self.createActions()
        self.createTrayIcon()
        self.sessionOpened()
        self.sessionBroadcast()
        self.updateLanguage()

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.statusGroupBox)
        mainLayout.addWidget(self.SettingsGroupBox)
        mainLayout.addWidget(self.UsersGroupBox)

        self.trayIcon.show()
        self.setWindowTitle(self.language['WindowTitle'])
        self.setFixedSize(400, 500)
        self.setWindowIcon(QIcon('icon.ico'))
        self.setLayout(mainLayout)

    def configuration(self):
        self.xmlConfig = QFile("config.xml")
        if not path.exists("config.xml"):
            xmlWriter = QXmlStreamWriter()
            xmlWriter.setAutoFormatting(True)
            self.xmlConfig.open(QIODevice.WriteOnly)
            xmlWriter.setDevice(self.xmlConfig)
            xmlWriter.writeStartDocument()
            xmlWriter.writeComment("Do not change this parameters!")
            xmlWriter.writeStartElement("Variables")
            xmlWriter.writeAttribute("LANG", "english")
            xmlWriter.writeAttribute("IPADDRESS", "None")
            xmlWriter.writeAttribute("PORT", "5454")
            xmlWriter.writeAttribute("DURATION", "5")
            xmlWriter.writeAttribute("NTSTATE", "0")
            xmlWriter.writeEndElement()
            xmlWriter.writeEndDocument()
            self.xmlConfig.close()

        self.readConf()

    def readConf(self):
        self.language = english #default language if can't load from file
        try:
            self.xmlConfig.open(QIODevice.ReadOnly)
            xmlReader = QXmlStreamReader(self.xmlConfig)
            while not xmlReader.atEnd():
                xmlReader.readNext()
                if xmlReader.isStartElement():
                    self.LANG = xmlReader.attributes().value("LANG")
                    if self.LANG == 'russian':
                        self.confLANG = 'russian'
                        self.language = russian
                    elif self.LANG == 'english':
                        self.language = english
                        self.confLANG = 'english'
                    elif self.LANG == 'ukraine':
                        self.language = ukraine
                        self.confLANG = 'ukraine'
                    self.confIP = xmlReader.attributes().value("IPADDRESS")
                    self.ipAddress = self.confIP.replace('"', '')
                    self.PORT = int(xmlReader.attributes().value("PORT"))
                    self.duration = int(xmlReader.attributes().value("DURATION"))
                    self.ntState = int(xmlReader.attributes().value("NTSTATE"))
        except:
            log.warning('Can\'t load configuration from "config.xml"')
            QMessageBox.critical(self, self.language['errAtStartName'], self.language['ErrAtStart'], QMessageBox.Ok)
            self.quitLog()
            sys.exit(app.exec_())

    def sessionOpened(self): # opening ports for TCP session
        self.statusGroupBox = QGroupBox(self.language['StatusGroup'])

        self.server = QTcpServer()
        self.tcpSocket = QTcpSocket()
        self.server.newConnection.connect(self.acceptConnection)

        if self.ipAddress == 'None': # get ip address
            for ipAddress in QNetworkInterface.allAddresses():
                if ipAddress != QHostAddress.LocalHost and ipAddress.toIPv4Address() != 0:
                    self.ipAddress = ipAddress
                    break
            else:
                self.ipAddress = QHostAddress(QHostAddress.LocalHost)
            self.ipAddress = self.ipAddress.toString()

        self.server.listen(QHostAddress(self.ipAddress), self.PORT) # listen TCP port

        self.statusLabel = QLabel(self.language['StatusLabel'].format(self.ipAddress, self.PORT))
        log.info('Server started on IP:{0} port:{1}'.format(self.ipAddress, self.PORT))

        statusLayout = QHBoxLayout()
        statusLayout.addWidget(self.statusLabel)
        self.statusGroupBox.setLayout(statusLayout)

    def acceptConnection(self): # if new connection
        client = self.server.nextPendingConnection()
        client.readyRead.connect(self.startRead)

    def startRead(self): # get information from client
        client = QObject.sender(self)
        message = client.read(client.bytesAvailable())
        try:
            message = message.decode("utf-8").split('||')
            if message[0] == 'connect':
                log.warning('%s (%s) plugged in %s with S/N: %s'%(message[1], message[2], message[3], message[4]))
                status = 'in'
                self.usersList[message[1]] = message[2]
                self.updateTable()
            elif message[0] == 'disconnect':
                log.info('%s (%s) plugged out %s with S/N: %s'%(message[1], message[2], message[3], message[4]))
                status = 'out'
                self.usersList.pop(message[1])
                self.updateTable()
            elif message[0] == 'data':
                self.usersData(message[1])
            if self.ntState == False:
                self.showMessage(message, status)
        except UnicodeDecodeError as error:
            log.warning(error)
            return
        except IndexError as error:
            log.warning(error)
            return

    def sessionBroadcast(self): # listening UDP port for broadcasting message from client
        self.udpSocket = QUdpSocket()
        self.udpSocket.bind(4545)
        self.udpSocket.readyRead.connect(self.readBroadcast)

    def readBroadcast(self): # read broadcast message from client
        while self.udpSocket.hasPendingDatagrams():
            self.datagram, host, port = self.udpSocket.readDatagram(self.udpSocket.pendingDatagramSize())
            self.datagram = str(self.datagram, encoding='ascii')
            self.datagram = self.datagram.split(' ')
            if self.datagram[0] == 'give_ip':
                self.sendBroadcast(self.datagram[1])

    def sendBroadcast(self, ipadd): # answer to client. Send self Port
        self.tcpSocket.abort()
        self.tcpSocket.connectToHost(ipadd, 5000)
        self.tcpSocket.waitForConnected(2000)

        request = QByteArray()
        stream = QDataStream(request, QIODevice.WriteOnly)
        stream.writeUInt32(0)
        stream.writeRawData(b'show %d' % self.PORT)
        stream.device().seek(0)
        stream.writeUInt32(request.size())

        self.tcpSocket.write(request)
        self.tcpSocket.readyRead.connect(self.startRead)
        self.tcpSocket.disconnectFromHost()

    def setVisible(self, visible):
        self.minimizeAction.setEnabled(visible)
        self.restoreAction.setEnabled(self.isMaximized() or not visible)
        super(Window, self).setVisible(visible)

    def closeEvent(self, event):
        if self.trayIcon.isVisible():
            QMessageBox.information(self, "Systray", self.language['TrayClose'])
            self.hide()

    def showMessage(self, msg, stat): # message about plugged in/out USB flash drives
        if stat == 'in':
            self.trayIcon.showMessage(self.language['ClientName'].format(msg[0], msg[1]), self.language['ClientMessageIN'].format(msg[3], msg[4]), self.trayIcon.Information, self.durationSpinBox.value() * 1000)
        else:
            self.trayIcon.showMessage(self.language['ClientName'].format(msg[0], msg[1]), self.language['ClientMessageOUT'].format(msg[3], msg[4]), self.trayIcon.Information, self.durationSpinBox.value() * 1000)

    def updateLanguage(self): #set current language
        if self.languageList.currentText() == 'English':
            self.currentLanguage = 'english'
            self.language = english
        elif self.languageList.currentText() == 'Русский':
            self.currentLanguage = 'russian'
            self.language = russian
        elif self.languageList.currentText() == 'Українська':
            self.currentLanguage = 'ukraine'
            self.language = ukraine
        self.updateLanguageText()
        self.activeSave()

    def updateLanguageText(self): # update all buttons and labels to another language
        self.setWindowTitle(self.language['WindowTitle'])

        self.closeButton.setText(self.language['Close'])
        self.saveButton.setText(self.language['Save'])

        self.statusGroupBox.setTitle(self.language['StatusGroup'])
        self.SettingsGroupBox.setTitle(self.language['SettingsGroup'])
        self.UsersGroupBox.setTitle(self.language['UserGroup'])
        self.UsersGroupBox.setToolTip(self.language['UserToolTip'])

        self.durationLabel.setText(self.language['Duration'])
        self.durationLabel.setToolTip(self.language['Duration2'])
        self.languageLabel.setText(self.language['Language'])
        self.statusLabel.setText(self.language['StatusLabel'].format(self.ipAddress, self.PORT))
        self.notifiLable.setText(self.language['Notification'])

        self.durationSpinBox.setSuffix(self.language['DurationSuffix'])

        self.minimizeAction.setText(self.language['Minimize'])
        self.restoreAction.setText(self.language['Restore'])
        self.quitAction.setText(self.language['Quit'])

    def activeSave(self): # enable save button only when spinbox and language was changed
        self.saveButton.setEnabled(True)

        if (self.durationSpinBox.text().replace(self.language['DurationSuffix'], '') == str(self.duration)) and (self.currentLanguage == self.confLANG) and self.ntState == self.disableNotifi.isChecked():
            self.saveButton.setEnabled(False)

    def onSave(self): # save new parameters to configuration file
        with open('config.xml', 'r') as read_config:
            text = read_config.read()

        if self.disableNotifi.isChecked() == True:
            ntState = 1
        else: ntState = 0

        with open('config.xml', 'w') as replace_config:
            replace_config.write(text.replace('LANG="{0}" IPADDRESS="{1}" PORT="{2}" DURATION="{3}" NTSTATE="{4}"'.format(self.confLANG, self.confIP, self.PORT, self.duration, self.ntState), 'LANG="{0}" IPADDRESS="{1}" PORT="{2}" DURATION="{3}" NTSTATE="{4}"'.format(self.currentLanguage, self.ipAddress, self.PORT, self.durationSpinBox.text().replace(self.language['DurationSuffix'], ''), ntState)))

        self.duration = self.durationSpinBox.text().replace(self.language['DurationSuffix'], '')
        self.confIP = self.ipAddress
        self.confLANG = self.currentLanguage
        self.ntState = self.disableNotifi.isChecked()

        self.saveButton.setEnabled(False)
        log.info('Configuration was changed')

    def ColRow(self, row=0,column=0): # second loop for creating table
        while True:
            yield row, column
            if column == 0:
                column += 1
            else:
                column = 0
                row = row+1

    def updateTable(self): # update information in table
        self.usersTable.setRowCount(len(self.usersList))
        gen=self.ColRow()
        for key, value in self.usersList.items():
            self.usersTable.setItem(*next(gen), QTableWidgetItem(key))
            self.usersTable.setItem(*next(gen), QTableWidgetItem(value))

    def createSettingsGroupBox(self): # creation Settings Group Box
        self.SettingsGroupBox = QGroupBox(self.language['SettingsGroup'])

        self.durationLabel = QLabel(self.language['Duration'])
        self.durationLabel.setToolTip(self.language['Duration2'])

        self.durationSpinBox = QSpinBox()
        self.durationSpinBox.setSuffix(self.language['DurationSuffix'])
        self.durationSpinBox.setRange(5, 60)
        self.durationSpinBox.setValue(self.duration)
        self.durationSpinBox.valueChanged.connect(self.activeSave)
        self.durationLabel.setBuddy(self.durationSpinBox)

        self.disableNotifi = QCheckBox()
        self.disableNotifi.setChecked(self.ntState)
        self.disableNotifi.stateChanged.connect(self.activeSave)
        self.notifiLable = QLabel(self.language['Notification'])

        self.languageLabel = QLabel(self.language['Language'])
        self.languageList = QComboBox()
        self.languageList.addItems(['English', 'Русский', 'Українська'])
        if self.language == russian:
            self.languageList.setCurrentIndex(1)
        elif self.language == english:
            self.languageList.setCurrentIndex(0)
        elif self.language == ukraine:
            self.languageList.setCurrentIndex(2)
        self.languageList.currentTextChanged.connect(self.updateLanguage)
        self.languageLabel.setBuddy(self.languageList)

        self.settingsLayout = QGridLayout()
        self.settingsLayout.addWidget(self.languageLabel, 0, 0)
        self.settingsLayout.addWidget(self.languageList, 0, 1)
        self.settingsLayout.addWidget(self.notifiLable, 1, 0)
        self.settingsLayout.addWidget(self.disableNotifi, 1, 1)
        self.settingsLayout.addWidget(self.durationLabel, 2, 0)
        self.settingsLayout.addWidget(self.durationSpinBox, 2, 1)

        self.SettingsGroupBox.setLayout(self.settingsLayout)

    def createUsersGroupBox(self): # creation Users Group Box
        self.UsersGroupBox = QGroupBox(self.language['UserGroup'])
        self.UsersGroupBox.setToolTip(self.language['UserToolTip'])

        self.closeButton = QPushButton(self.language['Close'])
        self.closeButton.clicked.connect(self.closeEvent)

        self.saveButton = QPushButton(self.language['Save'])
        self.saveButton.setEnabled(False)
        self.saveButton.clicked.connect(self.onSave)

        self.usersList = {}
        self.usersTable = QTableWidget()
        self.usersTable.setColumnCount(2)
        self.usersTable.setHorizontalHeaderLabels(['Host name', 'IP Address'])
        self.usersTable.setColumnWidth(0, 170)
        self.usersTable.setColumnWidth(1, 170)
        self.usersTable.setSortingEnabled(True)
        self.usersTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        UsersVLayout = QVBoxLayout()
        UsersVLayout.addWidget(self.usersTable)
        UsersHLayout = QHBoxLayout()
        UsersHLayout.addWidget(self.saveButton)
        UsersHLayout.addWidget(self.closeButton)
        UsersVLayout.addLayout(UsersHLayout)
        self.UsersGroupBox.setLayout(UsersVLayout)

    def createActions(self): # actions in tray menu
        self.minimizeAction = QAction(self.language['Minimize'], self, triggered=self.hide)
        self.restoreAction = QAction(self.language['Restore'], self,
                triggered=self.showNormal)
        self.quitAction = QAction(self.language['Quit'], self,
                triggered=QApplication.instance().quit)
        self.quitAction.triggered.connect(self.quitLog)

    def quitLog(self):
        log.info('Application was closed')

    def createTrayIcon(self): # creation tray menu
         self.trayIconMenu = QMenu(self)
         self.trayIconMenu.addAction(self.minimizeAction)
         self.trayIconMenu.addAction(self.restoreAction)
         self.trayIconMenu.addSeparator()
         self.trayIconMenu.addAction(self.quitAction)

         self.trayIcon = QSystemTrayIcon(self)
         self.trayIcon.setContextMenu(self.trayIconMenu)
         self.trayIcon.setIcon(QIcon('icon.ico'))

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)
    log.basicConfig(filename='usbspy.log', level=log.DEBUG, format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    window = Window()
    window.show()
    sys.exit(app.exec_())
