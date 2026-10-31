"""Build v2 geometry from the preserved, animated v1 source meshes."""
from pathlib import Path
from collections import defaultdict
import argparse
import json
import math
import re
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
V1 = ROOT.parent
parser = argparse.ArgumentParser()
parser.add_argument('--revision', type=int, default=1)
args = parser.parse_args()


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def parse_vertex(line):
    a = list(map(float, line.split()))
    return {'p': np.array(a[1:4]), 'n': np.array(a[4:7]), 'uv': np.array(a[7:9]),
            'weights': {int(a[10+j*2]): a[11+j*2] for j in range(int(a[9]))}}


def vertex_text(v):
    links = sorted(v['weights'].items(), key=lambda x: -x[1])[:3]
    total = sum(w for _, w in links)
    assert total > 0
    a = ['0'] + [f'{x:.8f}' for x in [*v['p'], *v['n'], *v['uv']]] + [str(len(links))]
    for bone, weight in links:
        a.extend((str(bone), f'{weight/total:.8f}'))
    return ' '.join(a)


def read_mesh(path):
    header, body = path.read_text().split('triangles\n', 1)
    lines = body.splitlines()
    return header, [(lines[i], [parse_vertex(s) for s in lines[i+1:i+4]])
                    for i in range(0, len(lines)-3, 4)]


def write_mesh(path, header, triangles):
    lines = [header.rstrip(), 'triangles']
    for material, triangle in triangles:
        remap={'kvarkar_field_coat.vmt':'kvarkar_leather_coat_fine.vmt','kvarkar_gloves.vmt':'kvarkar_leather_gloves.vmt','kvarkar_field_trousers.vmt':'kvarkar_field_trousers_clean.vmt'}
        lines.append(remap.get(material,material))
        lines.extend(vertex_text(v) for v in triangle)
    lines.append('end')
    path.write_text('\n'.join(lines) + '\n')


def blend(a, b, t):
    weights = defaultdict(float)
    for v, factor in [(a, 1-t), (b, t)]:
        for bone, weight in v['weights'].items():
            weights[bone] += weight*factor
    return {'p': a['p']*(1-t)+b['p']*t, 'n': a['n']*(1-t)+b['n']*t,
            'uv': a['uv']*(1-t)+b['uv']*t, 'weights': dict(weights)}


def clip(poly, axis, boundary, direction):
    result = []
    if not poly:
        return result
    previous = poly[-1]
    da = (previous['p'][axis]-boundary)*direction
    for vertex in poly:
        db = (vertex['p'][axis]-boundary)*direction
        if (da >= 0) != (db >= 0):
            result.append(blend(previous, vertex, da/(da-db)))
        if db >= 0:
            result.append(vertex)
        previous, da = vertex, db
    return result


def triangulate(poly):
    return [[poly[0], poly[i], poly[i+1]] for i in range(1, len(poly)-1)]


def face_warp(p):
    x, y, z = p
    front = clamp((1.3-y)/1.8)
    # Keep a natural chin taper; definition belongs at the cheek and rear jaw.
    jaw = math.exp(-((z-63.0)/1.35)**4) * front
    corner = math.exp(-((z-64.15)/0.65)**2) * clamp((y+2.0)/2.3)
    cheek = math.exp(-((z-65.35)/0.8)**2) * front
    cheekbone = math.exp(-((z-66.3)/0.45)**2) * front
    width = clamp((abs(x)-0.7)/1.2)
    x *= 1 - 0.015*jaw*width + 0.035*corner*width - 0.04*cheek*width + 0.035*cheekbone*width
    neck = math.exp(-((z-60.8)/1.1)**2) * clamp((y+2)/2)
    x *= 1+0.055*neck
    return np.array((x,y,z))


def warped_normal(fn, p, normal):
    h = 0.001
    jacobian = np.column_stack([(fn(p+np.eye(3)[i]*h)-fn(p-np.eye(3)[i]*h))/(2*h) for i in range(3)])
    result = np.linalg.solve(jacobian.T, normal)
    return result / max(np.linalg.norm(result), 1e-10)


