"""Package the shared character preview with department skins and optional equipment."""
from pathlib import Path
import zipfile,re,shutil,struct
from srctools.vtf import VTF,ImageFormats
from PIL import Image
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent
GAME=Path(r'G:\SteamLibrary\steamapps\common\GarrysMod\garrysmod')
STAGE=ROOT/'package';STAGE.mkdir(exist_ok=True)
with zipfile.ZipFile(REPO/'assets/herr_kvarkar_character_v2_preview_r7_waistfix.zip') as z:
 for n in z.namelist():
  if n.startswith('materials/'):
   p=STAGE/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
RSD=STAGE/'materials/models/kvarkar/rsd';RSD.mkdir(parents=True,exist_ok=True)
for p in (ROOT/'materials').iterdir():
 if p.suffix=='.vmt':shutil.copy2(p,RSD/p.name)
 elif p.suffix=='.vtf':
  with p.open('rb') as f:source=VTF.read(f);image=source.get().to_PIL().convert('RGBA')
  image.thumbnail((256,256),Image.Resampling.LANCZOS)
  texture=VTF(*image.size,version=(7,2),fmt=ImageFormats.DXT5)
  texture.get().copy_from(image.tobytes())
  with (RSD/p.name).open('wb') as f:texture.save(f)
for master,name,size in [('kvarkar_rsd_white_coat.png','white_labcoat',(1024,1024)),('kvarkar_rsd_white_shirt.png','white_shirt',(1024,512))]:
 image=Image.open(REPO/'assets'/master).convert('RGBA').resize(size,Image.Resampling.LANCZOS)
 texture=VTF(*size,version=(7,2),fmt=ImageFormats.DXT1)
 texture.get().copy_from(image.tobytes())
 with (RSD/(name+'.vtf')).open('wb') as f:texture.save(f)
mdl=GAME/'models/kvarkar/herr_kvarkar_rsd_preview_r6.mdl';d=mdl.read_bytes()
def cs(o):return d[o:d.index(0,o)].decode()
nt,ot=struct.unpack_from('<ii',d,204);names=[cs(ot+i*64+struct.unpack_from('<i',d,ot+i*64)[0]) for i in range(nt)]
files=set()
for name in names:
 mat=next((directory/(name+'.vmt') for directory in [RSD,STAGE/'materials/models/kvarkar/v2'] if (directory/(name+'.vmt')).exists()),None)
 assert mat is not None,name
 files.add(mat)
 for texture in re.findall(r'"?\$(?:basetexture|bumpmap|iris|corneatexture|selfillummask|ambientoccltexture|phongexponenttexture|detail)"?\s*"([^"]+)"',mat.read_text(),re.I):
  texture=STAGE/'materials'/(texture.replace('\\','/')+'.vtf')
  assert texture.exists(),texture
  files.add(texture)
for source in mdl.parent.glob(mdl.stem+'.*'):
 dest=STAGE/'models/kvarkar'/source.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);files.add(dest)
output=REPO/'assets/herr_kvarkar_rsd_preview_r6.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_STORED) as z:
 for p in sorted(files):z.write(p,p.relative_to(STAGE).as_posix())
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 assert len([n for n in z.namelist() if n.endswith('.mdl')])==1
assert output.stat().st_size<15360*1024,'Exceeds PAC server limit'
print(output.name,output.stat().st_size,'bytes',nt,'materials')

# Install only this preset's new native materials for isolated offscreen inspection.
for p in RSD.iterdir():
 target=GAME/'materials/models/kvarkar/rsd'/p.name
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
