from . import struct_w3d
from .reader import ReadLong, GetChunkSize, ReadMesh, ReadHierarchy, ReadAnimation, ReadCompressedAnimation, ReadHLod, ReadBox

import logging
logger = logging.getLogger("W3DModel.w3d")


class W3DModel(object):

    def __init__(self, meshes, hierarchy, animation, compressed_animation, hlod, box):
        self.meshes = meshes
        self.hierarchy = hierarchy
        self.animation = animation
        self.compressed_animation = compressed_animation
        self.hlod = hlod
        self.box = box

    @classmethod
    def from_file(Cls, path):

        with open(path, "rb") as file:
            file.seek(0,2)
            filesize = file.tell()
            file.seek(0,0)
            Meshes = []
            Box = struct_w3d.Box()
            Textures = []
            Hierarchy = struct_w3d.Hierarchy()
            Animation = struct_w3d.Animation()
            CompressedAnimation = struct_w3d.CompressedAnimation()
            HLod = struct_w3d.HLod()
            amtName = ""

            while file.tell() < filesize:
                Chunktype = ReadLong(file)
                Chunksize = GetChunkSize(ReadLong(file))
                #print(Chunksize)
                chunkEnd = file.tell() + Chunksize
                if Chunktype == 0:
                    m = ReadMesh(file, chunkEnd)
                    Meshes.append(m)
                    file.seek(chunkEnd,0)

                elif Chunktype == 256:
                    Hierarchy = ReadHierarchy(file, chunkEnd)
                    file.seek(chunkEnd,0)

                elif Chunktype == 512:
                    Animation = ReadAnimation(file, chunkEnd)
                    file.seek(chunkEnd,0)

                elif Chunktype == 640:
                    CompressedAnimation = ReadCompressedAnimation(file, chunkEnd)
                    file.seek(chunkEnd,0)

                elif Chunktype == 1792:
                    HLod = ReadHLod(file, chunkEnd)
                    file.seek(chunkEnd,0)

                elif Chunktype == 1856:
                    Box = ReadBox(file)
                    file.seek(chunkEnd,0)

                else:
                    logger.error("unknown chunktype in File: %s" % Chunktype)
                    file.seek(Chunksize,1)

        return Cls(Meshes, Hierarchy, Animation, CompressedAnimation, HLod, Box)


    def as_threejs(self):
        logger.debug("building threejs object...")

        if not self.hlod.header.modelName == self.hlod.header.HTreeName:
            raise NotImplementedError("hlod.header.modelName != hlod.header.HTreeName")

        mesh_index = { m.header.meshName: m for m in self.meshes }

        object_root = self.createHierarchyWrapper(self.hierarchy.pivots, self.meshes)
        print("object_root", object_root)
        """
        pivot_names = { i: p.name for i, p in enumerate(self.hierarchy.pivots) }
        print(pivot_names)
        pivot_hierarchy = {}
        for pivot in self.hierarchy.pivots:
            if pivot.parentID != 4294967295:
                pivot_hierarchy.setdefault(pivot_names[pivot.parentID], []).append(pivot)

        print(pivot_hierarchy[pivot_names[0]])
        print(pivot_hierarchy)


#        raise NotImplementedError

        for m in self.meshes:
            logger.debug("preparing mesh %s" % m.header.meshName)
            Faces = []
            for f in m.faces:
                Faces.append(Face(*f.vertIds, f.normal))

#            print(Faces)

            if len(m.matlPass.txStage.txCoords)>0:
                index = 0
                for f in m.faces:
                    face = Faces[index]
#                    print(
#                        m.matlPass.txStage.txCoords[face.a],
#                        m.matlPass.txStage.txCoords[face.b],
#                        m.matlPass.txStage.txCoords[face.c]
#                    )
#                    f.loops[0][uv_layer].uv = m.matlPass.txStage.txCoords[Faces[index][0]]
#                    f.loops[1][uv_layer].uv = m.matlPass.txStage.txCoords[Faces[index][1]]
#                    f.loops[2][uv_layer].uv = m.matlPass.txStage.txCoords[Faces[index][2]]
                    index+=1


        """

        logger.info("Threejs object built")

        _object = object_root.to_json()

        return {
            "images": [],
            "animations": [],
            "object": _object,
            "textures": [],
            "metadata": {},
            "geometries": [ mesh.to_json() for mesh in MeshWrapper.wrappings() ],
            "materials": []
        }


    def _as_threejs_object(self, pivot_hierarchy, mesh_index, pivot=None):
        mesh = None
        if pivot is None:  # search for root
            pivots = pivot_hierarchy.get("ROOTTRANSFORM")
            assert pivots, "No root pivot found"
            assert len(pivots) == 1, "More than one root node found"
            pivot = pivots[0]

            print(mesh_index)
            return {
                "type": "Scene",
                "children": [ self._as_threejs_object(pivot_hierarchy, mesh_index, p) for p in pivot_hierarchy.get(pivot.name, []) ],
                "matrix": [item for item in matrix4x4(pivot.position, pivot.rotation)],
                "uuid": "A591ACA3-4DE6-4996-9D9A-%s" % pivot.name,
            }


        if not mesh:
            mesh = mesh_index.get(pivot.name)



        return {
            "type": "Mesh" if mesh is not None else "Unknown",
            "name": pivot.name,
            "uuid": "DDA9AE26-14F9-3E6A-9BDD-%s" % pivot.name,
            "matrix": [item for item in matrix4x4(pivot.position, pivot.rotation)],
            "visible": True,
#            "material": "A4EB44DB-19EB-3E46-858B-2C653E96438F",
            "castShadow": True,
            "receiveShadow": True,
            "geometry": mesh.header.meshName if mesh else None,
            "children": [ self._as_threejs_object(pivot_hierarchy, mesh_index, p) for p in pivot_hierarchy.get(pivot.name, []) ],
        }




    def createHierarchyWrapper(self, pivots, meshes):
        # convert to wrappers
        pivots = [ PivotWrapper.wrap(pivot) for pivot in pivots ]

        meshIndex = { m.header.meshName: MeshWrapper.wrap(m) for m in meshes }
        for pivot in pivots:
            pivot.mesh = meshIndex.get(pivot.name)

        index = { i: pivot for i, pivot in enumerate(pivots) }

        for pivot in pivots:
            if pivot.parentID != 4294967295:
                parent = index[pivot.parentID]
                parent.children.append(pivot)

        if index:  # if we have a hierarchy
            return index[0]

        # looks like a pure mesh
        assert meshIndex, "Meshes required"
        scene = PivotWrapper(None)
        scene.mesh = list(meshIndex.values())[0]
        scene.name = scene.mesh.header.meshName
        scene.position = struct_w3d.Vector((0, 0, 0))
        scene.rotation = struct_w3d.Quaternion((0, 0, 0, 0))
        return scene

