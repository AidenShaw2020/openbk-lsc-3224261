"""Build the LN882H WS2805 test firmware from this source bundle."""
from pathlib import Path
import argparse, subprocess, os, sys, shutil, re
p=argparse.ArgumentParser()
p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parent.parent)
p.add_argument('--toolchain',type=Path,required=True,help='GCC Arm 10.3-2021.10 root')
p.add_argument('--cmake',default='cmake');p.add_argument('--ninja',default='ninja')
a=p.parse_args();r=a.repo.resolve();sdk=r/'sdk/OpenLN882H'
dependencies={'sdk/OpenLN882H':('https://github.com/openshwprojects/OpenLN882H.git','84149f251efc120561bdefa17ce399f62eadb8be'),
 'libraries/berry':('https://github.com/berry-lang/berry.git','b9ce913d9d43bb296d9604bc0cb4f2f68a6b703f')}
for path,(url,commit)in dependencies.items():
    d=r/path
    if not (d/'.git').exists():
        subprocess.run(['git','-c','http.sslBackend=openssl','clone','--no-checkout',url,str(d)],check=True)
        subprocess.run(['git','checkout','--detach',commit],cwd=d,check=True)
    elif subprocess.check_output(['git','rev-parse','HEAD'],cwd=d,text=True).strip()!=commit:
        raise SystemExit(f'{d} has a different revision; use a fresh source bundle.')
app=sdk/'project/OpenBeken/app'
if not app.exists():
    if os.name=='nt':subprocess.run(['cmd','/c','mklink','/J',str(app),str(r)],check=True)
    else:app.symlink_to(r,target_is_directory=True)
if app.resolve()!=r:raise SystemExit('SDK app link points to another source tree.')
f=sdk/'project/OpenBeken/gcc/gcc-custom-build-stage.cmake'
text=f.read_text();python=sys.executable.replace('\\','/')
text=re.sub(r'COMMAND\s+python3',f'COMMAND "{python}"',text);f.write_text(text)
f=sdk/'components/net/lwip-2.1.3/src/port/ln_osal/include/lwipopts.h';text=f.read_text()
text=re.sub(r'#define MEMP_NUM_UDP_PCB\s*\(4\)','#define MEMP_NUM_UDP_PCB (5)',text)
for key in ['LWIP_MDNS_RESPONDER','LWIP_NUM_NETIF_CLIENT_DATA']:
    if re.search(r'^\s*#define '+key+r'\b',text,re.M):text=re.sub(r'^\s*#define '+key+r'.*$', '#define '+key+' 1',text,flags=re.M)
    else:text+='\n#define '+key+' 1\n'
f.write_text(text)
(r/'libraries/berry/generate').mkdir(exist_ok=True)
subprocess.run([sys.executable,str(r/'libraries/berry/tools/coc/coc'),'-o',str(r/'libraries/berry/generate'),str(r/'libraries/berry/src'),str(r/'src/berry/modules'),'-c',str(r/'include/berry_conf.h')],check=True)
os.environ.update(APP_VERSION='ws2805-ln882h-test2',OBK_VARIANT='0',CROSS_TOOLCHAIN_ROOT=a.toolchain.resolve().as_posix())
cmake=str(Path(shutil.which(a.cmake)or a.cmake).resolve());ninja=str(Path(shutil.which(a.ninja)or a.ninja).resolve())
build=sdk/'build-ws2805'
subprocess.run([cmake,'-S',str(sdk),'-B',str(build),'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+ninja,'-DCMAKE_POLICY_VERSION_MINIMUM=3.5'],check=True)
subprocess.run([cmake,'--build',str(build),'--parallel','6'],check=True)
print('Images:',build/'bin')
