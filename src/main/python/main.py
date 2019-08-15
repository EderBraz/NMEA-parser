import csv
import sys

from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
import serial.tools.list_ports
import teste_bosta
import serial
import re
import datetime


class Worker(QtCore.QThread):
    sig = pyqtSignal(str)

    def __init__(self, port, timer):
        #QtCore.QThread.__init__(self, parent)
        super(Worker, self).__init__()
        self.port = port
        self.timer = timer

    def run(self):
        ser = serial.Serial(self.port, 9600, 8, 'N', 1, timeout=1)
        self.main_loop = True
        while self.main_loop:
            while ser.read().decode("utf-8") != "$":
                pass
            line = ser.readline().decode("utf-8")
            print("recebido:", line)
            if checksum(line) and valid_line(line):
                if line[0:5] == "GPGGA":
                    time, latitude, longitude, satellite, altitude = parse_gga(line)
                    # tipo, lat, long, altitude, velocidade, satelites, hora, data
                    tipo = line[0:5]
                    signal_sentence = tipo, latitude, longitude, altitude, "", satellite, time
                    self.sig.emit(str(signal_sentence))
                elif line[0:5] == "GPRMC":
                    time, latitude, longitude, speed = parse_rmc(line)
                    # tipo, lat, long, altitude, velocidade, satelites, hora, data
                    tipo = line[0:5]
                    signal_sentence = tipo, latitude, longitude, " ", speed, " ", time
                    self.sig.emit(str(signal_sentence))
                QThread.sleep(self.timer)


def set_date():
    date_time = datetime.datetime.now()
    dia, mes, ano = (date_time.day, date_time.month, date_time.year)
    date = (f"{dia}/{mes}/{ano}")
    return date


def fix_speed(speed):
    speed = float(speed) * 1.852
    return speed


def convert_coord(position):
    coord = "".join(position[0])
    cardeal = "".join(position[1])
    if not coord or coord == '0':
        return 0
    d, m = re.match(r'^(\d+)(\d\d\.\d+)$', coord).groups()
    coord = float(d) + (float(m) / 60)
    if cardeal == "S" or cardeal == "W":
        coord = -1 * coord
    return coord


#time to HH:MM:SS.sss
def format_time(time):
    time = time.replace(".", "")
    time = "{}{}:{}{}:{}{}".format(*time)
    #print(time)
    return time


def valid_line(line):
    dados = line.split(",")
    if dados[0] == "GPGGA":
        if int(dados[7]) >= 4:
            return True
        else:
            return False
    elif dados[0] == "GPRMC":
        if dados[2] == "A":
            return True
        else:
            return False


def checksum(line):
    line = line.strip("$")
    check_line = line.partition("*")
    checksum = 0
    for c in check_line[0]:
        checksum ^= ord(c)
    checksum = hex(checksum)
    try:
        digitos_checksum = int(check_line[2].rstrip(), 16)
        digitos_checksum = hex(digitos_checksum)
        if checksum == digitos_checksum:
            # print("checksum valido")
            return True
        else:
            # print("sentenca invalida")
            return False
    except:
        return False


def parse_gga(sentence):
    dados = sentence.split(",")
    print("dados", dados)
    time = format_time(dados[1])
    latitude = convert_coord(dados[2:4])
    latitude = round(latitude,4)
    longitude = convert_coord(dados[4:6])
    longitude = round(longitude, 4)
    satellite = dados[7]
    altitude = (dados[9])
    return time, latitude, longitude, satellite, altitude


def parse_rmc(sentence):
    dados = sentence.split(",")
    time = format_time(dados[1])
    latitude = convert_coord(dados[3:5])
    latitude = round(latitude, 4)
    longitude = convert_coord(dados[5:7])
    longitude = round(longitude, 4)
    speed = fix_speed(dados[7])
    speed = round(speed)
    return time, latitude, longitude, speed

date = set_date()
dados_csv = []


class MainApp(QMainWindow, teste_bosta.Ui_MainWindow):

    def __init__(self, parent=None):
        super(MainApp, self).__init__(parent)

        self.setupUi(self)

        self.port = ""
        # Start Button action:
        self.btn_start.clicked.connect(self.start_btn)
        self.btn_stop.clicked.connect(self.stop_btn)
        self.btn_apply.clicked.connect(self.apply_btn)
        self.txt_date.setPlainText(str(date))
        ports = list(serial.tools.list_ports.comports())
        for i in ports:
            self.combo_port.addItem(str(i))

    def apply_btn(self):
        self.port = self.connect_port()
        self.timer = self.set_timer()
        self.btn_start.setEnabled(True)
        print("port", self.port)
        print("timer", self.timer)
        return self.port, self.timer

    def start_btn(self):
        print(self.timer)
        self.thread1 = Worker(self.port, self.timer)
        self.thread1.start()
        self.thread1.sig.connect(self.read_signal)
        self.btn_stop.setEnabled(True)

    def stop_btn(self):
            try:
                self.thread1.main_loop = False
                self.csv_writer()
            except Exception as e:
                print("Problema salvando csv", str(e))

    def csv_writer(self):
        with open("gps.csv", "w") as new_file:
            csv_writer = csv.writer(new_file, delimiter=",")
            csv_writer.writerow(["Tipo", "lat", "long", "altitude", "velocidade", "satelites", "hora", "data"])
            #print("writer", dados_csv)
            csv_writer.writerows(dados_csv)

    def csv_builder(self, linha):
        dados_csv.append(linha)
        #print("builder", dados_csv)
        return dados_csv

    def read_signal(self, sentence):
        sentence = re.sub("[()']", '', sentence)
        lista = sentence.split(",")
        tipo = lista[0]
        latitude = lista[1]
        longitude = lista[2]
        altitude = lista[3]
        speed = lista[4]
        satellite = lista[5]
        time = lista[6]

        #lat, long, altitude, velocidade, satelites, hora
        self.txt_latitude.setPlainText(latitude)
        self.txt_longitude.setPlainText(longitude)
        if tipo == "GPGGA":
            self.txt_altitude.setPlainText(altitude)
        if tipo == "GPRMC":
            self.txt_speed.setPlainText(str(speed))
        if tipo == "GPGGA":
            self.txt_satellite.setPlainText(str(satellite))
        self.txt_time.setPlainText(time)
        linha_csv = tipo, latitude, longitude, altitude, speed, satellite, time, date
        self.csv_builder(linha_csv)

    def set_timer(self):
        if self.txt_timer.text() == "":
            t = 1
        else:
            t = self.txt_timer.text()
        timer = int(t) * 15
        return timer

    def connect_port(self):
        p = str(self.combo_port.currentText())
        port = p[0:4]
        return port


def main():
    app = QApplication(sys.argv)#
    myapp = MainApp()
    myapp.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
