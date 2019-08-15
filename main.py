import csv
import sys
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout
import serial.tools.list_ports
import serial
import re
import datetime
import gps_tela
import time as t

dados_csv = []
erros_csv = []


class timerThread(QtCore.QThread):
    timeElapsed = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super(timerThread, self).__init__(parent)
        self.timeStart = None

    def start(self, timeStart):
        self.timeStart = timeStart
        return super(timerThread, self).start()

    def run(self):
        while self.parent().isRunning():
            self.timeElapsed.emit(t.time() - self.timeStart)
            t.sleep(1)


#Thread loop-gps
class Worker(QtCore.QThread):
    sig = pyqtSignal(str)
    sig_status = pyqtSignal(str)
    timeElapsed = QtCore.pyqtSignal(int)

    def __init__(self, port, timer, parent = None):
        super(Worker, self).__init__(parent)
        self.port = port
        self.timer = timer
        self.main_loop = True

        self.timerThread = timerThread(self)
        self.timerThread.timeElapsed.connect(self.timeElapsed.emit)

    def run(self):
        ser = serial.Serial(self.port, 9600, 8, 'N', 1, timeout=1)
        self.sig_status.emit(str("Aguardando..."))
        self.timerThread.start(t.time())
        gga_check = False
        rmc_check = False
        signal_sentence = ""
        while self.main_loop:
            ser.flushInput()
            while ser.read().decode("utf-8") != "$":
                pass
            line = ser.readline().decode("utf-8")
            print("recebido:", line)
            if checksum(line) and valid_line(line):
                self.sig_status.emit(str("Conectado"))
                if gga_check and rmc_check is True:
                    gga_check,rmc_check = False, False
                    self.sig.emit(str(signal_sentence))
                    QThread.sleep(self.timer)

                elif line[0:5] == "GPGGA":
                    if gga_check is True:
                        pass
                    else:
                        gga_check = True
                        latitude, longitude, satellite, altitude, time, date = parse_gga(line)
                        #lat, long, altitude, satelites, hora, data, velocidade
                        signal_sentence = latitude, longitude, altitude, satellite, time, date

                elif line[0:5] == "GPRMC":
                    if gga_check is False or rmc_check is True:
                        pass
                    else:
                        rmc_check = True
                        speed = parse_rmc(line)
                        signal_sentence = signal_sentence, speed

            elif checksum(line) is False:
                dados = line.split(",")
                tipo = dados[0]
                erro = "Checksum invalido"
                date = set_date()
                time = set_time()
                print(erro)
                linha = tipo, erro, time, date
                csv_builder_erro(linha)

            elif valid_line(line) is False:
                if line[0:5] == "GPGGA":
                    dados = line.split(",")
                    tipo = dados[0]
                    erro = "Satelite insuficiente: {}".format(dados[7])
                    date = set_date()
                    time = set_time()
                    print(erro)
                    linha = tipo, erro, time, date
                    csv_builder_erro(linha)
                elif line[0:5] == "GPRMC":
                    dados = line.split(",")
                    tipo = dados[0]
                    erro = "Sinal invalido: {}".format(dados[2])
                    date = set_date()
                    time = set_time()
                    print(erro)
                    linha = tipo, erro, time, date
                    csv_builder_erro(linha)


def csv_builder_erro(linha):
    erros_csv.append(linha)
    return erros_csv


def set_date():
    date_time = datetime.datetime.now()
    dia, mes, ano = (date_time.day, date_time.month, date_time.year)
    date = f"{dia}/{mes}/{ano}"
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


def set_time():
    time = datetime.datetime.now()
    hora, minuto, segundo = (time.hour, time.minute, time.second)
    time = f"{hora}:{minuto}:{segundo}"
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
            return True
        else:
            return False
    except:
        return False


def parse_gga(sentence):
    dados = sentence.split(",")
    print("dados", dados)
    time = set_time()
    date = set_date()
    latitude = convert_coord(dados[2:4])
    latitude = round(latitude,4)
    longitude = convert_coord(dados[4:6])
    longitude = round(longitude, 4)
    satellite = dados[7]
    altitude = (dados[9])
    return latitude, longitude, satellite, altitude, time, date


