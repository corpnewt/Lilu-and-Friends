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

Currently Builds 58 Kexts:

* ACPIBacklight
* ACPIBatteryManager
* ALXEthernet
* AirportBrcmFixup
* Airportitlwm (10.13 High Sierra)
* Airportitlwm (10.14 Mojave)
* Airportitlwm (10.15 Catalina)
* Airportitlwm (11 Big Sur)
* Airportitlwm (12 Monterey)
* Airportitlwm (all versions)
* AlpsHID
* AppleALC
* AtherosE2200Ethernet
* BCM5722D
* BrcmPatchRAM (Acidanthera)
* BrightnessKeys
* CPUFriend
* CodecCommander
* DebugEnhancer
* ECEnabler
* FakePCIID
* FakeSMC (Kozlek)
* FakeSMC (Legacy)
* FakeSMC (RehabMan)
* FeatureUnlock
* GenericCardReaderFriend
* GenericUSBXHCI
* HWSensors (Kozlek)
* HWSensors (Legacy)
* HWSensors (RehabMan)
* HibernationFixup
* IntelBacklight
* IntelBluetoothFirmware
* IntelMausi (Acidanthera)
* IntelMausiEthernet
* Itlwm
* Lilu
* LucyRTL8125Ethernet
* NVMeFix
* NightShiftEnabler
* NoTouchID
* NullCPUPowerManagement
* RTCMemoryFixup
* RealtekCardReader
* RealtekCardReaderFriend
* RealtekRTL8100
* RealtekRTL8111
* RestrictEvents
* USBInjectAll
* USBInjectAll (Sniki)
* VirtualSMC
* VirtualSMC (All Tools)
* VoodooI2C
* VoodooInput
* VoodooPS2Controller
* VoodooPS2Controller (Acidanthera)
* VoodooRMI
* WhateverGreen
