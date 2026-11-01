"""Build Combat Medic from the approved ISD coat and original medic equipment."""
from pathlib import Path
from collections import defaultdict
import ast,json,re,shutil,copy
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
REPO=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PROFILE=json.loads((REPO/'department_profiles.json').read_text(encoding='utf-8'))['profiles']['combat_medic']
shared=REPO/'source/v2/build_v2.py'
tree=ast.parse(shared.read_text(encoding='utf-8'))
exec(compile(ast.Module([n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['blend','clip','triangulate','split_triangle']],type_ignores=[]),str(shared),'exec'))
scope={name:globals()[name] for name in ['blend','clip','triangulate','split_triangle']}
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


header,costume=read_smd(REPO/'source/isd/kvarkar_isd_costume.smd')
_,back_panel=read_smd(REPO/'source/isd/kvarkar_plain_back_panel.smd')
names={name:int(i) for i,name in re.findall(r'^(\d+) "([^"]+)" -?\d+$',header,re.M)}
hair=[(m,t) for m,t in costume if m=='kvarkar_hair.vmt']
old_gloves=[(m,t) for m,t in costume if m=='kvarkar_leather_gloves.vmt']
remap={'kvarkar_isd_blue_shirt.vmt':'kvarkar_cm_shirt.vmt','kvarkar_isd_leather_coat.vmt':'kvarkar_leather_coat_fine.vmt'}
costume=[(remap.get(m,m),t) for m,t in costume if m not in ['kvarkar_hair.vmt','kvarkar_leather_gloves.vmt']]
def donor(name,material):
 raw=json.loads((OUT/'donor'/(name+'.json')).read_text(encoding='utf-8'))
 out=[]
 for i in range(0,len(raw),3):
  out.append((material,[{'p':np.array(item['pos'],dtype=float),'n':np.array(item['normal'],dtype=float),'uv':np.array(item['uv'],dtype=float),'weights':{names[link['name']]:link['weight'] for link in item['weights']}} for item in raw[i:i+3]]))
 return out
def winding(mesh):
 values=[]
 for _,tri in mesh:
  a,b,c=[v['p'] for v in tri];normal=sum((v['n'] for v in tri),np.zeros(3));values.append(np.dot(np.cross(b-a,c-a),normal))
 return np.median([x for x in values if abs(x)>1e-8])
gloves=donor('gloves','kvarkar_cm_blue_gloves.vmt')
if np.sign(winding(gloves))!=np.sign(winding(old_gloves)):gloves=[(m,[t[0],t[2],t[1]]) for m,t in gloves]
for _,tri in gloves:
 for v in tri:
  v['uv']=np.mod(v['uv'],1.)
  assert np.all(v['uv']>=[.5,.5]) and np.all(v['uv']<=[1.001,1.001]),v['uv']
  v['uv']=v['uv']*2.-1.
costume+=gloves
vest=donor('vest','kvarkar_cm_vest.vmt')
kit=donor('fieldkit','kvarkar_cm_fieldkit.vmt')
for mesh in [vest,kit]:
 for _,tri in mesh:
  for v in tri:
   v['p'][0]*=.88
   scale=.82 if v['p'][1]<.5 else .55
   v['p'][1]=.5+(v['p'][1]-.5)*scale
# Preserve the native front plate thickness while fitting it over the muscular shirt.
vest_front_reference=np.array([[v['p'].copy() for v in tri] for _,tri in vest if max(v['p'][1] for v in tri)<0])
# Recess covered vest edges under the actual coat; match the coat's local skinning.
coat=[tri for m,tri in costume if m=='kvarkar_leather_coat_fine.vmt' and max(v['p'][2] for v in tri)>42]
centers=np.array([np.mean([v['p'] for v in tri],axis=0) for tri in coat]);surface_tree=cKDTree(centers)
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

matched=0
for _,tri in vest:
 for v in tri:
  x,y,z=v['p']
  back=min(1.,max(0.,(y-1.)/2.))
  shoulder=min(1.,max(0.,(z-56.5)/3.))*min(1.,max(0.,(abs(x)-2.5)/1.5))
  edge=min(1.,max(0.,(abs(x)-4.)/1.5))*min(1.,max(0.,(z-46.)/3.))
  factor=max(back,shoulder,edge)
  if factor<=0:continue
  _,ids=surface_tree.query(v['p'],k=min(24,len(coat)))
  options=[]
  for i in np.atleast_1d(ids):
   q,bary=nearest_point(v['p'],coat[int(i)]);options.append((np.linalg.norm(q-v['p']),int(i),q,bary))
  _,index,q,bary=min(options,key=lambda a:a[0]);surface=coat[index]
  normal=sum((a['n']*w for a,w in zip(surface,bary)),np.zeros(3));normal/=max(np.linalg.norm(normal),1e-9)
  signed=np.dot(v['p']-q,normal)
  if signed>-.28:v['p']-=normal*(signed+.28)*factor
  weights={bone:weight*(1.-factor) for bone,weight in v['weights'].items()}
  for a,w in zip(surface,bary):
   for bone,weight in a['weights'].items():weights[bone]=weights.get(bone,0.)+weight*w*factor
  v['weights']=weights;matched+=1