class Wrapper(object):
    _cache = {}

    @classmethod
    def wrap(Cls, wrapped):
        try:
            wrapper = Cls._cache[wrapped]
        except KeyError:
            wrapper = Cls._cache[wrapped] = Cls(wrapped)
        return wrapper

    def __init__(self, wrapped):
        self._wrapped = wrapped

    def __getattr__(self, key):
        return getattr(self._wrapped, key)
    def __getitem__(self, key):
        return self._wrapped[key]
    def __repr__(self):
        return '%s:%r' % (self.__class__.__name__, self._wrapped)

    @classmethod
    def wrappings(Cls):
        for wrapped in Cls._cache.values():
            if isinstance(wrapped, Cls):
                yield wrapped

class Face(object):
    def __init__(self, a, b, c, normal=None):
        self.a = a
        self.b = b
        self.c = c
        self.normal = normal
    def __repr__(self):
        return '<Face %s, %s, %s, normal=%s>' % (self.a, self.b, self.c, self.normal)
    def to_tuple(self, normals):
        return (
            16,
            self.a, self.b, self.c,
            normals.index(self.normal)
        )

class MeshWrapper(Wrapper):
    def uuid(self):
        return "DDA9AE26-MESH-UUID-%s" % self.header.meshName

    def to_json(self):

        faces = []
        normals = []
        for f in self.faces:
            faces.append(Face(*f.vertIds, f.normal))
            normals.append(f.normal)

        return {
            "uuid": self.uuid(),
            "type": "Geometry",
            "data": {
                "metadata": {
#                    "uvs": 1,
                    "vertices": len(self.verts),
#                    "bones": 0,
                    "faces": len(faces),
                    "normals": len(normals),
#                    "morphTargets": 0,
#                    "generator": "io_three",
#                    "version": 3,
#                    "materials": 1
                },
                "faces": [ item for face in faces for item in face.to_tuple(normals)],
                "normals": [ item for n in normals for item in n.to_tuple() ],
                "vertices": [ item for n in self.verts for item in n.to_tuple() ],
            },
        }

class PivotWrapper(Wrapper):
    def __init__(self, *args, **kwargs):
        super(PivotWrapper, self).__init__(*args, **kwargs)
        self.children = []
        self.mesh = None

    def uuid(self):
        return "DDA9AE26-PIVOT-UUID-%s" % self.name

    def to_json(self):
        data = {
            "name": self.name,
            "type": "Mesh" if self.mesh is not None else "Other",
            "uuid": self.uuid(),
            "matrix": [item for item in matrix4x4(self.position, self.rotation)],
            "visible": True,
            "children": [ pivot.to_json() for pivot in self.children ],
        }

        if self.mesh:
            data["geometry"] = self.mesh.uuid()

        return data


def matrix4x4(translation, rotation, scale=None):
    m = rotation.to_matrix().to_4x4()
    m[0][3] += translation.x
    m[1][3] += translation.y
    m[2][3] += translation.z
    for y in range(4):
        for x in range(4):
            yield m[x][y]
