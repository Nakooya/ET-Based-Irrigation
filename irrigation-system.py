"""
                                                DEPENDENCIES
Github Remote Repository: https://github.com/Nakooya/ET-Based-Irrigation/tree/master
APScheduler Documentation: https://apscheduler.readthedocs.io/en/3.x/userguide.html#basic-concepts
QtScheduler Examples: https://python.hotexamples.com/examples/apscheduler.schedulers.qt/QtScheduler/-/python-qtscheduler-class-examples.html
Pyeto Github: https://github.com/woodcrafty/PyETo
Pyeto Documentation: https://pyeto.readthedocs.io/en/latest/
Note: pip install pyeto not working
GPIO Zero: https://gpiozero.readthedocs.io/en/stable/recipes.html                               
"""


from logging import exception
from multiprocessing import current_process
from multiprocessing.heap import Arena
from winreg import EnableReflectionKey
import requests,pyeto,json,calendar
import time
import schedule
import gpiozero
import pickle

#Remove Comment when transfered to raspberry pi 
'''
import RPi.GPIO as GPIO
from time import sleep
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
'''



from apscheduler.schedulers.qt import QtScheduler
from datetime import date
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import QTime
#OpenWeather API Key
api_key = 'a048f036a050aab5d159597cf0d22e41'


