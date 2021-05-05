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

Currently Builds 45 kexts:

* ACPIBacklight
* ACPIBatteryManager
* ALXEthernet
* AirportBrcmFixup
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
* GenericUSBXHCI
* HWSensors (Kozlek)
* HWSensors (Legacy)
* HWSensors (RehabMan)
* HibernationFixup
* IntelBacklight
* IntelMausi (Acidanthera)
* IntelMausiEthernet
* Lilu
* LucyRTL8125Ethernet
* NVMeFix
* NightShiftEnabler
* NoTouchID
* NullCPUPowerManagement
* RTCMemoryFixup
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