header, costume = read_mesh(V1/'kvarkar_costume.smd')
nodes = {int(i): (name, int(parent)) for i,name,parent in re.findall(r'^(\d+) "([^"]+)" (-?\d+)$', header, re.M)}
bone_rows = header.split('skeleton\n', 1)[1].splitlines()
transforms = {}
for line in bone_rows:
    a = line.split()
    if len(a) != 7:
        continue
    bone = int(a[0]); x,y,z,rx,ry,rz = map(float,a[1:])
    cx,sx,cy,sy,cz,sz = math.cos(rx),math.sin(rx),math.cos(ry),math.sin(ry),math.cos(rz),math.sin(rz)
    matrix = np.eye(4)
    matrix[:3,:3] = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]]) @ np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]) @ np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
    matrix[:3,3] = [x,y,z]
    parent = nodes[bone][1]
    transforms[bone] = transforms[parent] @ matrix if parent >= 0 else matrix

segments = {}
arm_bones = set()
for bone,(name,parent) in nodes.items():
    if any(word in name for word in ('Clavicle','UpperArm','Forearm','Hand','Finger','Bicep','Ulna','Wrist','Shoulder')):
        arm_bones.add(bone)
    child_name = name.replace('UpperArm','Forearm') if 'UpperArm' in name else name.replace('Forearm','Hand') if 'Forearm' in name else None
    if child_name:
        child = next(i for i,(n,_) in nodes.items() if n==child_name)
        segments[bone] = (transforms[bone][:3,3], transforms[child][:3,3], 'UpperArm' in name)


def body_warp(p, weights, material):
    result = p.copy()
    if material in ('kvarkar_dea_shirt.vmt','kvarkar_black_tie.vmt','kvarkar_field_coat.vmt'):
        x,y,z = p
        trunk = clamp((10-abs(x))/3) * clamp((z-42)/5) * clamp((64-z)/3)
        chest = math.exp(-((z-55)/6)**2)
        waist = math.exp(-((z-44)/3.5)**2)
        result[0] *= 1 + trunk*(0.10*chest-0.035*waist)
        result[1] = 0.5 + (result[1]-0.5)*(1+trunk*(0.12*chest-0.025*waist))
        for bone, weight in weights.items():
            if bone not in segments:
                continue
            start,end,upper = segments[bone]
            direction = end-start
            t = clamp(np.dot(p-start,direction)/np.dot(direction,direction))
            radial = p-(start+t*direction)
            amount = 0.19*math.exp(-((t-0.3)/0.55)**2) if upper else 0.09*math.sin(t*math.pi)
            result += radial*amount*weight
        if material == 'kvarkar_field_coat.vmt' and p[2] < 40:
            result[2] = 40-(40-p[2])*1.72
            flare=clamp((42-result[2])/26)
            result[0]*=1+0.16*flare
            result[1]=0.8+(result[1]-0.8)*(1+0.22*flare)
        if material == 'kvarkar_dea_shirt.vmt':
            collar = clamp((p[2]-59.0)/2)*clamp((p[1]+0.2)/1.2)
            result[0] *= 1-0.07*collar
            result[1] = 0.8+(result[1]-0.8)*(1-0.12*collar)
        elif material == 'kvarkar_field_coat.vmt':
            collar = clamp((p[2]-58.5)/3)*clamp((p[1]-0.5)/1.3)*clamp((4.8-abs(p[0]))/1.5)
            result[1] += 0.18*collar
            result[2] += 0.18*collar
    return result


# Preserve the round button components instead of stretching them with the hem.
coat_points={};coat_parent={}
def coat_find(i):
    while coat_parent[i]!=i:
        coat_parent[i]=coat_parent[coat_parent[i]];i=coat_parent[i]
    return i
