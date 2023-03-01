from collections import OrderedDict
from enum import Enum

import pyvisa as visa

# scopeIp = 'TCPIP0::172.31.1.60::3000::SOCKET'
# dmmIp = 'TCPIP1::172.31.1.61::5025::SOCKET'
# psuIp = 'TCPIP2::172.31.1.62::5025::SOCKET'
#
# count = 0

class _EventStatus:
    _scope = None

    class Events(Enum):
        OPC = 1
        RQC = 2
        QYE = 4
        DDE = 8
        EXE = 16
        CME = 32
        URQ = 64
        PON = 128

    def __init__(self, gwScope):
        self._scope = gwScope

    def GetEventStatus(self):
        esr = self._scope.query('*ESR?')
        return esr

    def GetEventEnable(self):
        esr = self._scope.query('*ESE?')
        return esr

    def OperationComplete(self):
        opc = self._scope.query('*OPC?')
        return opc

class GWScope:



    class _EquipmentInfo:
        _manufacturer = ""
        _model = ""
        _sn = ""
        _version = ""
        _awg = False
        _la = False
        _aChan = 0
        _bw = 0

        def __init__(self, IDN):
            self._manufacturer, self._model, self._sn, self._version = IDN.split(',')
            if (self._model.startswith("MSO")):
                self._la = True
                if (self._model.endswith("EA")):
                    self._awg = True
            modNum = self._model[4:8]
            self._aChan = int(modNum[3])
            self._bw = int(modNum[1:3]) * 10
            pass

        @property
        def Manufacturer(self):
            return self._manufacturer

        @property
        def Model(self):
            return self._model

        @property
        def SerialNo(self):
            return self._sn

        @property
        def FirmwareVersion(self):
            return self._version

        @property
        def AWG(self):
            return self._awg

        @property
        def LogicAnalyzer(self):
            return self._la

        @property
        def AnalogChannels(self):
            return self._aChan

        @property
        def Bandwidth(self):
            return self._bw


    class _ArbitraryWaveformGenerator:
        _scope = None
        _status = None

        F_Max = 25_000_000

        V_Max_50 = 2.5
        V_Min_50 = 0.1

        V_Max_HZ = 5.0
        V_Min_HZ = 0.2

        class Impedance(Enum):
            Fifty = "FIFTy"
            HighZ = "HIGHZ"

        class Function(Enum):
            Arbitrary   = "ARBitrary"
            Sine        = "SINE"
            Square      = "SQUAre"
            Pulse       = "PULSe"
            Ramp        = "RAMP"
            DC          = "DC"
            Noise       = "NOISe"
            Sinc        = "SINC"
            Gaussian    = "GAUSsian"
            Lorentz     = "LOWRENTz"
            Exp_Rise    = "EXPRise"
            Exp_Fall    = "EXPFall"
            Haversine   = "HAVERSINe"
            Cardiac     = "CARDiac"



        def __init__(self, gwScope, gwSettings):
            self._scope = gwScope
            self._status = _EventStatus(gwScope)
            self._settings = gwSettings
            pass

        def Reset(self):
            # Does not appear to work, even on the scope itself (MSO-2204EA)
            self._scope.write(":AWG:UTIL PRESet")

        def _getImpedance(self, channel):
            return self._settings[":AWG{}:OUTPut:LOAd:IMPEDance".format(channel)]

        def _setImpedance(self, channel, impedance: Impedance):
            self._scope.write(":AWG{}:OUTPut:LOAd:IMPEDance {}".format(channel, impedance.value))
            self._settings[":AWG{}:OUTPut:LOAd:IMPEDance".format(channel)] = impedance.value

        @property
        def Chan1Impedance(self):
            return self._getImpedance('1')

        @property
        def Chan2Impedance(self):
            return self._getImpedance('2')

        @Chan1Impedance.setter
        def Chan1Impedance(self, impedance: Impedance):
            self._setImpedance('1', impedance)

        @Chan2Impedance.setter
        def Chan2Impedance(self, impedance: Impedance):
            self._setImpedance('2', impedance)





        def _getAmplitude(self, channel):
            return self._settings[":AWG{}:AMPlitude".format(channel)]

        def _setAmplitude(self, channel, voltage: float):
            if (((self._getImpedance(channel) == self.Impedance.HighZ.value) & (voltage >= self.V_Min_HZ) & (voltage <= self.V_Max_50)) |
                    ((self._getImpedance(channel) == self.Impedance.Fifty.value) & (voltage >= self.V_Min_50) & (voltage <= self.V_Max_50))):
                self._scope.write(":AWG{}:AMPlitude {:.5e}".format(channel, voltage))

                # Operaction Complete (*OPC?) seems to always return 1 (True)
                if (self._status.OperationComplete()):
                    self._settings[":AWG{}:AMPlitude".format(channel)] = "{:.5e}".format(voltage)
                else:
                    # TODO Command failure handling
                    print("The command failed")

            else:
                # Need to do something here for out of range frequency
                pass

        @property
        def Chan1Amplitude(self):
            return self._getAmplitude('1')

        @property
        def Chan2Amplitude(self):
            return self._getAmplitude('2')

        @Chan1Amplitude.setter
        def Chan1Amplitude(self, Amplitude: float):
            self._setAmplitude('1', Amplitude)

        @Chan2Amplitude.setter
        def Chan2Amplitude(self, Amplitude: float):
            self._setAmplitude('2', Amplitude)




        def _getFunction(self, channel):
            return self._settings[":AWG{}:FUNCtion".format(channel)]

        def _setFunction(self, channel, function: Function):
            self._scope.write(":AWG{}:FUNCtion {}".format(channel, function.value))
            self._settings[":AWG{}:FUNCtion".format(channel)] = function.value

        @property
        def Chan1Function(self):
            return self._getFunction('1')

        @property
        def Chan2Function(self):
            return self._getFunction('2')

        @Chan1Function.setter
        def Chan1Function(self, function: Function):
            self._setFunction('1', function)

        @Chan2Function.setter
        def Chan2Function(self, function: Function):
            self._setFunction('2', function)





        def _getFrequency(self, channel):
            return self._settings[":AWG{}:FREQuency".format(channel)]

        def _setFrequency(self, channel, frequency: float):
            if ((frequency > 0) & (frequency <= self.F_Max)):
                self._scope.write(":AWG{}:FREQuency {}".format(channel, frequency))
                self._settings[":AWG{}:FREQuency".format(channel)] = frequency
            else:
                # Need to do something here for out of range frequency
                pass

        @property
        def Chan1Frequency(self):
            return self._getFrequency('1')

        @property
        def Chan2Frequency(self):
            return self._getFrequency('2')

        @Chan1Frequency.setter
        def Chan1Frequency(self, frequency: float):
            self._setFrequency('1', frequency)

        @Chan2Frequency.setter
        def Chan2Frequency(self, frequency: float):
            self._setFrequency('2', frequency)



        def _getState(self, channel):
            return self._settings[":AWG{}:OUTPut:STATE".format(channel)]

        def _setState(self, channel, state: str):
            self._scope.write(":AWG{}:OUTPut:STATE {}".format(channel, state))
            self._settings[":AWG{}:OUTPut:STATE".format(channel)] = state

        @property
        def Chan1State(self):
            return self._getState('1')

        @property
        def Chan2State(self):
            return self._getState('2')

        def Chan1On(self):
            self._setState('1', 'ON')

        def Chan1Off(self):
            self._setState('1', 'OFF')

        def Chan2On(self):
            self._setState('2', 'ON')

        def Chan2Off(self):
            self._setState('2', 'OFF')




    # TODO Allow dynamic changing of timeout
    _timeout = 2500             # timeout in milliseconds
    _terminator = '\n'
    _ip = ""
    _port = ""
    _scope = ""
    _settings = {}
    _equipInfo = None
    _awg = None

    def __init__(self, IP, Port, Timeout=None):
        try:
            rm = visa.ResourceManager('@py')
            connectString = 'TCPIP0::{}::{}::SOCKET'.format(IP, Port)
            self._ip = IP
            self._port = Port
            self._scope = rm.open_resource(connectString)
            if (Timeout != None):
                self._timeout = Timeout

            self._scope.timeout = self._timeout
            self._scope.read_termination = self._terminator
            self._equipInfo = self._EquipmentInfo(self._scope.query("*IDN?"))
            settings = self._scope.query("*LRN?")
            if (settings.endswith(';')):
                settings = settings[:-1]
            for setting in settings.split(';'):
                if (setting.count(' ') == 2):
                    k1, k2, v1 = setting.split(' ')
                    setting = "{}_{} {}".format(k1, k2, v1)
                key, value = setting.split(' ')
                self._settings[key] = value

            self._settings = OrderedDict(sorted(self._settings.items()))
            self._awg = self._ArbitraryWaveformGenerator(self._scope, self._settings)

        except Exception as e:
            print(e)


    @property
    def EquipmentInfo(self):
        return self._equipInfo

    @property
    def Settings(self):
        return self._settings

    @property
    def AWG(self):
        return self._awg




#
# def Connect(IP, Port):
#     try:
#         global count
#         rm = visa.ResourceManager('@py')
#         connectString = 'TCPIP{}::{}::{}::SOCKET'.format(str(count), IP, Port)
#         scope = rm.open_resource(connectString)
#         scope.timeout = 2500
#         scope.read_termination='\n'
#         x = scope.query("*IDN?")
#         count += 1
#         return scope
#
#     except Exception as e:
#         print(e)
#         pass
#
#     return

# def main():
#     rm = visa.ResourceManager('@py')
#     scope = rm.get_instrument(scopeIp)
#     dmm = rm.get_instrument(dmmIp)
#     psu = rm.get_instrument(psuIp)
#     pass

