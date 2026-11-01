"""Prepare a separate ISD draft from the preserved V2 meshes; no engine tools required."""
from pathlib import Path
import sys,struct,re,shutil,json
import numpy as np
from scipy.spatial.transform import Rotation
REPO=Path(__file__).resolve().parents[2]
REFERENCE=Path(r'G:\ChatGPT\kvarkar_pac_research\isd_reference')
sys.path.insert(0,str(REFERENCE.parent))
from render_isd_reference import load
OUT=Path(__file__).resolve().parent
PROFILES=json.loads((REPO/'department_profiles.json').read_text(encoding='utf-8-sig'))
PROFILE=PROFILES['profiles']['isd']

def read_smd(p):
 header,body=p.read_text().split('triangles\n',1);lines=body.splitlines();triangles=[]
 for i in range(0,len(lines)-3,4):
  vertices=[]
  for l in lines[i+1:i+4]:
   a=list(map(float,l.split()));vertices.append({'p':np.array(a[1:4]),'n':np.array(a[4:7]),'uv':np.array(a[7:9]),'weights':{int(a[10+j*2]):a[11+j*2] for j in range(int(a[9]))}})
  triangles.append((lines[i],vertices))
 return header,triangles

def write_smd(p,header,triangles):
 text=[header.rstrip(),'triangles']
 for mat,tri in triangles:
  text.append(mat)
  for v in tri:
   links=sorted(v['weights'].items(),key=lambda x:-x[1])[:3];total=sum(w for _,w in links)
   assert total>.99
   text.append('0 '+' '.join(f'{x:.8f}' for x in [*v['p'],*v['n'],*v['uv']])+' '+str(len(links))+' '+' '.join(f'{b} {w/total:.8f}' for b,w in links))
 text.append('end');p.write_text('\n'.join(text)+'\n')

header,costume=read_smd(REPO/'source/v2/kvarkar_costume.smd')
nodes={int(i):(name,int(parent)) for i,name,parent in re.findall(r'^(\d+) "([^"]+)" (-?\d+)$',header,re.M)}
world={};name_ids={name:i for i,(name,parent) in nodes.items()}
for line in header.split('time 0\n',1)[1].splitlines():
 a=line.split()
 if len(a)!=7:continue
 i=int(a[0]);local=np.eye(4);local[:3,:3]=Rotation.from_euler('xyz',list(map(float,a[4:7]))).as_matrix();local[:3,3]=list(map(float,a[1:4]));parent=nodes[i][1];world[i]=world[parent]@local if parent>=0 else local
source=REFERENCE/'models/frostbyte/ia/internalsecurity_mike.mdl';mdl=source.read_bytes();nb,bo=struct.unpack_from('<ii',mdl,156);source_bones={}
for i in range(nb):
 o=bo+i*216;ni=struct.unpack_from('<i',mdl,o)[0];name=mdl[o+ni:mdl.index(0,o+ni)].decode();pose=np.eye(4);pose[:3,:]=np.array(struct.unpack_from('<12f',mdl,o+96)).reshape(3,4)
 source_bones[i]=(name,pose)
# Use the engine's bind-matrix export and Source SMD triangle winding.
raw=json.loads((OUT/'isd_vest_native.json').read_text())
vest=[]
for i in range(0,len(raw),3):
 vertices=[]
 for item in raw[i:i+3]:
  pos=np.array(item['pos'],dtype=float);normal=np.array(item['normal'],dtype=float)
  pos[0]*=.93;pos[1]=.5+(pos[1]-.5)*.92
  if pos[1]<0:pos[1]-=.9*min(1,-pos[1]/2)
  weights={name_ids[link['name']]:link['weight'] for link in item['weights']}
  vertices.append({'p':pos,'n':normal,'uv':np.array(item['uv']),'weights':weights})
 vest.append(('kvarkar_isd_vest.vmt',vertices))
assert vest
write_smd(OUT/'kvarkar_isd_armour.smd',header,vest)
# Reuse the shared fitted coat before the department-specific DEA stamp is added.
shared_builder=REPO/'source/v2/build_v2.py'
prefix=shared_builder.read_text().split('# A true shallow relief of the supplied DEA emblem',1)[0]
scope={'__file__':str(shared_builder),'__name__':'kvarkar_shared_geometry'}
exec(compile(prefix,str(shared_builder),'exec'),scope)
costume=[(mat,tri) for mat,tri in costume if mat not in ('kvarkar_dea_emboss.vmt','kvarkar_leather_coat_fine.vmt')]
costume += [('kvarkar_leather_coat_fine.vmt',tri) for mat,tri in scope['triangles'] if mat=='kvarkar_field_coat.vmt']
from PIL import Image
for i,(mat,tri) in enumerate(costume):
 if mat=='kvarkar_dea_emboss.vmt':costume[i]=('kvarkar_leather_coat_fine.vmt',tri)
 elif mat=='kvarkar_dea_shirt.vmt':costume[i]=(PROFILE['shirt_material'],tri)
