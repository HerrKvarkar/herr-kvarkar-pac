"""Package the shared character preview with department skins and optional equipment."""
from pathlib import Path
import zipfile,re,shutil,struct,json
from srctools.vtf import VTF,ImageFormats
from PIL import Image
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent
GAME=Path(r'G:\SteamLibrary\steamapps\common\GarrysMod\garrysmod')
STAGE=ROOT/'package';STAGE.mkdir(exist_ok=True)
with zipfile.ZipFile(REPO/'assets/herr_kvarkar_character_v2_preview_r7_waistfix.zip') as z:
 for n in z.namelist():
  if n.startswith('materials/'):
   p=STAGE/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
CM=STAGE/'materials/models/kvarkar/combat_medic';CM.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'donor/materials.json').read_text(encoding='utf-8'))
diffuse={record['textures']['$basetexture']['file'] for record in manifest.values() if '$basetexture' in record['textures']}
diffuse.add('cm_blue_gloves.vtf')
for p in (ROOT/'materials').iterdir():
 if p.suffix=='.vmt':shutil.copy2(p,CM/p.name)
 elif p.suffix=='.vtf':
  with p.open('rb') as f:source=VTF.read(f);image=source.get().to_PIL().convert('RGBA')
  if p.stat().st_size<32768:
   shutil.copy2(p,CM/p.name);continue
  limit=1024 if p.name=='cm_106vest.vtf' else (256 if p.name in ['cm_rac_headset_nml.vtf','cm_headgear_c_nml.vtf','cm_helmet_rails_mask.vtf'] else 512)
  image.thumbnail((limit,limit),Image.Resampling.LANCZOS)
  texture=VTF(*image.size,version=(7,2),fmt=ImageFormats.DXT1 if p.name in diffuse or "mask" in p.name else ImageFormats.DXT5,flags=source.flags)
  texture.get().copy_from(image.tobytes())
  with (CM/p.name).open('wb') as f:texture.save(f)
# Preserve hair colour/alpha and the full face; resize only its hidden fine normal detail.
p=STAGE/'materials/models/kvarkar/v2/hairshort01_n.vtf'
with p.open('rb') as f:source=VTF.read(f);image=source.get().to_PIL().convert('RGBA').resize((512,512),Image.Resampling.LANCZOS)
texture=VTF(512,512,version=(7,2),fmt=ImageFormats.DXT5,flags=source.flags)
texture.get().copy_from(image.tobytes())
with p.open('wb') as f:texture.save(f)
mdl=GAME/'models/kvarkar/herr_kvarkar_combat_medic_r2.mdl';d=mdl.read_bytes()
def cs(o):return d[o:d.index(0,o)].decode()
nt,ot=struct.unpack_from('<ii',d,204);names=[cs(ot+i*64+struct.unpack_from('<i',d,ot+i*64)[0]) for i in range(nt)]
files=set()
for name in names:
 mat=next((directory/(name+'.vmt') for directory in [CM,STAGE/'materials/models/kvarkar/v2'] if (directory/(name+'.vmt')).exists()),None)
 assert mat is not None,name
 files.add(mat)
 for texture in re.findall(r'"?\$(?:basetexture|bumpmap|iris|corneatexture|selfillummask|ambientoccltexture|phongexponenttexture|lightwarptexture|envmapmask|detail)"?\s*"([^"]+)"',mat.read_text(),re.I):
  texture=STAGE/'materials'/(texture.replace('\\','/')+'.vtf')
  assert texture.exists(),texture
  files.add(texture)
for source in mdl.parent.glob(mdl.stem+'.*'):
 dest=STAGE/'models/kvarkar'/source.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);files.add(dest)
output=REPO/'assets/herr_kvarkar_combat_medic_r2.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_STORED) as z:
 for p in sorted(files):z.write(p,p.relative_to(STAGE).as_posix())
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 assert len([n for n in z.namelist() if n.endswith('.mdl')])==1
assert output.stat().st_size<15360*1024,'Exceeds PAC server limit'
print(output.name,output.stat().st_size,'bytes',nt,'materials')

# Install only this preset's new native materials for isolated offscreen inspection.
for p in CM.iterdir():
 target=GAME/'materials/models/kvarkar/combat_medic'/p.name
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
