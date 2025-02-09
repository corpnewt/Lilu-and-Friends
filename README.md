# Lilu-and-Friends
A python script that can download and build a number of kexts.

Additional SDKs can be found [here](https://github.com/phracker/MacOSX-SDKs) if need be.

 * Copy them to */Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs* to use
 * You may need to change the `MinimumSDKVersion` in */Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Info.plist* if using Xcode 7.3+

***

## To install:

Do the following one line at a time in Terminal:

    git clone https://github.com/corpnewt/Lilu-and-Friends
    cd Lilu-and-Friends
    chmod +x Run.command
    
Then run with either `./Run.command` or by double-clicking *Run.command*

***

Currently Builds 71 Kexts:

* ACPIBacklight
* ACPIBatteryManager
* ALXEthernet
* AirportBrcmFixup
* Airportitlwm (10.13 High Sierra)
* Airportitlwm (10.14 Mojave)
* Airportitlwm (10.15 Catalina)
* Airportitlwm (11 Big Sur)
* Airportitlwm (12 Monterey)
* Airportitlwm (13 Ventura)
* Airportitlwm (14.0 Sonoma)
* Airportitlwm (14.4 Sonoma)
* Airportitlwm (all versions)
* AlpsHID
* AlpsHID (150ms delay)
* AppleALC
* AtherosE2200Ethernet
* BCM5722D
* BrcmPatchRAM (Acidanthera)
* BrightnessKeys
* CPUFriend
* CodecCommander
* CpuTscSync
* CpuTscSync (AMD)
* DebugEnhancer
* ECEnabler
* FakePCIID
* FakeSMC (Kozlek)
* FakeSMC (Legacy)
* FakeSMC (RehabMan)
* FeatureUnlock
* ForgedInvariant
* GenericCardReaderFriend
* GenericUSBXHCI
* HWSensors (Kozlek)
* HWSensors (Legacy)
* HWSensors (RehabMan)
* HibernationFixup
* IntelBacklight
* IntelBluetoothFirmware
* IntelLucy
* IntelMausi (Acidanthera)
* IntelMausiEthernet
* Itlwm
* Lilu
* LucyRTL8125Ethernet
* NVMeFix
* NightShiftEnabler
* NoTouchID
* NootRX
* NootedRed
* NullCPUPowerManagement
* RTCMemoryFixup
* RealtekCardReader
* RealtekCardReaderFriend
* RealtekRTL8100
* RealtekRTL8111
* RestrictEvents
* SMCRadeonSensors (ChefKissInc)
* USBInjectAll
* USBInjectAll (Sniki)
* VirtualSMC
* VirtualSMC (All Tools)
* VoodooI2C
* VoodooInput
* VoodooPS2-ALPS
* VoodooPS2-ALPS (VoodooInput)
* VoodooPS2Controller
* VoodooPS2Controller (Acidanthera)
* VoodooRMI
* WhateverGreen