shirt=[tri for m,tri in costume if m=='kvarkar_cm_shirt.vmt']
shirt_positions=np.array([[v['p'] for v in tri] for tri in shirt])
def surface_hit(positions,x,z,front=True):
 a,b,c=positions[:,0],positions[:,1],positions[:,2]
 ab=b[:,[0,2]]-a[:,[0,2]];ac=c[:,[0,2]]-a[:,[0,2]];q=np.array([x,z])-a[:,[0,2]]
 det=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0];safe=np.where(abs(det)>1e-9,det,1.)
 u=(q[:,0]*ac[:,1]-q[:,1]*ac[:,0])/safe;w=(ab[:,0]*q[:,1]-ab[:,1]*q[:,0])/safe
 ids=np.flatnonzero((abs(det)>1e-9)&(u>=-.001)&(w>=-.001)&(u+w<=1.001))
 if not len(ids):return None
 ys=(1.-u-w)*a[:,1]+u*b[:,1]+w*c[:,1]
 index=(min if front else max)(ids,key=lambda i:ys[i])
 return ys[index],int(index),[1.-u[index]-w[index],u[index],w[index]]
for _,tri in vest:
 for v in tri:
  x,y,z=v['p'];factor=min(1.,max(0.,(4.5-abs(x))/1.))
  if y>=0 or factor<=0:continue
  hit=surface_hit(shirt_positions,x,z)
  reference=surface_hit(vest_front_reference,x,z,False)
  if hit is None or reference is None:continue
  displacement=max(0.,reference[0]-hit[0]+.35)
  v['p'][1]-=displacement*factor
  weights={bone:weight*(1.-factor) for bone,weight in v['weights'].items()}
  for point,w in zip(shirt[hit[1]],hit[2]):
   for bone,weight in point['weights'].items():weights[bone]=weights.get(bone,0.)+weight*max(0.,w)*factor
  v['weights']=weights
# Mount the original medical pouch centrally on the carrier, leaving its back
# against the carrier and its front clear of the open coat.
kit_points=np.array([v['p'] for _,tri in kit for v in tri]);kit_center=(kit_points.min(0)+kit_points.max(0))/2.
for _,tri in kit:
 for v in tri:v['p']=(v['p']-kit_center)*.82+np.array([-2.8,-7.,48.])
write_smd(OUT/'kvarkar_cm_armour.smd',header,vest)
write_smd(OUT/'kvarkar_cm_medical_kit.smd',header,kit)
# Three headgear choices include their matching hair mesh; one selector handles both.
helmet=[]
for name in ['helmet_shell','helmet_rails','helmet_mounts']:helmet+=donor(name,'kvarkar_cm_'+name+'.vmt')
headset=donor('headset','kvarkar_cm_headset.vmt')
# The donor contains a detached three-triangle mic cap without its wire.
headset=[(m,t) for m,t in headset if not (max(v['p'][2] for v in t)<62.55 and max(v['p'][1] for v in t)<-3.7)]
# Size the shell to the measured skull and tighten the native lower webbing
# continuously, preserving the original strap/buckle assembly and its skinning.
scale=np.array([.92,.94,1.]);center=np.array([-.1,-.5,68.])
contacts=0
# Apply the same continuous fitting cage to every helmet submesh, including
# the strap sections welded to the shell, so their joins remain connected.
for _,tri in helmet:
 for v in tri:
  v['p']=center+(v['p']-center)*scale
  v['n']=v['n']/scale;v['n']/=max(np.linalg.norm(v['n']),1e-9)
  x,y,z=v['p'];t=min(1.,max(0.,(68.-z)/6.));f=t*t*(3.-2.*t)
  derivative=-6.*t*(1.-t)/6. if 0<t<1 else 0.
  sx=1.-.10*f;sy=1.-(.10*f if y<-.5 else 0.)
  dx=-.10*derivative;dy=-.10*derivative if y<-.5 else 0.
  jac=np.array([[sx,0.,(x+.1)*dx],[0.,sy,(y+.5)*dy],[0.,0.,1.+.55*derivative]])
  v['p']=np.array([-.1+(x+.1)*sx,-.5+(y+.5)*sy,z+.55*f])
  v['n']=np.linalg.solve(jac.T,v['n']);v['n']/=max(np.linalg.norm(v['n']),1e-9)
  if f>0:contacts+=1
