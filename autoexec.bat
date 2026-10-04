// LSC 3224261: LN882H + WS2805, 9 pixels, logical arguments R G B C W.
// P6 reuses the SM16703P_DIN pin role; WS2805 is the actual protocol driver.
PowerSave 0
SetPinRole 6 SM16703P_DIN
SetPinRole 12 IRRecv
SetPinRole 21 Btn_SmartLED
SetFlag 4 1
SetFlag 22 1
startDriver WS2805
WS2805_Init 9 BRGWC
stopDriver IR
startDriver TinyIR_NEC
LED_dimmer 30
LED_enableAll 0
// Optional pixel animations: startDriver PixelAnim
// Add learned IR_NEC address/command mappings below. See README.md.
