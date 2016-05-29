from . import struct_w3d
from .reader import ReadLong, GetChunkSize, ReadMesh, ReadHierarchy, ReadAnimation, ReadCompressedAnimation, ReadHLod, ReadBox

import logging
logger = logging.getLogger("W3DModel.w3d")

from mathutils import Vector
def t(vec):
    return vec
    return Vector((vec.z, vec.y, vec.x))



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


    def as_threejs(self, texture_paths=[]):
        logger.debug("building threejs object...")

        if not self.hlod.header.modelName == self.hlod.header.HTreeName:
            raise NotImplementedError("hlod.header.modelName != hlod.header.HTreeName")

        mesh_index = { m.header.meshName: m for m in self.meshes }

        object_root = self.createHierarchyWrapper(self.hierarchy.pivots, self.meshes)

        materials = []
        textures = []

        logger.info("Threejs object built")

        _object = object_root.to_json()

        for image in ImageWrapper.wrappings():
            image.fix_file(texture_paths=texture_paths)

        for image in ImageWrapper.wrappings():
            image.export(ext=".jpg", folder="textures")

        data = {
            "images": [ image.to_json() for image in ImageWrapper.wrappings() if image.ready() ],
            "animations": [],
            "object": _object,
            "textures": [ texture.to_json() for texture in TextureWrapper.wrappings() if texture.ready() ],
            "metadata": {},
            "geometries": [ mesh.to_json() for mesh in MeshWrapper.wrappings() ],
            "materials": [ material.to_json() for material in MaterialWrapper.wrappings() ]
        }

        if 0:
            data["materials"].append({
                    "emissive": 0,
                    "type": "MeshPhongMaterial",
                    "name": "zzbuildingsizeMaterial",
                    "ambient": 11579568,
                    "blending": "NormalBlending",
                    "uuid": "A4EB44DB-19EB-3E46-858B-2C653E96438F",
                    "vertexColors": False,
                    "depthWrite": True,
                    "side": 2,
                    "map": "1DED9F78-5CC5-39D4-A1BA-E382B36BBEF6",
                    "shininess": 50,
                    "specular": 0,
                    "depthTest": True,
                    "color": 11579568
                })

            data["textures"].append({
                    "magFilter": 1006,
                    "name": "zzbuildingsize_dds_jpg",
                    "wrap": [1000,1000],
                    "mapping": 300,
                    "minFilter": 1008,
                    "image": "0335B7DD-379B-3768-B834-4C9A343293D3",
                    "anisotropy": 1,
                    "uuid": "1DED9F78-5CC5-39D4-A1BA-E382B36BBEF6",
                    "repeat": [1,1]
                })

            data["images"].append({
                    "url": "zzbuildingsize.64x64.jpg",
                    "uuid": "0335B7DD-379B-3768-B834-4C9A343293D3",
                    "name": "zzbuildingsize.64x64.jpg"
                })

        return data

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
    def wrap(Cls, wrapped, *args, **kwargs):
        try:
            wrapper = Cls._cache[wrapped]
        except KeyError:
            wrapper = Cls._cache[wrapped] = Cls(wrapped, *args, **kwargs)
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
        self.uvs = []
    def __repr__(self):
        return '<Face %s, %s, %s, normal=%s>' % (self.a, self.b, self.c, self.normal)
    def to_tuple(self, normals, uvs):
        type = 0
        normal = uv = material = ()
        if self.normal:
            type += 1 << 4
            normal = (normals.index(self.normal),)
        if self.uvs:
            assert len(self.uvs) == 1
            type += 1 << 3
            uv = tuple( uvs.index(vec) for vec in self.uvs[0] )
            type += 1 << 1
            material = (0,)

        return (type,) + (self.a, self.b, self.c) + material + uv + normal

class MeshWrapper(Wrapper):
    def __init__(self, *args, **kwargs):
        super(MeshWrapper, self).__init__(*args, **kwargs)
        self.materials = []

    def uuid(self):
        return "DDA9AE26-MESH-UUID-%s" % self.header.meshName

    def to_json(self):

        faces = []
        normals = []
        uvs = []
        for f in self.faces:
            faces.append(Face(*f.vertIds, f.normal))
            normals.append(f.normal)

        assert len(self.matlPass.vmIds) >= 1, self.header.meshName

        if self.matlPass.vmIds != [0]:
            logger.warn("%s: Multitexture isn't supported yet, just using first" % self.header.meshName)
