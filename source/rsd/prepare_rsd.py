"""Build the white researcher preset from the preserved shared fitted character geometry."""
from pathlib import Path
import sys,json,shutil
import numpy as np
from PIL import Image
REPO=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PROFILE=json.loads((REPO/'department_profiles.json').read_text(encoding='utf-8'))['profiles']['rsd']
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
# Reuse shared coat shaping, knee clearance, collar, round buttons and tail weighting.
shared_builder=REPO/'source/v2/build_v2.py'
prefix=shared_builder.read_text(encoding='utf-8').split('# A true shallow relief of the supplied DEA emblem',1)[0]
scope={'__file__':str(shared_builder),'__name__':'kvarkar_shared_geometry'}
exec(compile(prefix,str(shared_builder),'exec'),scope)
costume=[(mat,tri) for mat,tri in costume if mat not in ('kvarkar_dea_emboss.vmt','kvarkar_leather_coat_fine.vmt')]
costume += [('kvarkar_leather_coat_fine.vmt',tri) for mat,tri in scope['triangles'] if mat=='kvarkar_field_coat.vmt']
# Blend the skirt into the upper thighs while retaining damped independent tails.
# This lets the lab coat open with a stride instead of passing through raised knees.
for mat,tri in costume:
 if mat=='kvarkar_leather_coat_fine.vmt':
  for v in tri:
   x,y,z=v['p']
   if z>=42:continue
   amount=min(1.,max(0.,(42-z)/12.))
   amount=amount*amount*(3.-2.*amount)*(.85 if y<.8 else .75)
   side='L' if x>0 else 'R'
   thigh=next(b for b,(name,parent) in scope['nodes'].items() if name=='ValveBiped.Bip01_'+side+'_Thigh')
   weights={b:w*(1.-amount) for b,w in v['weights'].items()}
   weights[thigh]=weights.get(thigh,0.)+amount
   v['weights']=weights
# White cloth exposes small thigh intersections hidden by the old black leather.
# Add a smooth lower-coat ease allowance without changing boots or tail skinning.
for mat,tri in costume:
 if mat=='kvarkar_leather_coat_fine.vmt':
  for v in tri:
   x,y,z=v['p'];ease=max(0.,1.-abs(z-31.)/14.)
   ease*=1.-min(1.,sum(weight for bone,weight in v['weights'].items() if bone in scope['arm_bones']))
   v['p'][0]=x*(1.+.03*ease)
   v['p'][1]=.8+(y-.8)*(1.+.07*ease)
tie=[(mat,tri) for mat,tri in costume if mat=='kvarkar_black_tie.vmt']
# Use the existing atlas's grey woven tie rather than its almost-black first strip.
for _,tri in tie:
 for v in tri:
  v['uv'][0]=.9165+v['uv'][0]*1.04
  collar=min(1.,max(0.,(v['p'][2]-58.3)/2.))
  center=max(0.,1.-abs(v['p'][0])/1.)
  v['p'][1]+=(.65-.6*center)*collar
  v['p'][0]*=1.-.16*collar
  v['p'][2]-=.12*collar
tie=[('kvarkar_rsd_charcoal_tie.vmt',tri) for _,tri in tie]
write_smd(OUT/'kvarkar_optional_tie.smd',header,tie)
# Original researcher pager, fitted to the shared belt and weighted to the pelvis.
pager=[]
raw=json.loads((OUT/'pager_native.json').read_text(encoding='utf-8'))
names={name:bone for bone,(name,parent) in scope['nodes'].items()}
for i in range(0,len(raw),3):
 vertices=[]
 for item in raw[i:i+3]:
  pos=np.array(item['pos'],dtype=float)+np.array([.4,-.15,-2.])
  vertices.append({'p':pos,'n':np.array(item['normal']),'uv':np.array(item['uv']),'weights':{names['ValveBiped.Bip01_Pelvis']:1.}})
 pager.append(('kvarkar_rsd_pager_'+raw[i]['material'].split('/')[-1]+'.vmt',vertices))
write_smd(OUT/'kvarkar_rsd_pager.smd',header,pager)
costume=[(PROFILE['shirt_material'] if mat=='kvarkar_dea_shirt.vmt' else mat,tri) for mat,tri in costume if mat!='kvarkar_black_tie.vmt']
panel=[];remaining=[]
rect=[(0,-4.5,1),(0,4.5,-1),(2,50,1),(2,59,-1)]
for material,tri in costume:
 if material!='kvarkar_leather_coat_fine.vmt' or min(v['p'][1] for v in tri)<1 or np.mean([v['n'][1] for v in tri])<.2:
  remaining.append((material,tri));continue
 poly=tri
 for axis,bound,direction in rect:
  outside=scope['clip'](poly,axis,bound,-direction)
  remaining.extend((material,t) for t in scope['triangulate'](outside))
  poly=scope['clip'](poly,axis,bound,direction)
  if not poly:break
 panel.extend(scope['triangulate'](poly))
