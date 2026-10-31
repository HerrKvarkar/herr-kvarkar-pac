local sourcePath = "models/player/cheddar/omega1/omega1_officer.mdl"
local targetPath = "models/player/cheddar/agent/agent_mike.mdl"
local meshes, sourceBind = util.GetModelMeshes(sourcePath, 0, 0)
local _, targetBind = util.GetModelMeshes(targetPath, 0, 0)
local source = ClientsideModel(sourcePath, RENDERGROUP_OTHER)
local target = ClientsideModel(targetPath, RENDERGROUP_OTHER)
source:SetNoDraw(true) target:SetNoDraw(true)
source:SetupBones() target:SetupBones()
local ids = {}
for id = 0, #targetBind do ids[target:GetBoneName(id)] = id end
local vertices = {}
for _, mesh in ipairs(meshes) do
    if (not string.EndsWith(mesh.material, "omega1_body_02")) then continue end
    for _, vertex in ipairs(mesh.triangles) do
        local p, n, links = Vector(), Vector(), {}
        for _, link in ipairs(vertex.weights) do
            local id = assert(ids[source:GetBoneName(link.bone)], "Unmapped boot bone")
            local matrix = targetBind[id].matrix:GetInverseTR() * sourceBind[link.bone].matrix
            p:Add((matrix * vertex.pos) * link.weight)
            local direction = Vector(vertex.normal)
            direction:Rotate(matrix:GetAngles())
            n:Add(direction * link.weight)
            links[#links + 1] = {bone=id,weight=link.weight}
        end
        n:Normalize()
        vertices[#vertices + 1] = {pos={p.x,p.y,p.z},normal={n.x,n.y,n.z},uv={vertex.u,1-vertex.v},weights=links}
    end
end
file.Write("pac3/kvarkar_source_export/v2_boot_vertices.json",util.TableToJSON(vertices))
local material = "models/omega1/shared/body/omega1_body_02"
local m = Material(material)
local dependencies = {}
for _, key in ipairs({"$basetexture","$bumpmap","$phongexponenttexture","$detail"}) do
    local value=m:GetString(key)
    if value and value~="" then dependencies[key]=value end
end
source:Remove() target:Remove()
return {vertices=#vertices,material=material,dependencies=dependencies,vmt=file.Read("materials/"..material..".vmt","GAME")}