#        assert self.matlPass.vmIds == [0], self.header.meshName  # just one material is currently supported

        if len(self.matlPass.txStage.txCoords)>0:
            for face in faces:
                uv = [
                    self.matlPass.txStage.txCoords[face.a],  # Tuple
                    self.matlPass.txStage.txCoords[face.b],
                    self.matlPass.txStage.txCoords[face.c]
                ]
                face.uvs.append(uv)
                uvs.extend(uv)

        data = {
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
                "faces": [ item for face in faces for item in face.to_tuple(normals, uvs)],
                "normals": [ item for n in normals for item in t(n).to_tuple() ],
                "vertices": [ item for n in self.verts for item in t(n).to_tuple() ],
            },
        }
        if uvs:
            data["data"]["metadata"]["uvs"] = 1
            data["data"]["uvs"] = [ [ x for vec in uvs for x in vec ] ]

        return data


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
            "matrix": [item for item in matrix4x4(t(self.position), self.rotation)],
            "visible": True,
            "children": [ pivot.to_json() for pivot in self.children ],
        }

        if self.mesh:
            data["geometry"] = self.mesh.uuid()
            data["material"] = createMaterial(self.mesh)

        return data

def createMaterial(mesh):
    assert len(mesh.vertMatls), mesh.header.meshName
#    assert len(mesh.textures), mesh.header.meshName
    assert len(mesh.vertMatls) >= 1, mesh.vertMatls
#    assert len(mesh.textures) >= 1, mesh.textures
    vertMatl = mesh.vertMatls[0]

    names = [ matl.vmName for matl in mesh.vertMatls ] + [ tx.name for tx in mesh.textures ]

    material = MaterialWrapper.wrap("-".join(names))

    if mesh.textures:
        texture = mesh.textures[0]
        material.texture = TextureWrapper.wrap(texture.name)
    material.vertMatl = vertMatl

    return material.uuid()

class MaterialWrapper(Wrapper):
    _cache = {}
    def __init__(self, *args, **kwargs):
        super(MaterialWrapper, self).__init__(*args, **kwargs)
        self.name = self._wrapped
        self._wrapped = None
        self.texture = None
        self.vertMatl = None

    def uuid(self):
        return self.name + "-Material"

    def to_json(self):
        data = {
            "uuid": self.uuid(),
            "type": "MeshPhongMaterial",

            "doubleSided": False,
            "shading": "phong",
            "blending": "NormalBlending",

            "opacity": self.vertMatl.vmInfo.opacity,
            "shininess": self.vertMatl.vmInfo.shininess,

#            "diffuse": rgba_to_hex(self.vertMatl.vmInfo.diffuse),  # TODO: wrong numbers ??
#            "ambient": rgba_to_hex(self.vertMatl.vmInfo.ambient),  # TODO: wrong numbers ??
            "specular": rgba_to_hex(self.vertMatl.vmInfo.specular),  # TODO: wrong numbers ??
            "emissive": rgba_to_hex(self.vertMatl.vmInfo.emissive),  # TODO: wrong numbers ??
        }

        if self.texture:
            if self.texture.ready():
                data["map"] = self.texture.ref()
            else:
                logger.warn("%s: texture isn't ready" % self.uuid())

        return data

class TextureWrapper(Wrapper):
    _cache = {}
    def __init__(self, *args, **kwargs):
        super(TextureWrapper, self).__init__(*args, **kwargs)
        self.name = self._wrapped
        self._wrapped = None
        self.image = ImageWrapper.wrap(self.name)

    def ref(self):
        return self.name + "-Texture"

    def to_json(self):
        data = {
            "uuid": self.ref(),
            "name": self.name,
#            "anisotropy": 1,
        }
        if self.image.ready():
            data["image"] = self.image.ref()
        else:
            logger.warn("%s: image isn't ready" % self.ref())
        return data

    def ready(self):
        return self.image.ready()

