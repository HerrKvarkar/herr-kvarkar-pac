"""Prepare a separate ISD draft from the preserved V2 meshes; no engine tools required."""
from pathlib import Path
import sys,struct,re,shutil,json
import numpy as np
from scipy.spatial.transform import Rotation
REPO=Path(__file__).resolve().parents[2]
REFERENCE=Path(r'G:\ChatGPT\kvarkar_pac_research\isd_reference')
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
   assert total>0
   text.append('0 '+' '.join(f'{x:.8f}' for x in [*v['p'],*v['n'],*v['uv']])+' '+str(len(links))+' '+' '.join(f'{b} {w/total:.8f}' for b,w in links))
 text.append('end');p.write_text('\n'.join(text)+'\n')

header,costume=read_smd(REPO/'source/v2/kvarkar_costume.smd')
nodes={int(i):(name,int(parent)) for i,name,parent in re.findall(r'^(\d+) "([^"]+)" (-?\d+)$',header,re.M)}
name_ids={name:i for i,(name,parent) in nodes.items()}
source=Path('models/frostbyte/ia/internalsecurity_mike.mdl')
# Use the engine's bind-matrix export and Source SMD triangle winding.
raw=json.loads((OUT/'isd_vest_native.json').read_text())
vest=[]
for i in range(0,len(raw),3):
 vertices=[]
 for item in raw[i:i+3]:
  pos=np.array(item['pos'],dtype=float);normal=np.array(item['normal'],dtype=float)
  pos[0]*=.93;pos[1]=.5+(pos[1]-.5)*.92
  if pos[1]<0:pos[1]-=.9*min(1,-pos[1]/2)
  shoulder=min(1,max(0,(pos[2]-57)/3))*min(1,max(0,(abs(pos[0])-2.5)/1.5))
  pos[0]*=1-.14*shoulder
  if pos[1]<2.5:pos[1]+=.65*shoulder
  pos[2]-=.15*shoulder
  weights={name_ids[link['name']]:link['weight'] for link in item['weights']}
  vertices.append({'p':pos,'n':normal,'uv':np.array(item['uv']),'weights':weights})
 vest.append(('kvarkar_isd_vest.vmt',vertices))
assert vest
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
  collar=min(1,max(0,(v['p'][2]-58)/2))
  v['p'][1]+=.45*collar
  v['p'][0]*=1-.15*collar
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
# Fit the upper straps to the actual coat surface and follow its skin weights.
# This keeps shoulder clearance when the upper arms swing during running.
from scipy.spatial import cKDTree
coat=[tri for mat,tri in costume if mat=='kvarkar_leather_coat_fine.vmt' and max(v['p'][2] for v in tri)>40 and min(v['p'][2] for v in tri)<64]
centers=np.array([np.mean([v['p'] for v in tri],axis=0) for tri in coat])
tree=cKDTree(centers)
def nearest_point(p,tri):
 a,b,c=[v['p'] for v in tri];ab=b-a;ac=c-a;ap=p-a
 aa=np.dot(ab,ab);bb=np.dot(ab,ac);cc=np.dot(ac,ac);den=aa*cc-bb*bb
 options=[]
 if abs(den)>1e-10:
  u=(cc*np.dot(ap,ab)-bb*np.dot(ap,ac))/den;v=(aa*np.dot(ap,ac)-bb*np.dot(ap,ab))/den
  if u>=0 and v>=0 and u+v<=1:options.append((a+u*ab+v*ac,np.array([1-u-v,u,v])))
 for i,j in [(0,1),(1,2),(2,0)]:
  x=tri[i]['p'];d=tri[j]['p']-x;t=min(1,max(0,np.dot(p-x,d)/max(np.dot(d,d),1e-12)))
  weights=np.zeros(3);weights[i]=1-t;weights[j]=t;options.append((x+t*d,weights))
 return min(options,key=lambda item:np.linalg.norm(item[0]-p))
matched_straps=0
for _,tri in vest:
 for vertex in tri:
  pos=vertex['p'];factor=min(1,max(0,(pos[2]-56.5)/3))*min(1,max(0,(abs(pos[0])-2.5)/1.5))
  back=min(1,max(0,(pos[1]-1)/2))*min(1,max(0,(pos[2]-40)/2))
  factor=max(factor,back)
  if factor<=0:continue
  _,ids=tree.query(pos,k=min(24,len(coat)))
  candidates=[]
  for i in np.atleast_1d(ids):
   q,bary=nearest_point(pos,coat[i]);candidates.append((np.linalg.norm(q-pos),int(i),q,bary))
  distance,index,q,bary=min(candidates,key=lambda item:item[0]);surface=coat[index]
  normal=sum((v['n']*w for v,w in zip(surface,bary)),np.zeros(3));normal/=max(np.linalg.norm(normal),1e-10)
  signed=np.dot(pos-q,normal)
  if signed>-.35:vertex['p']=pos-normal*min(1.2,signed+.35)*factor
  weights={bone:weight*(1-factor) for bone,weight in vertex['weights'].items()}
  for v,w in zip(surface,bary):
   for bone,weight in v['weights'].items():weights[bone]=weights.get(bone,0)+weight*w*factor
  weights=dict(sorted(weights.items(),key=lambda x:-x[1])[:3]);total=sum(weights.values())
  vertex['weights']={bone:weight/total for bone,weight in weights.items()}
  matched_straps+=1