for material,triangle in costume:
    if material!='kvarkar_field_coat.vmt':continue
    indices=[]
    for v in triangle:
        key=tuple(np.round(v['p'],4));i=coat_points.setdefault(key,len(coat_points));coat_parent.setdefault(i,i);indices.append(i)
    for i in indices[1:]:coat_parent[coat_find(i)]=coat_find(indices[0])
coat_groups=defaultdict(list)
for key,i in coat_points.items():coat_groups[coat_find(i)].append(key)
buttons={}
for points in coat_groups.values():
    a=np.array(points);center=a.mean(axis=0)
    if len(a)<100 and max(np.ptp(a,axis=0))<2 and center[1]<-4 and abs(center[0])<6:
        representative=next(v for m,t in costume if m=='kvarkar_field_coat.vmt' for v in t if tuple(np.round(v['p'],4))==points[0])
        fn=lambda p:body_warp(p,representative['weights'],'kvarkar_field_coat.vmt')
        h=.001;j=np.column_stack([(fn(center+np.eye(3)[i]*h)-fn(center-np.eye(3)[i]*h))/(2*h) for i in range(3)])
        u,_,vt=np.linalg.svd(j);rotation=u@vt
        for key in points:buttons[key]=(center,fn(center),rotation)

triangles = []
for material, triangle in costume:
    # Discard the source shirt sleeves that were hidden under v1's coat.
    if material == 'kvarkar_dea_trousers.vmt' and any(sum(w for b,w in v['weights'].items() if b in arm_bones)>0.2 for v in triangle):
        continue
    poly = triangle
    if material == 'kvarkar_dea_trousers.vmt':
        poly = clip(poly, 2, 41.0, 1)
    for tri in triangulate(poly):
        shaped = []
        for v in tri:
            button=buttons.get(tuple(np.round(v['p'],4))) if material=='kvarkar_field_coat.vmt' else None
            if button is not None:
                center,target,rotation=button
                shaped.append({**v,'p':target+rotation@(v['p']-center),'n':rotation@v['n']})
                continue
            fn = lambda p, v=v, mat=material: body_warp(p,v['weights'],mat)
            shaped.append({**v,'p':fn(v['p']),'n':warped_normal(fn,v['p'],v['n'])})
        triangles.append((material,shaped))

# Use the exact boot components, excluding their source camouflage trousers.
raw = json.loads((ROOT/'boot_vertices.json').read_text())
parent = {}
position_ids = {}
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
raw_triangles = []
for i in range(0,len(raw),3):
    ids=[]
    for item in raw[i:i+3]:
        key=tuple(round(x,3) for x in item['pos'])
        index=position_ids.setdefault(key,len(position_ids)); parent.setdefault(index,index); ids.append(index)
    for index in ids[1:]: parent[find(index)] = find(ids[0])
    raw_triangles.append(ids)
component_max = defaultdict(lambda:-1e9)
for key,index in position_ids.items(): component_max[find(index)] = max(component_max[find(index)],key[2])
boot_count = 0
field_pant_count = 0
for i,indices in enumerate(raw_triangles):
    maximum=component_max[find(indices[0])]
    is_boot=maximum<11
    is_pant=maximum>40
    if not (is_boot or is_pant):
        continue
    tri=[]
    for offset in (0,2,1):
        v=raw[i*3+offset]
        tri.append({'p':np.array(v['pos']),'n':np.array(v['normal']),'uv':np.array(v['uv']),
                    'weights':{w['bone']:w['weight'] for w in v['weights']}})
    if is_boot:
        triangles.append(('kvarkar_field_boots.vmt',tri));boot_count+=1
    else:
        for triangle in triangulate(clip(tri,2,42.2,-1)):
            fitted=[]
            def fit_waist(p):
                result=p.copy();factor=clamp((p[2]-35)/7.2)
                result[0]*=1-0.12*factor
                result[1]=0.5+(result[1]-0.5)*(1-0.08*factor)
                return result
            for v in triangle:
                fitted.append({**v,'p':fit_waist(v['p']),'n':warped_normal(fit_waist,v['p'],v['n'])})
            triangles.append(('kvarkar_field_trousers.vmt',fitted));field_pant_count+=1