class ImageWrapper(Wrapper):
    _cache = {}
    def __init__(self, *args, **kwargs):
        super(ImageWrapper, self).__init__(*args, **kwargs)
        self.name = self._wrapped
        self._wrapped = None
        self.url = None
        self.error = None

    def ref(self):
        return self.name + "-Image"

    def to_json(self):
        data = {
            "uuid": self.ref(),
            "name": self.name,
        }
        if self.ready():
            data["url"] = self.url
        return data

    def ready(self):
        return self.error is None

    def fix_file(self, texture_paths=[]):
        logger.debug(texture_paths)
        import os.path
        path, ext = os.path.splitext(self.name.lower())
        for e in [ext] + [".dds", ".tga"]:
            for root in texture_paths:
                logger.debug("test: %s" % os.path.join(root, path+e))
                if os.path.exists(os.path.join(root, path+e)):
                    path = os.path.join(root, path)
                    ext = e
                    self.url = os.path.relpath("%s%s" % (path, ext), root)
                    self.root = root
                    logger.debug("found: %s" % self.url)
                    return
        raise FileNotFoundError(self.name)

    def export(self, ext=".jpg", folder="."):
        import os.path
        path, e = os.path.splitext(self.url)

        if e == ".jpg":
            pass
        elif e == ".dds":
            to_url = os.path.join(folder, self.url+".jpg")

            folder, a = os.path.split(to_url)
            try:
                os.makedirs(folder)
            except FileExistsError:
                pass

            try:
                logger.debug("convert: %s" % self.url)
                from .dds import DDS
                im = DDS(os.path.join(self.root, self.url))
                im.save(to_url)
                self.url = to_url
            except ValueError as e:
                logger.exception("Couldn't convert image - skipping...")
                self.error = e
        else:
            raise NotSupportedError(e)


class __MaterialWrapper(Wrapper):
    def __init__(self, *args, **kwargs):
        super(MaterialWrapper, self).__init__(*args, **kwargs)
#        self.shaders = shaders
#        self.children = []
#        self.mesh = None

    def uuid(self):
        return self.vmName + "Material"

    def to_json(self):
        data = {
#            "emissive": 0,
            "type": "MeshPhongMaterial",
#            "name": "zzbuildingsizeMaterial",
#            "ambient": 11579568,
#            "blending": "NormalBlending",
            "uuid": self.uuid(),
#            "vertexColors": False,
#            "depthWrite": True,
#            "side": 2,
            "map": "1DED9F78-5CC5-39D4-A1BA-E382B36BBEF6",
#            "shininess": 50,
#            "specular": 0,
#            "depthTest": True,
#            "color": 11579568
        }

        return data

    """
    def to_mesh_json(self, mesh):
        data = {
                "DbgIndex": 0,
                "DbgName": self.uuid(),
                "DbgColor": 15658734,
                "blending": "NormalBlending",
                "visible": True,

                "transparent": False,

                "opacity": self.vmInfo.opacity,
                "doubleSided": False,
                "shading": "phong",
                "mapDiffuseAnisotropy": 1,
                "mapDiffuseRepeat": [1,1],
#                    "mapDiffuse": "zzbuildingsize.64x64.jpg",
#                    "mapDiffuseWrap": ["RepeatWrapping","RepeatWrapping"],
                "depthTest": True,
                "depthWrite": True,
                "wireframe": False,
                "specularCoef": 50,
                "__colorDiffuse": [0.690196, 0.690196, 0.690196],
                "colorDiffuse": rgba_to_rgbtuple(self.vmInfo.diffuse),  # TODO: wrong numbers ??

                "__colorAmbient": [0.690196, 0.690196, 0.690196],
                "colorAmbient": rgba_to_rgbtuple(self.vmInfo.ambient),  # TODO: wrong numbers ??

                "__colorSpecular": [0.001176, 0.001176, 0.001176],
                "colorSpecular": rgba_to_rgbtuple(self.vmInfo.specular),  # TODO: wrong numbers ??

                "__colorEmissive": [0, 0, 0],
                "colorEmissive": rgba_to_rgbtuple(self.vmInfo.emissive),  # TODO: wrong numbers ??
                "foooo": "bar",
            }

        if len(mesh.shaders) > 0:
            if mesh.shaders[0].alphaTest == 1:
                raise NotImplementedError("shader.alphaTest")
#                mat.use_transparency = True
#                mat.transparency_method = "Z_TRANSPARENCY"
            if mesh.shaders[0].destBlend == 1:
                raise NotImplementedError("shader.destBlend")
#                mat.use_transparency = True
#                mat.transparency_method = "Z_TRANSPARENCY"
#                destBlend = 1


#        if not mesh.bumpMaps.normalMap.entryStruct.normalMap == "":
#            raise NotImplementedError("Material.bumpMaps")

        return data
"""


def matrix4x4(translation, rotation, scale=None):
    m = rotation.to_matrix().to_4x4()
    m[0][3] += translation.x
    m[1][3] += translation.y
    m[2][3] += translation.z
    for y in range(4):
        for x in range(4):
            yield m[x][y]


def rgba_to_hex(color):
    # MAYBE: https://github.com/mrdoob/three.js/blob/master/src/math/Color.js#L273 ?????
    return color.b + (color.g << 8) + (color.r << 16)
