from pathlib import Path
import subprocess, sys, os
base=Path(__file__).parent.resolve(); repo=Path(os.environ.get('OBK_SOURCE',base/'OpenBK7231T_App'))
sys.path.insert(0,os.environ.get('OBK_TESTDEPS',str(base/'testdeps')))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_R0

def function(src,name):
    a=src.index(name); a=src.rfind('\n',0,a)+1; b=src.index('{',a); level=1; k=b+1
    while level:
        level+=(src[k]=='{')-(src[k]=='}'); k+=1
    return src[a:k]
dma=function((repo/'src/driver/drv_spidma.c').read_text(encoding='utf8'),'bool SPIDMA_StartTXChecked')
raw=function((repo/'src/driver/drv_leds_shared.c').read_text(encoding='utf8'),'commandResult_t Strip_CMD_setRaw')
wire=function((repo/'src/driver/drv_ws2805.c').read_text(encoding='utf8'),'static byte WS2805_WireByte')
stub=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
typedef uint8_t byte;
void *memset(void *p, int v, size_t n) { unsigned char *s=p; while(n--) *s++=v; return p; }
size_t strlen(const char *s) { size_t n=0; while(s[n])n++; return n; }
#include "src/driver/ws2805_encode.h"
typedef unsigned TickType_t;
#define pdMS_TO_TICKS(x) (x)
#define HAL_ENABLE 1
#define HAL_DISABLE 0
#define SPI0_BASE 0
#define DMA_CH_4 4
#define SPI_DMA_TX_EN 0
#define SPI_STATUS_FLAG_TXE 1
#define SPI_STATUS_FLAG_BSY 2
#define DMA_STATUS_FLAG_TRAN_ERR 0
#define LOG_FEATURE_DRV 0
#define ADDLOG_ERROR(...) ((void)0)
static bool ln_spi_initialized=true, ws2805_mode=true, ln_full_duplex=true;
static unsigned tick, elapsed, remaining, dma_enabled, spi_dma_enabled, recovered, reset_us, scenario;
static int current_pin=6;
static struct { int base,pin; } g_pins[26];
struct spi_message { byte *send_buf; unsigned send_len; };
static unsigned xTaskGetTickCount(){return tick;}
static void vTaskDelay(int x){ tick+=x; elapsed+=x; if(scenario!=1 && elapsed>=2) remaining=0; }
static unsigned hal_clock_get_apb0_clk(){return 40000000;}
static unsigned hal_dma_get_data_num(int ch){return remaining;}
static void hal_dma_set_data_num(int ch,unsigned n){remaining=n;}
static void hal_dma_set_mem_addr(int ch,unsigned addr){}
static void hal_dma_en(int ch,int en){dma_enabled=en;}
static void hal_spi_dma_en(int spi,int dir,int en){spi_dma_enabled=en;}
static bool hal_spi_get_status_flag(int spi,int flag){return flag==SPI_STATUS_FLAG_TXE ? true : (scenario==3 || elapsed<5);}
static bool hal_dma_get_status_flag(int ch,int flag){return scenario==2 && elapsed>=2;}
static void SPIDMA_StopTX(){dma_enabled=spi_dma_enabled=0;}
static void hal_spi_en(int spi,int en){}
static void hal_spi_deinit(int spi){}
static unsigned spi_dr_get(int spi){return 0;}
static unsigned spi_sr_get(int spi){return 0;}
static void hal_gpio_pin_afio_en(int base,int pin,int en){}
static void HAL_PIN_Setup_Output(int pin){}
static void HAL_PIN_SetOutputValue(int pin,int val){}
static void HAL_Delay_us(int us){reset_us=us;}
static void SPIDMA_Init(struct spi_message *msg){recovered++;}
typedef int commandResult_t;
enum {CMD_RES_OK=0,CMD_RES_ERROR=1,CMD_RES_BAD_ARGUMENT=2,CMD_RES_NOT_ENOUGH_ARGUMENTS=3};
static byte data[50];
static int pushes,argc,bPush,offset;
static const char *hex;
static void setByte(unsigned i,byte x){ if(i<50)data[i]=x; }
static void apply(){pushes++;}
static struct { void(*setByte)(unsigned,byte);void(*apply)();bool(*isReady)();}led_backend={setByte,apply,0};
static unsigned pixel_count=10; static int pixel_size=5;
static void Tokenizer_TokenizeString(const char *args,int f){}
static int Tokenizer_GetArgsCount(){return argc;}
static int Tokenizer_GetArgInteger(int i){return i==0?bPush:offset;}
static const char *Tokenizer_GetArg(int i){return hex;}
static byte hexbyte(const char *s){byte n=0;for(int i=0;i<2;i++){char c=s[i];n=(n<<4)+(c<='9'?c-'0':(c&~32)-'A'+10);}return n;}
'''
tests=r'''
int main(){
 // Exhaustive byte encoding: check every high/low run, cells and guard bytes.
 byte encoded[28];
 for(unsigned v=0;v<256;v++){
  memset(encoded,0x5a,sizeof(encoded)); WS2805_EncodeByte(v,encoded+1);
  if(encoded[0]!=0x5a || encoded[27]!=0x5a)return 1;
  for(unsigned b=0;b<8;b++)for(unsigned i=0;i<26;i++){
   unsigned p=b*26+i;bool hi=(encoded[1+p/8]>>(7-p%8))&1;
   unsigned n=(v & (0x80>>b))?13:7;
   if(hi!=(i<n))return 2;
  }
 }
 if(WS2805_RESET_BYTES*8*50<300000)return 3;
 // Hardware-verified wire layout: 5 channel bytes + zero pad per pixel.
 for(unsigned i=0;i<50;i++)data[i]=i+1;
 raw=data;
 for(unsigned n=0;n<10*WS2805_WIRE_BYTES_PER_PIXEL;n++){
  byte want=n%6==5?0:data[n/6*5+n%6];
  if(WS2805_WireByte(n)!=want)return 22;
 }
 // Success waits for shifter, stalled DMA, bus busy, error, wrap and invalid lengths.
 struct spi_message msg={data,2100};
 for(scenario=0;scenario<4;scenario++){
  tick=0xfffffffc; elapsed=recovered=reset_us=0;
  bool ok=SPIDMA_StartTXChecked(&msg);
  if(dma_enabled || spi_dma_enabled)return 4;
  if(scenario==0){if(!ok || elapsed<5 || recovered)return 5;}
  else{if(ok || !recovered || reset_us<300 || elapsed>15)return 6;}
 }
 recovered=0;msg.send_len=65536;if(SPIDMA_StartTXChecked(&msg)||recovered)return 7;
 if(SPIDMA_StartTXChecked(0))return 8;
 // Raw command writes use offset and reject all malformed/oversized writes atomically.
 memset(data,0x55,50);argc=3;bPush=1;offset=48;hex="aB01";
 if(Strip_CMD_setRaw(0,0,0,0)!=CMD_RES_OK || data[48]!=0xab || data[49]!=1 || data[0]!=0x55 || pushes!=1)return 9;
 const char *bad[]={"00ff01","a","GG","00x0"};
 for(unsigned i=0;i<4;i++){hex=bad[i];if(Strip_CMD_setRaw(0,0,0,0)==CMD_RES_OK || data[48]!=0xab || pushes!=1)return 10;}
 hex="aa";offset=-1;if(Strip_CMD_setRaw(0,0,0,0)==CMD_RES_OK)return 11;
 offset=51;if(Strip_CMD_setRaw(0,0,0,0)==CMD_RES_OK)return 12;
 pixel_count=0;if(Strip_CMD_setRaw(0,0,0,0)==CMD_RES_OK)return 13;
 pixel_count=10;led_backend.setByte=0;if(Strip_CMD_setRaw(0,0,0,0)==CMD_RES_OK)return 14;
 return 0;
}
'''
testdir=base/'tests';testdir.mkdir(exist_ok=True);f=testdir/'firmware_harness.c'
ir=(repo/'src/driver/drv_tinyir_nec.c').read_text(encoding='utf8')
irglobals=ir[ir.index('static float ir_periodus'):ir.index('static inline unsigned char digitalReadFast')]
irstub=r'''
#define IOR_IRRecv 1
#define IOR_IRRecv_nPup 2
#define LOG_FEATURE_IR 0
#define ADDLOG_INFO(...) ((void)0)
static bool level=true;static int timer_result=0,timer_requests,timer_deinits,timer_stops;
static unsigned char digitalReadFast(unsigned char p){return level;}
static int PIN_FindPinIndexForRole(int role,int prev){return role==IOR_IRRecv?12:-1;}
static void HAL_PIN_Setup_Input(int p){}
static void HAL_PIN_Setup_Input_Pullup(int p){}
static int HAL_RequestHWTimer(float a,float *b,void(*fn)(void*),void *arg){timer_requests++;return timer_result;}
static void HAL_HWTimerStart(int p){}
static void HAL_HWTimerStop(int p){timer_stops++;}
static void HAL_HWTimerDeinit(int p){timer_deinits++;}
static bool last_level=true;
'''
irfunctions='\n'.join(function(ir,name)for name in ['static void DRV_IR_ISR','void TinyIR_NEC_Init','void TinyIR_NEC_Deinit'])
irtests=r'''
static void pulse(bool l,unsigned ticks){level=l;for(unsigned i=0;i<ticks;i++)DRV_IR_ISR(0);}
static void frame(unsigned val){pulse(0,180);pulse(1,90);for(unsigned b=0;b<32;b++){pulse(0,11);pulse(1,(val>>b)&1?34:11);}pulse(0,11);pulse(1,30);}
static int testIR(){
 timer_result=-1;TinyIR_NEC_Init();if(ir_chan!=-1)return 15;TinyIR_NEC_Deinit();if(timer_deinits||timer_stops)return 16;
 timer_result=0;TinyIR_NEC_Init();TinyIR_NEC_Init();if(timer_requests!=2 || ir_chan!=0 || recvpin!=12)return 17;
 pulse(1,100);frame(0xed12ff00);if(!irDataAvailable || _irData.addr!=0xff00 || _irData.cmd!=0x12 || _irData.keyHeld)return 18;
 irDataAvailable=false;pulse(0,180);pulse(1,45);pulse(0,11);pulse(1,30);
 if(!irDataAvailable || !_irData.keyHeld || _irData.cmd!=0x12)return 19;
 irDataAvailable=false;frame(0x0012ff00);if(irDataAvailable)return 20;
 TinyIR_NEC_Deinit();TinyIR_NEC_Deinit();if(timer_deinits!=1 || timer_stops!=1 || ir_chan!=-1 || recvpin!=-1)return 21;
 return 0;
}
'''
tests=tests.replace(' return 0;\n}', ' return testIR();\n}')
f.write_text(stub+'static byte *raw;\n'+wire+'\n'+dma+'\n'+raw+'\n'+irglobals+irstub+irfunctions+irtests+tests,encoding='utf8')
tool=Path(os.environ.get('ARM_GCC_BIN',base/'gcc10/gcc-arm-none-eabi-10.3-2021.10/bin'))
subprocess.run([str(tool/'arm-none-eabi-gcc.exe'),'-std=c99','-mcpu=cortex-m4','-mthumb','-O1','-nostdlib','-fno-builtin','-I'+str(repo),'-Wl,-Ttext=0x10000,-Tdata=0x18000,-e,main',str(f),'-lgcc','-o',str(testdir/'test.elf')],check=True)
subprocess.run([str(tool/'arm-none-eabi-objcopy.exe'),'-O','binary',str(testdir/'test.elf'),str(testdir/'test.bin')],check=True)
nm=subprocess.check_output([str(tool/'arm-none-eabi-nm.exe'),str(testdir/'test.elf')],text=True)
main=int(next(l.split()[0]for l in nm.splitlines()if l.endswith(' T main')),16)
u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.mem_map(0x10000,0x10000);u.mem_map(0x20000000,0x10000)
u.mem_write(0x10000,(testdir/'test.bin').read_bytes());u.reg_write(UC_ARM_REG_SP,0x2000fff0);u.reg_write(UC_ARM_REG_LR,0x1fff1)
u.emu_start(main|1,0x1fff0,count=10000000);result=u.reg_read(UC_ARM_REG_R0)
assert result==0, f'C firmware test failed: {result}'
print('PASS: 256 actual C encoder cases; 6-byte WS2805 wire layout with zero pad; DMA success/stall/error/SPI busy/tick wrap; raw offset/bounds/invalid hex/stopped backend.')
print('PASS: actual TinyIR NEC ISR full frame, held repeat, bad complement and timer start/stop/failure/restart guards.')
print('Timing: T0H=350ns T0L=950ns T1H=650ns T1L=650ns cell=1300ns reset=320us; frame(10 pixels x 48 bits)=944us.')


