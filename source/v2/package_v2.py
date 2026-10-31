"""Package the approved local geometry as a portable PAC model preview."""
from pathlib import Path
import argparse
import re
import shutil
import zipfile
from PIL import Image
from srctools.vtf import VTF, ImageFormats, VTFFlags

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
parser=argparse.ArgumentParser()
parser.add_argument('--game',type=Path,required=True)
parser.add_argument('--revision',type=int,required=True)
args=parser.parse_args()
stage=ROOT/'package'
materials=stage/'materials/models/kvarkar/v2'
models=stage/'models/kvarkar'
materials.mkdir(parents=True,exist_ok=True)
models.mkdir(parents=True,exist_ok=True)

with zipfile.ZipFile(REPO/'assets/herr_kvarkar_character_v4.zip') as archive:
    for entry in archive.namelist():
        if not entry.startswith('materials/models/kvarkar/final_v1/'):
            continue
        data=archive.read(entry)
        if entry.endswith('.vmt'):
            data=data.decode().replace('models/kvarkar/final_v1/','models/kvarkar/v2/').encode()
        (materials/Path(entry).name).write_bytes(data)
for name in ['boots_diffuse.vtf','boots_normal.vtf','kvarkar_leather_coat_fine.vmt',
             'kvarkar_leather_gloves.vmt','kvarkar_field_trousers_clean.vmt','kvarkar_field_pocket.vmt',
             'kvarkar_dea_emboss.vmt','kvarkar_field_boots.vmt']:
    shutil.copy2(ROOT/name,materials/name)
for master,texture,size in [
    ('kvarkar_leather_coat_v2_fine.png','coat_leather_fine_diffuse.vtf',(512,512)),
    ('kvarkar_leather_gloves_v2.png','gloves_leather_diffuse.vtf',(1024,512)),
    ('kvarkar_field_trousers_v2_clean.png','field_trousers_clean_diffuse.vtf',(1024,512))]:
    image=Image.open(REPO/'assets'/master).convert('RGBA').resize(size,Image.Resampling.LANCZOS)
    texture_data=VTF(*size,version=(7,2),fmt=ImageFormats.DXT5,flags=VTFFlags.ANISOTROPIC)
    texture_data.get().copy_from(image.tobytes())
    with (materials/texture).open('wb') as stream:
        texture_data.save(stream)

# Preserve the shirt's full resolution while avoiding its uncompressed RGBA payload.
shirt_path=materials/'dea_red.vtf'
with shirt_path.open('rb') as stream:
    shirt=VTF.read(stream)
    shirt_pixels=shirt.get().to_PIL().convert('RGBA').tobytes()
compressed=VTF(shirt.width,shirt.height,version=(7,2),fmt=ImageFormats.DXT5,flags=shirt.flags)
compressed.get().copy_from(shirt_pixels)
with shirt_path.open('wb') as stream:
    compressed.save(stream)

names=['kvarkar_face','kvarkar_mouth','kvarkar_eye_l','kvarkar_eye_r','kvarkar_dea_trousers',
       'kvarkar_dea_shirt','kvarkar_leather_gloves','kvarkar_black_tie','kvarkar_leather_coat_fine',
       'kvarkar_hair','kvarkar_field_boots','kvarkar_field_trousers_clean','kvarkar_field_pocket','kvarkar_dea_emboss']
files=[]
for name in names:
    material=materials/(name+'.vmt')
    files.append(material)
    for reference in re.findall(r'"(?:\$basetexture|\$bumpmap|\$iris|\$corneatexture|\$ambientoccltexture|\$phongexponenttexture|\$detail)"\s*"([^"]+)"',material.read_text(),re.I):
        texture=materials/(reference.replace('\\','/').split('/')[-1]+'.vtf')
        assert texture.is_file(),f'Missing texture: {reference}'
        files.append(texture)
for source in (args.game/'models/kvarkar').glob(f'herr_kvarkar_v2_r{args.revision}.*'):
    dest=models/source.name
    shutil.copy2(source,dest)
    files.append(dest)
assert any(p.suffix=='.mdl' for p in files)
output=REPO/'assets'/f'herr_kvarkar_character_v2_preview_r{args.revision}_compact.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_STORED) as archive:
    for path in sorted(set(files)):
        archive.write(path,path.relative_to(stage).as_posix())
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert len([n for n in archive.namelist() if n.endswith('.mdl')])==1
assert output.stat().st_size<15360*1024,'Model pack exceeds the verified server PAC download limit'
print(f'{output.name}: {output.stat().st_size:,} bytes, one MDL, all texture dependencies checked')