# Shallow sewn pocket panels follow the actual OUTER-thigh surfaces and skinning.
def split_triangle(tri):
    a,b,c=tri;ab=blend(a,b,.5);bc=blend(b,c,.5);ca=blend(c,a,.5)
    return [[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]
pockets=[]
def pocket_tri(tri,depth=0):
    if depth<3 and max(np.linalg.norm(tri[i]['p']-tri[(i+1)%3]['p']) for i in range(3))>1:
        for child in split_triangle(tri):pocket_tri(child,depth+1)
        return
    out=[]
    for v in tri:
        s=clamp((v['p'][1]+1.4)/4.0);t=clamp((34.5-v['p'][2])/6.5)
        offset=.015+.20*math.sin(s*math.pi)*math.sin(t*math.pi)
        out.append({**v,'p':v['p']+v['n']*offset,'uv':np.array([.865+.13*s,1-(.012+.21*t)])})
    pockets.append(('kvarkar_field_pocket.vmt',out))
for material,tri in triangles:
    if material!='kvarkar_field_trousers.vmt':continue
    center=np.mean([v['p'] for v in tri],axis=0);normal=np.mean([v['n'] for v in tri],axis=0)
    if abs(center[0])<5 or normal[0]*np.sign(center[0])<.35:continue
    poly=tri
    for axis,boundary,sign in [(1,-1.4,1),(1,2.6,-1),(2,28,1),(2,34.5,-1)]:poly=clip(poly,axis,boundary,sign)
    for clipped in triangulate(poly):pocket_tri(clipped)
triangles.extend(pockets)

# Tie clearance and skinning are derived from the shirt's front surface.
shirt = [tri for mat,tri in triangles if mat=='kvarkar_dea_shirt.vmt']
shirt_positions = np.array([[v['p'] for v in tri] for tri in shirt])
samples = 0
for material,tri in triangles:
    if material != 'kvarkar_black_tie.vmt': continue
    for v in tri:
        if v['p'][1] > -2 or v['p'][2] > 61.25: continue
        x,z = v['p'][[0,2]]
        a=shirt_positions[:,0,[0,2]];b=shirt_positions[:,1,[0,2]];c=shirt_positions[:,2,[0,2]]
        ab=b-a;ac=c-a;q=np.array([x,z])-a
        denominator=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
        safe=np.where(np.abs(denominator)>1e-9,denominator,1)
        u=(q[:,0]*ac[:,1]-q[:,1]*ac[:,0])/safe
        w=(ab[:,0]*q[:,1]-ab[:,1]*q[:,0])/safe
        valid=(np.abs(denominator)>1e-9)&(u>=-0.001)&(w>=-0.001)&(u+w<=1.001)
        indices=np.flatnonzero(valid)
        if not len(indices):continue
        hit_y=(1-u-w)*shirt_positions[:,0,1]+u*shirt_positions[:,1,1]+w*shirt_positions[:,2,1]
        index=min(indices,key=lambda j:hit_y[j])
        v['p'][1]=min(v['p'][1],hit_y[index]-0.18)
        weights=defaultdict(float)
        for vertex,factor in zip(shirt[index],(1-u[index]-w[index],u[index],w[index])):
            for bone,weight in vertex['weights'].items():weights[bone]+=weight*max(0,factor)
        links=sorted(weights.items(),key=lambda p:-p[1])[:3];total=sum(w for _,w in links)
        v['weights']={b:w/total for b,w in links}
        samples+=1

# Both collars use the same underlying neck/chest blend, with outer-coat clearance.
collar_vertices=[v for t in shirt for v in t if v['p'][2]>59 and v['p'][1]>0]
for material,tri in triangles:
    if material!='kvarkar_field_coat.vmt':continue
    for v in tri:
        if v['p'][2]<59.5 or v['p'][1]<0.5 or abs(v['p'][0])>4.5:continue
        nearest=min(collar_vertices,key=lambda s:np.linalg.norm(s['p']-v['p']))
        if np.linalg.norm(nearest['p']-v['p'])<2:
            v['weights']=nearest['weights'].copy()

# Two independent, damped coat-tail bones replace the direct leg attachment.
# Their local +Z points down the hanging skirt, as required by Source's solver.
tail_ids=[max(nodes)+1,max(nodes)+2]
tail_names=['Kvarkar.CoatTail.L','Kvarkar.CoatTail.R']
extra_nodes=[];extra_pose=[]
for bone,name,x in zip(tail_ids,tail_names,[3.0,-3.0]):
    world=np.eye(4);world[:3,:3]=np.diag([1,-1,-1]);world[:3,3]=[x,0.8,39]
    local=np.linalg.inv(transforms[0])@world
    rx=math.atan2(local[2,1],local[2,2]);ry=math.asin(clamp(-local[2,0],-1,1));rz=math.atan2(local[1,0],local[0,0])
    extra_nodes.append(f'{bone} "{name}" 0')
    extra_pose.append(f'{bone} '+' '.join(f'{n:.8f}' for n in [*local[:3,3],rx,ry,rz]))
header=re.sub(r'(nodes\n.*?)(\nend\n)',lambda m:m[1]+'\n'+'\n'.join(extra_nodes)+m[2],header,count=1,flags=re.S)
header=re.sub(r'(skeleton\n.*?)(\nend\n)',lambda m:m[1]+'\n'+'\n'.join(extra_pose)+m[2],header,count=1,flags=re.S)
leg_bones={b for b,(name,_) in nodes.items() if any(n in name for n in ('Thigh','Calf','Foot','Toe'))}
for material,tri in triangles:
    if material!='kvarkar_field_coat.vmt':continue
    for v in tri:
        if v['p'][2]>=41:continue
        amount=clamp((41-v['p'][2])/23)
        amount=amount*amount*(3-2*amount)
        left=clamp((v['p'][0]+1.5)/3)
        weights=defaultdict(float)
        for bone,weight in v['weights'].items():weights[0 if bone in leg_bones else bone]+=weight*(1-amount)
        weights[tail_ids[0]]+=amount*left
        weights[tail_ids[1]]+=amount*(1-left)
        v['weights']=dict(weights)

# A true shallow relief of the supplied DEA emblem, integrated in the back panel.
# Original leather UVs and bone weights continue across the stamp; no badge plane.
alpha=np.asarray(Image.open(ROOT.parent.parent/'assets/dea_logo_reference.png').getchannel('A'),dtype=float)/255
def logo_alpha(p):
    u=(4-p[0])/8;v=(58-p[2])/8
    if not (0<=u<=1 and 0<=v<=1):return 0.0
    x=u*(alpha.shape[1]-1);y=v*(alpha.shape[0]-1);ix=int(x);iy=int(y);fx=x-ix;fy=y-iy
    jx=min(ix+1,alpha.shape[1]-1);jy=min(iy+1,alpha.shape[0]-1)
    return alpha[iy,ix]*(1-fx)*(1-fy)+alpha[iy,jx]*fx*(1-fy)+alpha[jy,ix]*(1-fx)*fy+alpha[jy,jx]*fx*fy
stamped=[];stamp_count=0
def stamp_triangle(tri,depth=0):
    global stamp_count
    positions=np.array([v['p'] for v in tri]);lo=positions.min(axis=0);hi=positions.max(axis=0)
    if hi[0]<-4 or lo[0]>4 or hi[2]<50 or lo[2]>58:
        stamped.append(('kvarkar_field_coat.vmt',tri));return
    x0=max(0,int((4-hi[0])/8*(alpha.shape[1]-1)));x1=min(alpha.shape[1]-1,int((4-lo[0])/8*(alpha.shape[1]-1))+1)
    y0=max(0,int((58-hi[2])/8*(alpha.shape[0]-1)));y1=min(alpha.shape[0]-1,int((58-lo[2])/8*(alpha.shape[0]-1))+1)
    region=alpha[y0:y1+1,x0:x1+1]
    if region.size==0 or region.max()==0:
        stamped.append(('kvarkar_field_coat.vmt',tri));return
    span=max(hi[0]-lo[0],hi[2]-lo[2])
    if depth<9 and span>.09 and region.min()<.999:
        for child in split_triangle(tri):stamp_triangle(child,depth+1)
        return
    out=[]
    for vertex in tri:
        p=vertex['p'];a=logo_alpha(p);h=.03
        dx=(logo_alpha(p+np.array([h,0,0]))-logo_alpha(p-np.array([h,0,0])))/(2*h)
        dz=(logo_alpha(p+np.array([0,0,h]))-logo_alpha(p-np.array([0,0,h])))/(2*h)
        n=vertex['n'].copy();n[0]-=.045*dx*n[1];n[2]-=.045*dz*n[1];n/=max(np.linalg.norm(n),1e-9)
        out.append({**vertex,'p':p+np.array([0,.045*a,0]),'n':n})
    material='kvarkar_dea_emboss.vmt' if logo_alpha(positions.mean(axis=0))>.4 else 'kvarkar_field_coat.vmt'
    stamped.append((material,out));stamp_count+=1
for material,tri in triangles:
    positions=np.array([v['p'] for v in tri])
    if material=='kvarkar_field_coat.vmt' and positions[:,1].min()>1 and np.mean([v['n'][1] for v in tri])>.2:
        stamp_triangle(tri)
    else:stamped.append((material,tri))
triangles=stamped
write_mesh(ROOT/'kvarkar_costume.smd',header,triangles)
head_header, head = read_mesh(V1/'kvarkar_animated_head.smd')
for _,tri in head:
    for v in tri:
        v['n']=warped_normal(face_warp,v['p'],v['n'])
        v['p']=face_warp(v['p'])
write_mesh(ROOT/'kvarkar_animated_head.smd',head_header,head)

vta=(V1/'kvarkar_face.vta').read_text()
prefix, animation=vta.split('vertexanimation\n',1)
out=[]
for line in animation.splitlines():
    values=line.split()
    if len(values)==7 and values[0].isdigit():
        p=np.array(list(map(float,values[1:4])));n=np.array(list(map(float,values[4:7])))
        n=warped_normal(face_warp,p,n);p=face_warp(p)
        line=values[0]+' '+' '.join(f'{x:.8f}' for x in [*p,*n])
    out.append(line)
(ROOT/'kvarkar_face.vta').write_text(prefix+'vertexanimation\n'+'\n'.join(out)+'\n')
qc=(V1/'kvarkar_animated.qc').read_text()
qc=re.sub(r'\$modelname "[^"]+"',f'$modelname "kvarkar/herr_kvarkar_v2_r{args.revision}.mdl"',qc)
qc=qc.replace('models/kvarkar/final_v1/','models/kvarkar/v2/')
for name in tail_names:
    qc+='\n$jigglebone "'+name+'" {\n is_flexible {\n  length 26\n  tip_mass 15\n  yaw_stiffness 110\n  yaw_damping 10\n  pitch_stiffness 100\n  pitch_damping 10\n  along_stiffness 120\n  along_damping 10\n  angle_constraint 8\n }\n}\n'
(ROOT/'kvarkar_animated.qc').write_text(qc)
print(json.dumps({'revision':args.revision,'costume_triangles':len(triangles),'boot_triangles':boot_count,
                  'matching_field_trouser_triangles':field_pant_count,
                  'outer_pocket_triangles':len(pockets),'emboss_relief_triangles':stamp_count,
                  'tie_vertices_matched_to_shirt':samples,'coat_hem_z':min(v['p'][2] for m,t in triangles if m=='kvarkar_field_coat.vmt' for v in t)},indent=2))
