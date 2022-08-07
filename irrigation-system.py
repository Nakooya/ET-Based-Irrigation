import requests,pyeto,json
import calendar
from datetime import date
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5 import uic
#OpenWeather API Key
api_key = 'a048f036a050aab5d159597cf0d22e41'


class MyGUI(QMainWindow):
    ETo = 0
    Kc = 0
    ETc = 0

    def __init__(self):
        super(MyGUI, self).__init__()
        uic.loadUi("main-window.ui", self)
        self.show()

        self.longitudeTB.setText("121.1609810803121")
        self.latitudeTB.setText("14.524589860522429")
        self.Kc_init.toggled.connect(self.calculateCropEvapotranspiration)
        self.Kc_mid.toggled.connect(self.calculateCropEvapotranspiration)
        self.Kc_late.toggled.connect(self.calculateCropEvapotranspiration)
        self.getData.clicked.connect(self.calculatePenmanMonteith)
        self.HargreavesButton.clicked.connect(self.calculatePenmanMonteith)
        text = "Initialized Logs..."
        self.logs.setPlainText(text)
        self.lcdNumber_2.display(0)
        self.pushButton.clicked.connect(self.displayET)

       
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


        #Evapotranspiration using Penman-Monteith
        et_penman_monteith = pyeto.fao56_penman_monteith(net_rad, mean_temp_in_k, ws, svp, avp, delta_svp, psy, shf=0.0)
        print("The estimated evapotranspiration using Penman-Monteith Equation: ",et_penman_monteith, "mm/day")
        self.ETo = et_penman_monteith

        #Logs
        self.logs.append("Net Radiation: " + str(net_rad) + "MJ m-2 day-1")
        #self.logs.append("Mean Temperature: " + str(mean_temp) + "°Kelvin")
        self.logs.append("Wind Speed: " + str(ws) + "m/s")
        self.logs.append("Saturated Vapour Pressure: " + str(svp) + "kPa")
        self.logs.append("Actual Vapour Pressure: " + str(avp) + "kPa")
        self.logs.append("Delta Saturated Vapour Pressure: " + str(avp))
        self.logs.append("Psychrometric constant: " + str(psy))
        
    

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
        

    def calculateCropEvapotranspiration(self):
        if self.Kc_init.isChecked():
            self.Kc = 0.3
        elif self.Kc_mid.isChecked():
            self.Kc = 1.15
        elif self.Kc_late.isChecked():
            self.Kc = 0.4
        self.lcdNumber_2.display(self.Kc)

       
      

def main():
   app = QApplication([])
   window = MyGUI()
   app.exec_()

if __name__ == '__main__':
    main()