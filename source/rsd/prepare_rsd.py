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
# Keep the shared DEA/ISD lower-coat geometry and damped tail weights unchanged.
# Department variants must not add thigh pinning or inflate the skirt.
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
# The donor's Researcher ID clips onto the left chest; its lanyard is separate.
# Fit the card to the outer coat rather than leave it inside the donor's shirt.
badge=[];lanyard=[]
coat=[tri for mat,tri in costume if mat=='kvarkar_leather_coat_fine.vmt']
coat_points=np.array([[v['p'] for v in tri] for tri in coat])
aa=coat_points[:,0];bb=coat_points[:,1];cc=coat_points[:,2]
ab=bb[:,[0,2]]-aa[:,[0,2]];ac=cc[:,[0,2]]-aa[:,[0,2]]
det=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0];safe=np.where(abs(det)>1e-9,det,1.)
def coat_front_y(x,z):
 q=np.array([x,z])-aa[:,[0,2]]
 u=(q[:,0]*ac[:,1]-q[:,1]*ac[:,0])/safe;w=(ab[:,0]*q[:,1]-ab[:,1]*q[:,0])/safe
 valid=(abs(det)>1e-9)&(u>=-.001)&(w>=-.001)&(u+w<=1.001)
 ids=np.flatnonzero(valid)
 if not len(ids):return None
 ys=(1.-u-w)*aa[:,1]+u*bb[:,1]+w*cc[:,1]
 index=min(ids,key=lambda i:ys[i]);bary=[1.-u[index]-w[index],u[index],w[index]]
 weights={};normal=np.zeros(3)
 for v,factor in zip(coat[index],bary):
  normal+=v['n']*factor
  for bone,weight in v['weights'].items():weights[bone]=weights.get(bone,0.)+weight*max(0.,factor)
 normal/=max(np.linalg.norm(normal),1e-9)
 return ys[index],weights,normal
raw=json.loads((OUT/'badge_native.json').read_text(encoding='utf-8'))
card=[item for item in raw if item['material'].endswith('/badge_researcher')]
points=np.array([item['pos'] for item in card]);old_center=(points.min(0)+points.max(0))/2.
_,_,axes=np.linalg.svd(points-points.mean(0))
old_n=axes[-1]
if old_n[1]>0:old_n=-old_n
def basis(normal):
 right=np.cross(np.array([0.,0.,1.]),normal);right/=np.linalg.norm(right)
 up=np.cross(normal,right);up/=np.linalg.norm(up)
 return np.column_stack([right,up,normal])
# Anchor the original clip's rear jaw to the coat. Tilt the rigid card from
# that mounting point until the breast panel clears its underside.
center_x=6.4;center_z=54.
clip_raw=np.array([item['pos'] for item in raw if item['material'].endswith('/clip')])
card_samples=[]
for i in range(0,len(card),3):
 a,b,c=[np.array(item['pos']) for item in card[i:i+3]]
 for j in range(5):
  for k in range(5-j):card_samples.append(a*(1.-(j+k)/4.)+b*j/4.+c*k/4.)
card_samples=np.array(card_samples)
fit=None
for slope in np.linspace(.05,1.75,69):
 new_n=np.array([.15,-1.,slope]);new_n/=np.linalg.norm(new_n)
 rotation=basis(new_n)@basis(old_n).T
 new_center=np.array([center_x,0.,center_z])
 clips=(rotation@(clip_raw-old_center).T).T+new_center
 rear=clips[np.argmax(clips[:,1])]
 mount=coat_front_y(rear[0],rear[2])
 if mount is None:continue
 new_center[1]=mount[0]+.02-rear[1]
 samples=(rotation@(card_samples-old_center).T).T+new_center
 gaps=[]
 for pos in samples:
  hit=coat_front_y(pos[0],pos[2])
  if hit is not None:gaps.append(hit[0]-pos[1])
 if gaps and min(gaps)>=.025:
  fit=(rotation,new_center,mount[1],float(slope),min(gaps));break
assert fit is not None,'No rigid badge fit clears the coat while keeping the clip attached'
rotation,new_center,mount_weights,badge_slope,badge_clearance=fit
print(json.dumps({'badgeSlope':badge_slope,'minimumCardClearance':badge_clearance,'clipRearEmbedded':.02}))
for i in range(0,len(raw),3):
 kind=raw[i]['material'].split('/')[-1];vertices=[]
 for item in raw[i:i+3]:
  pos=np.array(item['pos'],dtype=float);normal=np.array(item['normal'])
  if kind!='lanyard':
   pos=rotation@(pos-old_center)+new_center
   normal=rotation@normal
   weights=mount_weights.copy()
  else:
   pos[1]-=.35*min(1.,max(0.,(-pos[1]-1.)/2.))
   weights={names[link['name']]:link['weight'] for link in item['weights']}
  vertices.append({'p':pos,'n':normal,'uv':np.array(item['uv']),'weights':weights})
 (lanyard if kind=='lanyard' else badge).append(('kvarkar_rsd_id_'+kind+'.vmt',vertices))
write_smd(OUT/'kvarkar_rsd_id_badge.smd',header,badge)
write_smd(OUT/'kvarkar_rsd_lanyard.smd',header,lanyard)

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
qc=qc.replace('kvarkar/herr_kvarkar_v2_r7.mdl','kvarkar/herr_kvarkar_rsd_preview_r15.mdl').replace('"kvarkar_costume.smd"','"kvarkar_rsd_costume.smd"')
qc=qc.replace('$cdmaterials "models/kvarkar/v2/"','$cdmaterials "models/kvarkar/rsd/"\n$cdmaterials "models/kvarkar/v2/"')
qc+='\n$bodygroup "Tie" {\n blank\n studio "kvarkar_optional_tie.smd"\n}\n'
qc+='\n$bodygroup "Department insignia" {\n studio "kvarkar_plain_back_panel.smd"\n studio "kvarkar_rsd_emblem.smd"\n}\n'
qc+='\n$bodygroup "Pager" {\n blank\n studio "kvarkar_rsd_pager.smd"\n}\n'
qc+='\n$bodygroup "ID badge" {\n blank\n studio "kvarkar_rsd_id_badge.smd"\n}\n'
qc+='\n$bodygroup "Lanyard" {\n blank\n studio "kvarkar_rsd_lanyard.smd"\n}\n'
(OUT/'kvarkar_rsd.qc').write_text('\n'.join(line.rstrip() for line in qc.splitlines())+'\n',encoding='utf-8')
print(json.dumps({'costumeTriangles':len(costume),'emblemTriangles':len(emblem),'armour':False,'state':'not worn'}))