write_smd(OUT/'kvarkar_isd_armour.smd',header,vest)
# Department insignia is a conforming shallow relief, independently selectable.
# Copy the coat surface and skin weights so it follows the same animated panel.
emblem=[]
def emblem_triangle(tri):
 span=max(np.linalg.norm(tri[i]['p']-tri[(i+1)%3]['p']) for i in range(3))
 if span>1:
  for child in scope['split_triangle'](tri):emblem_triangle(child)
  return
 vertices=[]
 for v in tri:
  x,y,z=v['p'];n=v['n']/max(np.linalg.norm(v['n']),1e-10)
  vertices.append({**v,'p':v['p']+n*.045,'uv':np.array([(4.5-x)/9,(z-50)/9])})
 emblem.append(('kvarkar_isd_back_emblem.vmt',vertices))
for material,tri in costume:
 if material!='kvarkar_leather_coat_fine.vmt' or min(v['p'][1] for v in tri)<1:continue
 if np.mean([v['n'][1] for v in tri])<.2:continue
 poly=tri
 for axis,bound,direction in [(0,-4.5,1),(0,4.5,-1),(2,50,1),(2,59,-1)]:poly=scope['clip'](poly,axis,bound,direction)
 for clipped in scope['triangulate'](poly):emblem_triangle(clipped)
assert emblem
write_smd(OUT/'kvarkar_isd_back_emblem.smd',header,emblem)
write_smd(OUT/'kvarkar_dea_back_emblem.smd',header,[('kvarkar_dea_back_emblem.vmt',tri) for _,tri in emblem])

costume=[(PROFILE['coat_material'] if mat=='kvarkar_leather_coat_fine.vmt' else mat,tri) for mat,tri in costume]
write_smd(OUT/'kvarkar_isd_costume.smd',header,costume)
for name in ['kvarkar_animated_head.smd','kvarkar_face.vta','kvarkar_merged_idle.smd']:shutil.copy2(REPO/'source/v2'/name,OUT/name)
qc=(REPO/'source/v2/kvarkar_animated.qc').read_text();qc=qc.replace('kvarkar/herr_kvarkar_v2_r7.mdl','kvarkar/herr_kvarkar_isd_draft_r6.mdl').replace('"kvarkar_costume.smd"','"kvarkar_isd_costume.smd"')
# An independent armour bodygroup keeps the shared character usable without armour.
qc=qc.replace('$cdmaterials \"models/kvarkar/v2/\"','$cdmaterials \"models/kvarkar/isd/\"\n$cdmaterials \"models/kvarkar/v2/\"')
qc+='\n$bodygroup "Department armour" {\n blank\n studio "kvarkar_isd_armour.smd"\n}\n'
qc+='\n$bodygroup "Tie" {\n blank\n studio "kvarkar_optional_tie.smd"\n studio "kvarkar_tie_tucked.smd"\n}\n'
qc+='\n$texturegroup "Department colours" {\n { "kvarkar_isd_blue_shirt" "kvarkar_isd_leather_coat" }\n { "kvarkar_dea_shirt" "kvarkar_leather_coat_fine" }\n}\n'
qc+='\n$bodygroup "Department insignia" {\n blank\n studio "kvarkar_isd_back_emblem.smd"\n studio "kvarkar_dea_back_emblem.smd"\n}\n'
(OUT/'kvarkar_isd.qc').write_text(qc)
(OUT/'pac_department_defaults.json').write_text(json.dumps({name:{'name':p['display_name'],'skin':p['skin'],'bodygroups':p['bodygroups'],'accessories':p['accessories']} for name,p in PROFILES['profiles'].items()},indent=2))
from srctools.vtf import VTF,ImageFormats,VTFFlags
master=REPO/PROFILE['coat_accent_master']
if master.exists():
 image=Image.open(master).convert('RGBA').resize((512,512),Image.Resampling.LANCZOS)
 texture=VTF(512,512,version=(7,2),fmt=ImageFormats.DXT5,flags=VTFFlags.ANISOTROPIC)
 texture.get().copy_from(image.tobytes())
 with (OUT/'materials/coat_isd_blue_accents.vtf').open('wb') as stream:texture.save(stream)
a=np.array([v['p'] for m,t in vest for v in t]);summary={'state':'source draft only; not compiled or worn','armour_triangles':len(vest),'bounds':[a.min(0).tolist(),a.max(0).tolist()],'coatMatchedArmourVertices':matched_straps,'emblemTriangles':len(emblem),'independentArmourBodygroup':True,'source':str(source),'coatFitTested':False}
(OUT/'draft-status.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))