for _,tri in headset:
 for v in tri:
  x=v['p'][0];v['p'][0]-=np.sign(x)*.25*min(1.,abs(x)/2.)
  v['p'][1]=-.5+(v['p'][1]+.5)*.94
print(json.dumps({'helmetWidthScale':.92,'helmetDepthScale':.94,'fittedStrapVertices':contacts}))
shell=[tri for m,tri in helmet if m=='kvarkar_cm_helmet_shell.vmt' and min(v['p'][2] for v in tri)>67.]
cap=np.array([[v['p'] for v in tri] for tri in shell]);a=cap[:,0];e1=cap[:,1]-a;e2=cap[:,2]-a
origin=np.array([0.,0.,67.2]);s=origin-a;q=np.cross(s,e1)
tucked=copy.deepcopy(hair);changed=0;max_change=0.
cache={}
for _,tri in tucked:
 for v in tri:
  p=v['p'];key=tuple(p)
  if key in cache:v['p']=cache[key].copy();continue
  if p[2]<67.5:cache[key]=p.copy();continue
  direction=p-origin;distance=np.linalg.norm(direction)
  if distance<.1:cache[key]=p.copy();continue
  direction/=distance;h=np.cross(np.broadcast_to(direction,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h)
  safe=np.where(abs(det)>1e-9,det,1.);u=np.einsum('ij,ij->i',s,h)/safe;w=q@direction/safe;t=np.einsum('ij,ij->i',e2,q)/safe
  valid=(abs(det)>1e-9)&(u>=-.0001)&(w>=-.0001)&(u+w<=1.0001)&(t>.1)
  hits=t[valid]
  if len(hits):
   limit=max(.1,float(hits.min())-.15)
   if distance>limit:
    v['p']=origin+direction*limit;changed+=1;max_change=max(max_change,distance-limit)
  cache[key]=v['p'].copy()
assert changed>0,'Hair tuck failed to find crown intersections'
write_smd(OUT/'kvarkar_cm_hair_normal.smd',header,hair)
write_smd(OUT/'kvarkar_cm_helmet.smd',header,tucked+helmet)
write_smd(OUT/'kvarkar_cm_helmet_headset.smd',header,tucked+helmet+headset)
# Reuse the approved ISD back-panel cutout, preserving every other coat triangle.
panel=[tri for _,tri in back_panel]
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

emblem=emboss_panel('medical_logo_reference.png','kvarkar_cm_leather_emboss.vmt')
write_smd(OUT/'kvarkar_cm_back_emblem.smd',header,emblem)
write_smd(OUT/'kvarkar_cm_costume.smd',header,costume)
for name in ['kvarkar_animated_head.smd','kvarkar_face.vta','kvarkar_merged_idle.smd']:shutil.copy2(REPO/'source/v2'/name,OUT/name)
qc=(REPO/'source/v2/kvarkar_animated.qc').read_text(encoding='utf-8')
qc=qc.replace('kvarkar/herr_kvarkar_v2_r7.mdl','kvarkar/herr_kvarkar_combat_medic_r6.mdl').replace('"kvarkar_costume.smd"','"kvarkar_cm_costume.smd"').replace('costume_and_hair','costume')
qc=qc.replace('$cdmaterials "models/kvarkar/v2/"','$cdmaterials "models/kvarkar/combat_medic/"\n$cdmaterials "models/kvarkar/v2/"')
qc+='\n$bodygroup "Department armour" {\n blank\n studio "kvarkar_cm_armour.smd"\n}\n'
qc+='\n$bodygroup "Medical kit" {\n blank\n studio "kvarkar_cm_medical_kit.smd"\n}\n'
qc+='\n$bodygroup "Headgear" {\n studio "kvarkar_cm_hair_normal.smd"\n studio "kvarkar_cm_helmet.smd"\n studio "kvarkar_cm_helmet_headset.smd"\n}\n'
qc+='\n$bodygroup "Department insignia" {\n studio "kvarkar_plain_back_panel.smd"\n studio "kvarkar_cm_back_emblem.smd"\n}\n'
(OUT/'kvarkar_combat_medic.qc').write_text('\n'.join(line.rstrip() for line in qc.splitlines())+'\n',encoding='utf-8')
summary={'costumeTriangles':len(costume),'vestTriangles':len(vest),'kitTriangles':len(kit),'helmetTriangles':len(helmet),'headsetTriangles':len(headset),'blueGloveTriangles':len(gloves),'tuckedHairVertices':changed,'maxCrownTuck':max_change,'matchedArmourVertices':matched,'emblemTriangles':len(emblem),'customRunningOverride':False}
(OUT/'build-status.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary))