class MyGUI(QMainWindow):

    ETo = 0
    Kc = 0
    ETc = 0
    rain_1h = 0
    RAW = 0
    ETcR = 0
    CumETcR = 0
    ETinInch = 0
    runtime = 0
    
    precipitationRate = 1.53
    GPM = 0.035
    Area = 2.197
    gallonToday = 0
    ETinInch = 0
    dripperCount = 4
    FinalPrecipRate = 0
    t = time.localtime()
    current_time_H = int(time.strftime("%H", t))
    current_time_M = int(time.strftime("%M", t))
    
    def __init__(self):
        super(MyGUI, self).__init__()
        uic.loadUi("main-window.ui", self)
        #LOAD VARIABLES
        self.loadData()
        #INITIALIZE ELEMENTS
        self.initializeButtons()
        

    def loadData(self):
        #Soil Depth text box
        loadDepth = str(pickle.load(open("depth.dat", "rb")))
        self.soilDepth.setText(loadDepth) 

        #Time Edit Input
        loadTimeH = int(pickle.load(open("TimeH.dat", "rb")))
        loadTimeM = int(pickle.load(open("TimeM.dat", "rb")))
        self.timeEdit.setTime(QTime(loadTimeH,loadTimeM,0))

        #Kc Radio Buttons
        loadKc = str(pickle.load(open("Kc.dat", "rb")))
        if loadKc == "init":
            self.Kc_init.setChecked(True)
            self.Kc = 0.3
        elif loadKc == "mid":
            self.Kc_mid.setChecked(True)
            self.Kc = 1.15
        elif loadKc == "late":
            self.Kc_late.setChecked(True)
            self.Kc = 0.4

        #Method Radio Buttons
        method = str(pickle.load(open("Method.dat", "rb")))
        if method == "Penman":
            self.pmRadioButton.setChecked(True)
        elif method == "Hargreaves":
            self.hargreavesRadioButton.setChecked(True)
        
    def initializeButtons(self):
        self.show()
        self.Kc_init.toggled.connect(self.calculateCropEvapotranspiration)
        self.Kc_mid.toggled.connect(self.calculateCropEvapotranspiration)
        self.Kc_late.toggled.connect(self.calculateCropEvapotranspiration)
        self.computeET.clicked.connect(self.calculateET)
        self.logs.setPlainText("Initialized Logs...")
        self.lcdNumber_2.display(0)
        self.schedButton.clicked.connect(self.setSchedule)
        self.manualSprinkler.clicked.connect(self.manualWater)
   
    def inputChecker(self):
        try:
            if self.pmRadioButton.isChecked():
                self.logs.append("Calculating using Penman-Monteith")
            elif self.hargreavesRadioButton.isChecked():
                self.logs.append("Calculating using Hargreaves Equation")
            else:
                raise Exception("No evapotranspiration method chosen")
            
            try:
                if self.Kc_init.isChecked():
                    self.logs.append("Initial Kc Chosen")
                elif self.Kc_mid.isChecked():
                    self.logs.append("Mid Kc Chosen")
                    
                elif self.Kc_late.isChecked():
                    self.logs.append("Late Kc Chosen")
                    
                else:
                    raise Exception("No Crop Coefficient Chosen")
                try:
                    if self.soilDepth.text() == '':
                        raise Exception("No Soil Depth input")
                except Exception as e:
                    message = QMessageBox()
                    message.setText("An Error Occured: " + str(e))
                    message.exec_()

            except Exception as e:
                message = QMessageBox()
                message.setText("An Error Occured: " + str(e))
                message.exec_()

        except Exception as e:
            message = QMessageBox()
            message.setText("An Error Occured: " + str(e))
            message.exec_()
   
    def manualWater(self):
        if self.manualSprinkler.isChecked():
            print("Solenoid Valve ON...")
            self.logs.append("Solenoid Valve ON...")
            self.manualSprinkler.setStyleSheet("background-color : Green")
            #GPIO.output(17, 1)
            
        else:
            print("Solenoid Valve OFF...")
            self.logs.append("Solenoid Valve OFF...")
            self.manualSprinkler.setStyleSheet("background-color : Gray")
            #GPIO.output(17, 0)
  
    def setSchedule(self):
        self.inputChecker()
        TE_time_H = int(self.timeEdit.time().hour())
        TE_time_M = int(self.timeEdit.time().minute())
        pickle.dump(TE_time_H, open("TimeH.dat", "wb"))
        pickle.dump(TE_time_M, open("TimeM.dat", "wb"))
        print("Time Edit Hour: ", TE_time_H)
        print("Time Edit Min: ", TE_time_M)
        #print("Current Hour: ",self.current_time_H)
        #print("Current Min: ", self.current_time_M)
        scheduler = QtScheduler()
        scheduler.add_job(self.calculateET, 'cron', id='scheduleET', hour = TE_time_H, minute = TE_time_M, second = 0)
        scheduler.start()
           
    def displayET(self):
        print("The ETo is", self.ETo)
        print("The Kc is", self.Kc)
        print("The ETc is", self.ETo * self.Kc)
       
    def calculatePenmanMonteith(self):
        #Get month value for extraterrestrial radiation
        et_radiation_bymonth = [29.9, 33.1, 36.1, 38.1, 38.4, 38.1, 38.1, 38, 36.7, 33.9, 30.6, 28.9]
        current_month = int(datetime.now().strftime('%m'))
        current_month_array = current_month-1
        print("Array Month: ",current_month_array)
        cs_radiation = pyeto.cs_rad(21, et_radiation_bymonth[current_month_array] )
        
        #Weather Data
        weather_data = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={14.524589860522429}&lon={121.1609810803121}&appid={api_key}&units=metric")
        print("API CODE: ",weather_data.status_code)
        areaName = weather_data.json()['name']
        print("Area Name: " , areaName)
        temp = weather_data.json()['main']['temp']
        #current Temperature Celsius
        print("Temperature: " , temp, "°Celsius")
        t = pyeto.celsius2kelvin(temp)
        #current temperature Kelvin
        print("Temperature: " , t, "°Kelvin")
        #Humidity Percentage
        humidity = weather_data.json()['main']['humidity']
        print("Humidity: ", humidity, "%")
        #Wind Speed
        ws = weather_data.json()['wind']['speed']
        print("Wind Speed: ",ws,"m/s")
        #Evapotranspiration Inputs
        #-------------------------#


        #Delta SVP
        min_temp = weather_data.json()['main']['temp_min']
        min_temp_in_k = pyeto.celsius2kelvin(min_temp)
        print("Min Temp in K: ", min_temp_in_k)
        max_temp = weather_data.json()['main']['temp_max']
        max_temp_in_k = pyeto.celsius2kelvin(max_temp)
        print("Max Temp in K: ", max_temp_in_k)
        mean_temp = (min_temp + max_temp)/2
        print("Mean Temp: ", mean_temp)
        mean_temp_in_k = pyeto.celsius2kelvin(mean_temp)
        print("Mean Temp in Kelvin: ", mean_temp_in_k, "deg Kelvin")
        delta_svp = pyeto.delta_svp(mean_temp)
        print("Delta SVP: ",delta_svp,"kPa")


        #Net Radiation
        sol_rad = pyeto.sol_rad_from_t(et_radiation_bymonth[current_month_array],cs_radiation,min_temp,max_temp,False)
        print("Solar Radiation: ", sol_rad, "MJ m-2 day-1")
        ni_sw_rad = pyeto.net_in_sol_rad(sol_rad, albedo=0.23)
        print("Net incoming solar radiation: ", ni_sw_rad, "MJ m-2 day-1")
        #Calculating the extraterrestrial radiation by month
        print("ET Rad: ",et_radiation_bymonth[current_month_array], "MJ m-2 day-1")


        #Actual Vapour Pressure (avp)
        svp_tmin = pyeto.svp_from_t(min_temp) 
        rh_max = humidity
        avp = pyeto.avp_from_rhmax(svp_tmin, rh_max)
        print("Actual Vapour Pressure: ", avp, "kPa")

        
        no_lw_rad = pyeto.net_out_lw_rad(min_temp_in_k,max_temp_in_k,sol_rad,cs_radiation,avp)
        print("Net outgoing solar radiation: ", no_lw_rad, "MJ m-2 day-1")
        net_rad = pyeto.net_rad(ni_sw_rad, no_lw_rad)
        print("Net Radiation: ",net_rad,"MJ m-2 day-1")


        #Saturated Vapour Pressure(svp)
        svp = pyeto.svp_from_t(temp)
        print("Saturated Vapour Pressure: ", svp, "kPa")


        #Psychrometric constant
        psy = pyeto.psy_const(97)
        print("Psychrometric Constant: ",psy,"kPa/degC")


        #Rain amount
        try: 
            self.rain_1h = weather_data.json()['rain']['1h']
            print("Rain amount in the past Hour: ", self.rain_1h, "mm")
        #self.rain_3h = weather_data.json()['rain']['3h']
        #print("Rain amount in the past 3 Hours: ", self.rain_3h, "mm")
        except:
            print("No rainfall")


        #Evapotranspiration using Penman-Monteith
        et_penman_monteith = pyeto.fao56_penman_monteith(net_rad, mean_temp_in_k, ws, svp, avp, delta_svp, psy, shf=0.0)
        print("The estimated evapotranspiration using Penman-Monteith Equation: ",et_penman_monteith, "mm/day")
        self.ETo = et_penman_monteith


        #Logs
        self.logs.append("Net Radiation: " + str(net_rad) + "MJ m-2 day-1")
        self.logs.append("Mean Temperature: " + str(mean_temp) + "°Kelvin")
        self.logs.append("Wind Speed: " + str(ws) + "m/s")
        self.logs.append("Saturated Vapour Pressure: " + str(svp) + "kPa")
        self.logs.append("Actual Vapour Pressure: " + str(avp) + "kPa")
        self.logs.append("Delta Saturated Vapour Pressure: " + str(avp))
        self.logs.append("Psychrometric constant: " + str(psy))
        self.logs.append("Evapotranspiration: " + str(self.ETo) + "mm/day")
        
    def calculateHargreaves(self):
        #Open Weather Map API Call
        weather_data = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={14.524589860522429}&lon={121.1609810803121}&appid={api_key}&units=metric")
        print("API CODE: ",weather_data.status_code)

        #Philippines Extraterrestrial Radiation per month in array
        et_radiation_bymonth = [29.9, 33.1, 36.1, 38.1, 38.4, 38.1, 38.1, 38, 36.7, 33.9, 30.6, 28.9]
        
        #Input Values
        min_temp = weather_data.json()['main']['temp_min']
        max_temp = weather_data.json()['main']['temp_max']
        mean_temp = (min_temp + max_temp)/2
        print("Min temp: ", min_temp, "deg C")
        print("Max temp: ", max_temp, "deg C")
        print("Mean temp: ", mean_temp, "deg C")

        #Get month value for extraterrestrial radiation
        current_month = int(datetime.now().strftime('%m'))
        current_month_array = current_month-1
        print("Array Month: ",current_month_array)
        print("ET Rad: ",et_radiation_bymonth[current_month_array], "MJ m-2 day-1")

        #Exapotranspiration Estimation using Hargreaves: pyeto.hargreaves(tmin, tmax, tmean, et_rad)
        et_hargreaves = pyeto.hargreaves(min_temp, max_temp,mean_temp, et_radiation_bymonth[current_month_array])
        evapotranspiration = et_hargreaves
        print("The estimated evapotranspiration using Hargreaves Equation: ", et_hargreaves,"mm/day")
        self.ETo = evapotranspiration

        #logs
        self.logs.append("Minimum Temperature: " + str(min_temp))
        self.logs.append("Maximum Temperature: " + str(max_temp))
        self.logs.append("Mean Temperature: " + str(mean_temp))
        self.logs.append("Extraterrestrial Radiation " + str(et_radiation_bymonth[current_month_array]))
        self.logs.append("Estimated Evapotranspiration using Hargreaves Equation: " + str(self.ETo) + "mm/day")

    def calculateCropEvapotranspiration(self):
        if self.Kc_init.isChecked():
            self.Kc = 0.3
            pickle.dump("init", open("Kc.dat", "wb"))
        elif self.Kc_mid.isChecked():
            self.Kc = 1.15
            pickle.dump("mid", open("Kc.dat", "wb"))
        elif self.Kc_late.isChecked():
            self.Kc = 0.4
            pickle.dump("late", open("Kc.dat", "wb"))
        self.lcdNumber_2.display(self.Kc)

    def calculateET (self):
       
        if self.pmRadioButton.isChecked():
            self.calculatePenmanMonteith()
            pickle.dump("Penman", open("Method.dat", "wb"))
        elif self.hargreavesRadioButton.isChecked():
            self.calculateHargreaves()
            pickle.dump("Hargreaves", open("Method.dat", "wb"))
  
        print("The ETo is", self.ETo)
        print("The Kc is", self.Kc)
        self.ETc = self.ETo * self.Kc
        print("The ETc is", self.ETc)
        self.ETcR = self.ETc - self.rain_1h
        print("ETC-R is: ",self.ETcR)
        self.CumETcR += self.ETcR
        print("Cumulative ETc-R is: ", self.CumETcR)
        depth = self.soilDepth.text()
        RAW = float(depth) * 0.69
        print("Total Readily Available Water(RAW): ", RAW, "mm" )
        #save soil depth value
        pickle.dump( depth , open("depth.dat","wb"))

        #current raw
        datRAW = float(pickle.load(open("cRAW.dat", "rb")))
        cRaw = datRAW - self.CumETcR
        print("Current RAW: ", cRaw)
        pickle.dump( cRaw, open("cRaw.dat", "wb"))
        ###########test
        self.convertETmmtoin(self.ETc)
        self.sprinklerHead()
        self.calculateRuntimeGallon()


    def convertETmmtoin(self, ETmm):
        self.ETinInch = ETmm * 0.04
        print("ETc in inches per day: ", self.ETinInch, "in/day")

    def sprinklerHead(self):
        self.FinalPrecipRate = self.precipitationRate/self.dripperCount
        print(self.dripperCount, "Dripper Head Precipitation rate: ", self.FinalPrecipRate,"in/hour")
        

    def calculateRuntimeGallon(self):
        self.runtime = (60*self.ETinInch)/(self.FinalPrecipRate)
        print("Runtime in minutes: ", self.runtime, "min")
        self.gallonToday = self.runtime * self.GPM
        print("Gallons Today: ", self.gallonToday, "Gal")


def main():
   app = QApplication([])
   window = MyGUI()
   app.exec_()
   

if __name__ == '__main__':
    main()
    
    
    
        