assert panel
costume=remaining
write_smd(OUT/'kvarkar_plain_back_panel.smd',header,[(PROFILE['coat_material'],tri) for tri in panel])

def emboss_panel(master,material):
 alpha=np.asarray(Image.open(REPO/'assets'/master).getchannel('A'),dtype=float)/255
 result=[]
 def sample(p):
  u=(4.5-p[0])/9;v=(59-p[2])/9
  if not(0<=u<=1 and 0<=v<=1):return 0.
  x=u*(alpha.shape[1]-1);y=v*(alpha.shape[0]-1);ix=int(x);iy=int(y);fx=x-ix;fy=y-iy
  jx=min(ix+1,alpha.shape[1]-1);jy=min(iy+1,alpha.shape[0]-1)
  return alpha[iy,ix]*(1-fx)*(1-fy)+alpha[iy,jx]*fx*(1-fy)+alpha[jy,ix]*(1-fx)*fy+alpha[jy,jx]*fx*fy
 def stamp(tri,depth=0):
  ps=np.array([v['p'] for v in tri]);lo=ps.min(0);hi=ps.max(0)
  x0=max(0,int((4.5-hi[0])/9*(alpha.shape[1]-1)));x1=min(alpha.shape[1]-1,int((4.5-lo[0])/9*(alpha.shape[1]-1))+1)
  y0=max(0,int((59-hi[2])/9*(alpha.shape[0]-1)));y1=min(alpha.shape[0]-1,int((59-lo[2])/9*(alpha.shape[0]-1))+1)
  region=alpha[y0:y1+1,x0:x1+1]
  mixed=region.size and region.max()>.01 and region.min()<.999
  if mixed and max(hi[0]-lo[0],hi[2]-lo[2])>.17 and depth<10:
   for child in scope['split_triangle'](tri):stamp(child,depth+1)
   return
  out=[]
  for vertex in tri:
   p=vertex['p'];h=.03;level=sample(p)
   dx=(sample(p+np.array([h,0,0]))-sample(p-np.array([h,0,0])))/(2*h)
   dz=(sample(p+np.array([0,0,h]))-sample(p-np.array([0,0,h])))/(2*h)
   n=vertex['n'].copy();n[0]-=.025*dx*n[1];n[2]-=.025*dz*n[1];n/=max(np.linalg.norm(n),1e-9)
   out.append({**vertex,'p':p+np.array([0,.025*level,0]),'n':n})
  mat=material if sample(ps.mean(0))>.35 else PROFILE['coat_material']
  result.append((mat,out))
 for tri in panel:stamp(tri)
 return result

emblem=emboss_panel('rsd_logo_reference.png','kvarkar_rsd_emboss.vmt')
write_smd(OUT/'kvarkar_rsd_emblem.smd',header,emblem)
costume=[(PROFILE['coat_material'] if mat=='kvarkar_leather_coat_fine.vmt' else mat,tri) for mat,tri in costume]
write_smd(OUT/'kvarkar_rsd_costume.smd',header,costume)
for name in ['kvarkar_animated_head.smd','kvarkar_face.vta','kvarkar_merged_idle.smd']:shutil.copy2(REPO/'source/v2'/name,OUT/name)
qc=(REPO/'source/v2/kvarkar_animated.qc').read_text(encoding='utf-8')
qc=qc.replace('kvarkar/herr_kvarkar_v2_r7.mdl','kvarkar/herr_kvarkar_rsd_preview_r6.mdl').replace('"kvarkar_costume.smd"','"kvarkar_rsd_costume.smd"')
qc=qc.replace('$cdmaterials "models/kvarkar/v2/"','$cdmaterials "models/kvarkar/rsd/"\n$cdmaterials "models/kvarkar/v2/"')
qc+='\n$bodygroup "Tie" {\n blank\n studio "kvarkar_optional_tie.smd"\n}\n'
qc+='\n$bodygroup "Department insignia" {\n studio "kvarkar_plain_back_panel.smd"\n studio "kvarkar_rsd_emblem.smd"\n}\n'
qc+='\n$bodygroup "Pager" {\n blank\n studio "kvarkar_rsd_pager.smd"\n}\n'
(OUT/'kvarkar_rsd.qc').write_text('\n'.join(line.rstrip() for line in qc.splitlines())+'\n',encoding='utf-8')
print(json.dumps({'costumeTriangles':len(costume),'emblemTriangles':len(emblem),'armour':False,'state':'not worn'}))