def parse_rmc(sentence):
    dados = sentence.split(",")
    print("dados", dados)
    speed = fix_speed(dados[7])
    speed = round(speed)
    return speed


class MainApp(QMainWindow, gps_tela.Ui_MainWindow):

    def __init__(self, parent=None):
        super(MainApp, self).__init__(parent)

        self.setupUi(self)
        self.port = ""
        self.lbl_status_txt.setText("Pausado")
        self.lbl_status_txt.setStyleSheet("color:red")

        # Start Button action:
        self.btn_start.clicked.connect(self.start_btn)
        self.btn_stop.clicked.connect(self.stop_btn)
        self.btn_apply.clicked.connect(self.apply_btn)

        ports = list(serial.tools.list_ports.comports())
        for i in ports:
            self.combo_port.addItem(str(i))

    @QtCore.pyqtSlot(int)
    def on_Worker_timeElapsed(self, seconds):
        self.txt_runtime.setPlainText(t.strftime("%H:%M:%S", t.gmtime(seconds)))
        if seconds > 43200:
            self.stop_btn()

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
        self.thread1.sig_status.connect(self.set_status)
        self.thread1.timeElapsed.connect(self.on_Worker_timeElapsed)
        self.btn_stop.setEnabled(True)
        self.btn_start.setEnabled(False)

    def stop_btn(self):
        try:
            self.thread1.main_loop = False
            self.lbl_status_txt.setText("Desconectado")
            self.lbl_status_txt.setStyleSheet("color:red")
            self.csv_writer()
            self.csv_writer_erro()
        except Exception as e:
            print("Problema salvando csv", str(e))
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def set_status(self, status):
        self.lbl_status_txt.setText(status)
        if status == "Aguardando...":
            self.lbl_status_txt.setStyleSheet("color:orange")
        elif status == "Conectado":
            self.lbl_status_txt.setStyleSheet("color: green")

    def csv_writer(self):
        with open("gps.csv", "w") as new_file:
            csv_writer = csv.writer(new_file, delimiter=",")
            csv_writer.writerow(["lat", "long", "altitude", "satelites", "hora", "data", "velocidade"])
            csv_writer.writerows(dados_csv)

    def csv_builder(self, linha):
        dados_csv.append(linha)
        return dados_csv

    def csv_writer_erro(self):
        with open("erro.csv", "w") as new_file:
            csv_writer = csv.writer(new_file, delimiter=",")
            csv_writer.writerow(["Tipo", "erro", "hora", "data"])
            csv_writer.writerows(erros_csv)

    def read_signal(self, sentence):
        sentence = re.sub("[()']", '', sentence)
        lista = sentence.split(",")
        latitude = lista[0]
        longitude = lista[1]
        altitude = lista[2]
        satellite = lista[3]
        time = lista[4]
        date = lista[5]
        speed = lista[6]

        #lat, long, altitude, velocidade, satelites, hora
        self.txt_latitude.setPlainText(latitude)
        self.txt_longitude.setPlainText(longitude)
        self.txt_altitude.setPlainText(altitude)
        self.txt_speed.setPlainText(str(speed))
        self.txt_satellite.setPlainText(str(satellite))
        self.txt_time.setPlainText(time)
        self.txt_date.setPlainText(date)
        linha_csv = latitude, longitude, altitude, satellite, time, date, speed
        self.csv_builder(linha_csv)
        tamanho_lista = len(dados_csv)
        print(f"tamanho da lista: {tamanho_lista}")

    def set_timer(self):
        if self.txt_timer.text() == "":
            t = 1
        else:
            t = self.txt_timer.text()
            t = int(t)
            if t < 1:
                t = 1
            elif t > 720:
                t = 720
        timer = t * 1
        timer = int(timer)
        return timer

    def connect_port(self):
        p = str(self.combo_port.currentText())
        port = p[0:4]
        return port


def main():
    app = QApplication(sys.argv)
    myapp = MainApp()
    myapp.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
