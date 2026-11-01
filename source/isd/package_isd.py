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
ISD=STAGE/'materials/models/kvarkar/isd';ISD.mkdir(parents=True,exist_ok=True)
for p in (ROOT/'materials').iterdir():
 if p.suffix in ('.vmt','.vtf'):shutil.copy2(p,ISD/p.name)
# Retain source resolution, compress the blue diffuse to fit PAC's server budget.
for filename in ['suit_shirtx.vtf','kevlar_vest2.vtf']:
 p=ISD/filename
 with p.open('rb') as f:
  source=VTF.read(f);pixels=source.get().to_PIL().convert('RGBA').resize((1024,512),Image.Resampling.LANCZOS).tobytes()
 texture=VTF(1024,512,version=(7,2),fmt=ImageFormats.DXT1 if filename=="suit_shirtx.vtf" else ImageFormats.DXT5,flags=source.flags)
 texture.get().copy_from(pixels)
 with p.open('wb') as f:texture.save(f)
# One shared normal map avoids ambiguous duplicate names in PAC's flattened cache.
p=ISD/'kvarkar_isd_blue_shirt.vmt';s=p.read_text().replace('models/kvarkar/isd/suit_shirt_n','models/kvarkar/v2/suit_shirt_n');p.write_text(s)
mdl=GAME/'models/kvarkar/herr_kvarkar_isd_draft_r7.mdl';d=mdl.read_bytes()
def cs(o):return d[o:d.index(0,o)].decode()
nt,ot=struct.unpack_from('<ii',d,204);names=[cs(ot+i*64+struct.unpack_from('<i',d,ot+i*64)[0]) for i in range(nt)]
files=set()
for name in names:
 mat=next((directory/(name+'.vmt') for directory in [ISD,STAGE/'materials/models/kvarkar/v2'] if (directory/(name+'.vmt')).exists()),None)
 assert mat is not None,name
 files.add(mat)
 for texture in re.findall(r'"?\$(?:basetexture|bumpmap|iris|corneatexture|ambientoccltexture|phongexponenttexture|detail)"?\s*"([^"]+)"',mat.read_text(),re.I):
  texture=STAGE/'materials'/(texture.replace('\\','/')+'.vtf')
  assert texture.exists(),texture
  files.add(texture)
for source in mdl.parent.glob(mdl.stem+'.*'):
 dest=STAGE/'models/kvarkar'/source.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);files.add(dest)
output=REPO/'assets/herr_kvarkar_department_r7.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_STORED) as z:
 for p in sorted(files):z.write(p,p.relative_to(STAGE).as_posix())
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 assert len([n for n in z.namelist() if n.endswith('.mdl')])==1
assert output.stat().st_size<15360*1024,'Exceeds PAC server limit'
print(output.name,output.stat().st_size,'bytes',nt,'materials')