# ISD uses an open blue collar with no tie geometry.
tie=[(material,tri) for material,tri in costume if material=='kvarkar_black_tie.vmt']
write_smd(OUT/'kvarkar_optional_tie.smd',header,tie)
tucked=[]
for mat,tri in tie:
 vertices=[]
 for vertex in tri:
  v={**vertex,'p':vertex['p'].copy(),'n':vertex['n'].copy(),'uv':vertex['uv'].copy(),'weights':vertex['weights'].copy()}
  v['p'][1]+=1.2*min(1,max(0,(59-v['p'][2])/2))
  vertices.append(v)
 tucked.append((mat,vertices))
write_smd(OUT/'kvarkar_tie_tucked.smd',header,tucked)
costume=[(material,tri) for material,tri in costume if material!='kvarkar_black_tie.vmt']
# Open the leather front around the vest; keep the existing hem and leg clearance.
for material,tri in costume:
 if material=='kvarkar_leather_coat_fine.vmt':
  for v in tri:
   x,y,z=v['p'];front=min(1,max(0,(-y-2)/2));height=min(1,max(0,(z-40)/5))*min(1,max(0,(64-z)/3));center=min(1,max(0,(10-abs(x))/3));factor=front*height*center
   v['p'][0]+=(.85 if x>0 else -.85)*factor
   v['p'][1]-=.7*factor
costume=[(PROFILE['coat_material'] if mat=='kvarkar_leather_coat_fine.vmt' else mat,tri) for mat,tri in costume]
write_smd(OUT/'kvarkar_isd_costume.smd',header,costume)
for name in ['kvarkar_animated_head.smd','kvarkar_face.vta','kvarkar_merged_idle.smd']:shutil.copy2(REPO/'source/v2'/name,OUT/name)
qc=(REPO/'source/v2/kvarkar_animated.qc').read_text();qc=qc.replace('kvarkar/herr_kvarkar_v2_r7.mdl','kvarkar/herr_kvarkar_isd_draft_r3.mdl').replace('"kvarkar_costume.smd"','"kvarkar_isd_costume.smd"')
# An independent armour bodygroup keeps the shared character usable without armour.
qc=qc.replace('$cdmaterials \"models/kvarkar/v2/\"','$cdmaterials \"models/kvarkar/isd/\"\n$cdmaterials \"models/kvarkar/v2/\"')
qc+='\n$bodygroup "Department armour" {\n blank\n studio "kvarkar_isd_armour.smd"\n}\n'
qc+='\n$bodygroup "Tie" {\n blank\n studio "kvarkar_optional_tie.smd"\n studio "kvarkar_tie_tucked.smd"\n}\n'
qc+='\n$texturegroup "Department colours" {\n { "kvarkar_isd_blue_shirt" "kvarkar_isd_leather_coat" }\n { "kvarkar_dea_shirt" "kvarkar_leather_coat_fine" }\n}\n'
(OUT/'kvarkar_isd.qc').write_text(qc)
(OUT/'pac_department_defaults.json').write_text(json.dumps({name:{'name':p['display_name'],'skin':p['skin'],'bodygroups':p['bodygroups'],'accessories':p['accessories']} for name,p in PROFILES['profiles'].items()},indent=2))
from srctools.vtf import VTF,ImageFormats,VTFFlags
master=REPO/PROFILE['coat_accent_master']
if master.exists():
 image=Image.open(master).convert('RGBA').resize((512,512),Image.Resampling.LANCZOS)
 texture=VTF(512,512,version=(7,2),fmt=ImageFormats.DXT5,flags=VTFFlags.ANISOTROPIC)
 texture.get().copy_from(image.tobytes())
 with (OUT/'materials/coat_isd_blue_accents.vtf').open('wb') as stream:texture.save(stream)
a=np.array([v['p'] for m,t in vest for v in t]);summary={'state':'source draft only; not compiled or worn','armour_triangles':len(vest),'bounds':[a.min(0).tolist(),a.max(0).tolist()],'independentArmourBodygroup':True,'source':str(source),'coatFitTested':False}
(OUT/'draft-status.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))

