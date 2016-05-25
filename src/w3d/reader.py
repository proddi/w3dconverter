import sys
import struct
from mathutils import Vector, Quaternion
from . import struct_w3d


import logging
logger = logging.getLogger("reader.w3d")


#######################################################################################
# Basic Methods
#######################################################################################

def ReadString(file):
    bytes = []
    b = file.read(1)
    while ord(b)!=0:
        bytes.append(b)
        b = file.read(1)
    return (b"".join(bytes)).decode("utf-8")

def ReadFixedString(file):
    SplitString = ((str(file.read(16)))[2:18]).split("\\")
    return SplitString[0]

def ReadLongFixedString(file):
    SplitString = ((str(file.read(32)))[2:34]).split("\\")
    return SplitString[0]

def ReadRGBA(file):
    return struct_w3d.RGBA(r=ord(file.read(1)), g=ord(file.read(1)), b=ord(file.read(1)), a=ord(file.read(1)))

def GetChunkSize(data):
    return (data & 0x7FFFFFFF)

def ReadLong(file):
    #binary_format = "<l" long
    return (struct.unpack("<L", file.read(4))[0])

def ReadShort(file):
    #binary_format = "<h" short
    return (struct.unpack("<H", file.read(2))[0])

def ReadUnsignedShort(file):
    return (struct.unpack("<h", file.read(2))[0])

def ReadLongArray(file,chunkEnd):
    LongArray = []
    while file.tell() < chunkEnd:
        LongArray.append(ReadLong(file))
    return LongArray

def ReadFloat(file):
    #binary_format = "<f" float
    return (struct.unpack("f", file.read(4))[0])

def ReadSignedByte(file):
    return (struct.unpack("<b", file.read(1))[0])

def ReadUnsignedByte(file):
    return (struct.unpack("<B", file.read(1))[0])

def ReadVector(file):
    return Vector((ReadFloat(file), ReadFloat(file), ReadFloat(file)))

def ReadQuaternion(file):
    quat = (ReadFloat(file), ReadFloat(file), ReadFloat(file), ReadFloat(file))
    #change order from xyzw to wxyz
    return Quaternion((quat[3], quat[0], quat[1], quat[2]))

def ReadCompressedQuaternion(file, faktor):
    quat = (ReadSignedByte(file) / faktor, ReadSignedByte(file) / faktor, ReadSignedByte(file) / faktor, ReadSignedByte(file) / faktor)
    #change order from xyzw to wxyz
    return Quaternion((quat[3], quat[0], quat[1], quat[2]))

def GetVersion(data):
    return struct_w3d.Version(major = (data)>>16, minor = (data) & 0xFFFF)

#######################################################################################
# Hierarchy
#######################################################################################

def ReadHierarchyHeader(file):
    HierarchyHeader = struct_w3d.HierarchyHeader()
    HierarchyHeader.version = GetVersion(ReadLong(file))
    HierarchyHeader.name = ReadFixedString(file)
    HierarchyHeader.pivotCount = ReadLong(file)
    HierarchyHeader.centerPos = ReadVector(file)
    return HierarchyHeader

def ReadPivots(file, chunkEnd):
    pivots = []
    while file.tell() < chunkEnd:
        pivot = struct_w3d.HierarchyPivot()
        pivot.name = ReadFixedString(file)
        pivot.parentID = ReadLong(file)
        pivot.position = ReadVector(file)
        pivot.eulerAngles = ReadVector(file)
        pivot.rotation = ReadQuaternion(file)
        pivots.append(pivot)
    return pivots

# if the exported pivots are corrupted these fixups are used
def ReadPivotFixups(file, chunkEnd):
    pivot_fixups = []
    while file.tell() < chunkEnd:
        pivot_fixup = ReadVector(file)
        pivot_fixups.append(pivot_fixup)
    return pivot_fixups

def ReadHierarchy(file, chunkEnd):
    #print("\n### NEW HIERARCHY: ###")
    HierarchyHeader = struct_w3d.HierarchyHeader()
    Pivots = []
    Pivot_fixups = []
    while file.tell() < chunkEnd:
        chunkType = ReadLong(file)
        chunkSize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + chunkSize
        if chunkType == 257:
            HierarchyHeader = ReadHierarchyHeader(file)
            #print("Header")
        elif chunkType == 258:
            Pivots = ReadPivots(file, subChunkEnd)
            #print("Pivots")
        elif chunkType == 259:
            Pivot_fixups = ReadPivotFixups(file, subChunkEnd)
            #print("PivotFixups")
        else:
            logger.error("unknown chunktype in Hierarchy: %s" % chunkType)
            file.seek(chunkSize, 1)
    return struct_w3d.Hierarchy(header = HierarchyHeader, pivots = Pivots, pivot_fixups = Pivot_fixups)

#######################################################################################
# Animation
#######################################################################################

def ReadAnimationHeader(file):
    return struct_w3d.AnimationHeader(version = GetVersion(ReadLong(file)), name = ReadFixedString(file),
        hieraName = ReadFixedString(file), numFrames = ReadLong(file), frameRate = ReadLong(file))

def ReadAnimationChannel(file, chunkEnd):
#    print("Channel")
    FirstFrame = ReadShort(file)
    LastFrame = ReadShort(file)
    VectorLen = ReadShort(file)
    Type = ReadShort(file)
    Pivot = ReadShort(file)
    Pad = ReadShort(file)
    Data = []
    if VectorLen == 1:
        while file.tell() < chunkEnd:
            Data.append(ReadFloat(file))
    elif VectorLen == 4:
        while file.tell() < chunkEnd:
            Data.append(ReadQuaternion(file))
    else:
        logger.error("!!!unsupported vector len %s" % VectorLen)
        while file.tell() < chunkEnd:
            file.read(1)
    return struct_w3d.AnimationChannel(firstFrame = FirstFrame, lastFrame = LastFrame, vectorLen = VectorLen,
        type = Type, pivot = Pivot, pad = Pad, data = Data)

def ReadAnimation(file, chunkEnd):
#    print("\n### NEW ANIMATION: ###")
    Header = struct_w3d.AnimationHeader()
    Channels = []
    while file.tell() < chunkEnd:
        chunkType = ReadLong(file)
        chunkSize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + chunkSize
        if chunkType == 513:
            Header = ReadAnimationHeader(file)
        elif chunkType == 514:
            Channels.append(ReadAnimationChannel(file, subChunkEnd))
        else:
            logger.error("unknown chunktype in Animation: %s" % chunkType)
            file.seek(chunkSize, 1)
    return struct_w3d.Animation(header = Header, channels = Channels)


def ReadCompressedAnimationHeader(file):
    return struct_w3d.CompressedAnimationHeader(version = GetVersion(ReadLong(file)), name = ReadFixedString(file),
        hieraName = ReadFixedString(file), numFrames = ReadLong(file), frameRate = ReadShort(file), flavor = ReadShort(file))

def ReadTimeCodedAnimationChannel(file, chunkEnd): # bfme I animation struct
    TimeCodesCount = ReadLong(file)
    Pivot = ReadShort(file)
    VectorLen = ReadUnsignedByte(file)
    Type = ReadUnsignedByte(file)
    TimeCodedKeys = []

    while file.tell() < chunkEnd:
        Key = struct_w3d.TimeCodedAnimationKey()
        Key.frame = ReadLong(file)
        if Type == 6:
            Key.value = ReadQuaternion(file)
        else:
            Key.value = ReadFloat(file)
        TimeCodedKeys.append(Key)
    return struct_w3d.TimeCodedAnimationChannel(timeCodesCount = TimeCodesCount, pivot = Pivot, vectorLen = VectorLen, type = Type,
        timeCodedKeys = TimeCodedKeys)

def ReadTimeCodedBitChannel(file, chunkEnd): #-- channel of boolean values (e.g. visibility) - always size 16
    TimeCodesCount = ReadLong(file)
    Pivot = ReadShort(file)
    Type = ReadUnsignedByte(file) #0 = vis, 1 = timecoded vis
    DefaultValue = ReadUnsignedByte(file)
    print(TimeCodesCount, Pivot, Type, DefaultValue)
    values = []

    #8 bytes left
    while file.tell() < chunkEnd:
        # dont yet know how to interpret this data
        print(ReadUnsignedByte(file))

##test function
def FromSageFloat16(s):
    return ((s >> 8) * 10.0 + (s & 255) * 9.96000003814697 / 256.0);
#return (float) ((double) (byte) ((uint) v >> 8) * 10.0 + (double) (byte) ((uint) v & (uint) byte.MaxValue) * 9.96000003814697 / 256.0);

def ReadTimeCodedAnimationVector(file, chunkEnd):
    CompressionType = ReadShort(file) #0 or 256 or 512 -> 0, 8 or 16 bit
    VectorLen = ReadUnsignedByte(file)
    Type = ReadUnsignedByte(file) #is x or y or z or quat  #what is type 15?? (vecLen = 1)
    TimeCodesCount = ReadShort(file)
    Pivot = ReadShort(file)
    TimeCodedKeys = []

    if CompressionType == 0:
        if Type == 6:
            while file.tell() <= chunkEnd - 18: # 20:1 36:2 56:3 72:4 92:5 108:6 128:7 144:8 164:9 180:10 200:11 216:12   (18 + 2)
                #print(ReadShort(file) | 0x8000)
                #print(ReadUnsignedByte(file))
                #print(ReadUnsignedByte(file))
                #print(ReadShort(file))
                #print(ReadQuaternion(file))
                #print(ReadLong(file))
                file.read(18)
            if file.tell() < chunkEnd:
                file.read(2) #padding (2 bytes if the TimeCodesCount is uneven)
        else:
            while file.tell() <= chunkEnd - 6: # 8:1 32:5 56:9  (6 + 2)
                #Data.append(ReadShort(file)) #still some weird values in here
                #Data.append(ReadFloat(file))
                print(ReadShort(file))#| 0x80000000)
                print(ReadFloat(file))
                #print(FromSageFloat16(ReadShort(file)))
                #file.read(2)
            if file.tell() < chunkEnd:
                file.read(2) #padding (2 bytes if the TimeCodesCount is uneven)

    #elif CompressionType == 256:
    #    if Type == 6:
    #        while file.tell() < chunkEnd: # 56:16 (92:21 92:30) (128:36 128:40 128:45) (200:66 200:75) (236:84 236:90) 308:117 344:144 380:157
    #            #print(ReadUnsignedByte(file) & 0xFFFF)
    #            #file.read(4)
    #            print(FromSageFloat16(ReadShort(file)))
    #            #print(ReadSignedByte(file)/255)
    #            #print(ReadSignedByte(file)/255)
    #            #print(ReadSignedByte(file)/255)
    #    else:
    #        while file.tell() < chunkEnd: # 17:16 26:21 (35:36 35:45) 62:90 71:100 89:144
    #            file.read(1)

    #elif CompressionType == 512:
    #    if Type == 6:
    #        while file.tell() < chunkEnd: # (156:21 156:30) 224:45 292:64 (360:66 360:72)
    #            file.read(1)
    #    else:
    #        #print("512 compressed vec")
    #        #print(TimeCodesCount)
    #        while file.tell() < chunkEnd: # 25:16 59:42 (93:66 93:75) 110:90
    #            file.read(1)

    while file.tell() < chunkEnd:
            file.read(1)

    #return struct_w3d.TimeCodedAnimationVector(magicNum = CompressionType, vectorLen = VectorLen, type = Type,
    #   timeCodesCount = TimeCodesCount, pivot = Pivot, timeCodedKeys = TimeCodedKeys)

def ReadCompressedAnimation(file, chunkEnd):
    print("\n### NEW COMPRESSED ANIMATION: ###")
    Header = struct_w3d.CompressedAnimationHeader()
    Channels = []
    Vectors = []
    while file.tell() < chunkEnd:
        chunkType = ReadLong(file)
        chunkSize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + chunkSize
        if chunkType == 641:
            Header = ReadCompressedAnimationHeader(file)
            print("#### numFrames %s" % Header.numFrames)
            print("##Flavor %s" % Header.flavor)
        elif chunkType == 642:
            Channels.append(ReadTimeCodedAnimationChannel(file, subChunkEnd))
        elif chunkType == 643:
            #print("### size: %s" % chunkSize)
            #ReadTimeCodedBitChannel(file, subChunkEnd)
            print("not implemented yet")
            file.seek(chunkSize, 1)
        elif chunkType == 644:
            #print("####size %s" % (chunkSize - 8))
            #Vectors.append(ReadTimeCodedAnimationVector(file, subChunkEnd))
            print("not implemented yet")
            file.seek(chunkSize, 1)
        else:
            logger.error("unknown chunktype in CompressedAnimation: %s" % chunkType)
            file.seek(chunkSize, 1)
    return struct_w3d.CompressedAnimation(header = Header, channels = Channels, vectors = Vectors)

#######################################################################################
# HLod
#######################################################################################

def ReadHLodHeader(file):
    HLodHeader = struct_w3d.HLodHeader()
    HLodHeader.version = GetVersion(ReadLong(file))
    HLodHeader.lodCount = ReadLong(file)
    HLodHeader.modelName = ReadFixedString(file)
    HLodHeader.HTreeName = ReadFixedString(file)
    return HLodHeader

def ReadHLodArrayHeader(file):
    HLodArrayHeader = struct_w3d.HLodArrayHeader()
    HLodArrayHeader.modelCount = ReadLong(file)
    HLodArrayHeader.maxScreenSize = ReadFloat(file)
    return HLodArrayHeader

def ReadHLodSubObject(file):
    HLodSubObject = struct_w3d.HLodSubObject()
    HLodSubObject.boneIndex = ReadLong(file)
    HLodSubObject.name = ReadLongFixedString(file)
    return HLodSubObject

def ReadHLodArray(file, chunkEnd):
    HLodArrayHeader = struct_w3d.HLodArrayHeader()
    HLodSubObjects = []
    while file.tell() < chunkEnd:
        chunkType = ReadLong(file)
        chunkSize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + chunkSize
        if chunkType == 1795:
            HLodArrayHeader = ReadHLodArrayHeader(file)
        elif chunkType == 1796:
            HLodSubObjects.append(ReadHLodSubObject(file))
        else:
            logger.error("unknown chunktype in HLodArray: %s" % chunkType)
            file.seek(chunkSize, 1)
    return struct_w3d.HLodArray(header = HLodArrayHeader, subObjects = HLodSubObjects)

def ReadHLod(file, chunkEnd):
    #print("\n### NEW HLOD: ###")
    HLodHeader = struct_w3d.HLodHeader()
    HLodArray = struct_w3d.HLodArray()
    while file.tell() < chunkEnd:
        chunkType = ReadLong(file)
        chunkSize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + chunkSize
        if chunkType == 1793:
            HLodHeader = ReadHLodHeader(file)
            #print("Header")
        elif chunkType == 1794:
            HLodArray = ReadHLodArray(file, subChunkEnd)
            #print("HLodArray")
        else:
            logger.error("unknown chunktype in HLod: %s" % chunkType)
            file.seek(chunkSize, 1)
    return struct_w3d.HLod(header = HLodHeader, lodArray = HLodArray)

#######################################################################################
# Box
#######################################################################################

def ReadBox(file):
    #print("\n### NEW BOX: ###")
    version = GetVersion(ReadLong(file))
    attributes = ReadLong(file)
    name = ReadLongFixedString(file)
    color = ReadRGBA(file)
    center = ReadVector(file)
    extend = ReadVector(file)
    return struct_w3d.Box(version = version, attributes = attributes, name = name, color = color, center = center, extend = extend)

#######################################################################################
# Texture
#######################################################################################

def ReadTexture(file, chunkEnd):
    tex = struct_w3d.Texture()
    while file.tell() < chunkEnd:
        Chunktype = ReadLong(file)
        Chunksize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + Chunksize
        if Chunktype == 50:
            tex.name = ReadString(file)
        elif Chunktype == 51:
            tex.textureInfo = struct_w3d.TextureInfo(attributes = ReadShort(file),
                animType = ReadShort(file), frameCount = ReadLong(file), frameRate = ReadFloat(file))
        else:
            logger.error("unknown chunktype in Texture: %s" % chunkType)
            file.seek(Chunksize,1)
    return tex

def ReadTextureArray(file, chunkEnd):
    textures = []
    while file.tell() < chunkEnd:
        Chunktype = ReadLong(file)
        Chunksize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + Chunksize
        if Chunktype == 49:
            textures.append(ReadTexture(file, subChunkEnd))
        else:
            logger.error("unknown chunktype in TextureArray: %s" % chunkType)
            file.seek(Chunksize, 1)
    return textures

#######################################################################################
# Material
#######################################################################################

def ReadMeshTextureCoordArray(file, chunkEnd):
    txCoords = []
    while file.tell() < chunkEnd:
        txCoords.append((ReadFloat(file), ReadFloat(file)))
    return txCoords

def ReadMeshTextureStage(file, chunkEnd):
    TextureIds = []
    TextureCoords = []
    while file.tell() < chunkEnd:
        chunkType = ReadLong(file)
        chunkSize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + chunkSize
        if chunkType == 73:
            TextureIds = ReadLongArray(file, subChunkEnd)
        elif chunkType == 74:
            TextureCoords = ReadMeshTextureCoordArray(file, subChunkEnd)
        else:
            logger.error("unknown chunktype in MeshTextureStage: %s" % chunkType)
            file.seek(chunkSize,1)
    return struct_w3d.MeshTextureStage(txIds = TextureIds, txCoords = TextureCoords)

def ReadMeshMaterialPass(file, chunkEnd):
    # got two different types of material passes depending on if the mesh has bump maps of not
    VertexMaterialIds = []
    ShaderIds = []
    DCG =  []
    TextureStage = struct_w3d.MeshTextureStage()
    while file.tell() < chunkEnd:
        chunkType = ReadLong(file)
        chunkSize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + chunkSize
        if chunkType == 57: #Vertex Material Ids
            VertexMaterialIds = ReadLongArray(file, subChunkEnd)
        elif chunkType == 58:#Shader Ids
            ShaderIds = ReadLongArray(file, subChunkEnd)
        elif chunkType == 59:#vertex colors
            while file.tell() < subChunkEnd:
                DCG.append(ReadRGBA(file))
        elif chunkType == 63:# dont know what this is -> size is always 4 and value 0
            #print("<<< unknown Chunk 63 >>>")
            file.seek(chunkSize, 1)
        elif chunkType == 72: #Texture Stage
            TextureStage = ReadMeshTextureStage(file, subChunkEnd)
        elif chunkType == 74: #Texture Coords
            TextureStage.txCoords = ReadMeshTextureCoordArray(file, subChunkEnd)
        else:
            logger.error("unknown chunktype in MeshMaterialPass: %s" % chunkType)
            file.seek(chunkSize, 1)
    return struct_w3d.MeshMaterialPass(vmIds = VertexMaterialIds, shaderIds = ShaderIds, dcg = DCG, txStage = TextureStage)

def ReadMaterial(file, chunkEnd):
    mat = struct_w3d.MeshMaterial()
    while file.tell() < chunkEnd:
        chunkType = ReadLong(file)
        chunkSize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + chunkSize
        if chunkType == 44:
            mat.vmName = ReadString(file)
        elif chunkType == 45:
            vmInf = struct_w3d.VertexMaterial()
            vmInf.attributes = ReadLong(file)
            vmInf.ambient = ReadRGBA(file)
            vmInf.diffuse = ReadRGBA(file)
            vmInf.specular = ReadRGBA(file)
            vmInf.emissive = ReadRGBA(file)
            vmInf.shininess = ReadFloat(file)
            vmInf.opacity = ReadFloat(file)
            vmInf.translucency = ReadFloat(file)
            mat.vmInfo = vmInf
        elif chunkType == 46:
            mat.vmArgs0 = ReadString(file)
        elif chunkType == 47:
            mat.vmArgs1 = ReadString(file)
        else:
            logger.error("unknown chunktype in Material: %s" % chunkType)
            file.seek(chunkSize,1)
    return mat

def ReadMeshMaterialArray(file, chunkEnd):
    Mats = []
    while file.tell() < chunkEnd:
        chunkType = ReadLong(file)
        chunkSize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell()+chunkSize
        if chunkType == 43:
            Mats.append(ReadMaterial(file, subChunkEnd))
        else:
            logger.error("unknown chunktype in MeshMaterialArray: %s" % chunkType)
            print("!!!unknown chunktype in MeshMaterialArray: %s" % chunkType)
            file.seek(chunkSize,1)
    return Mats

def ReadMeshMaterialSetInfo (file):
    result = struct_w3d.MeshMaterialSetInfo(passCount = ReadLong(file), vertMatlCount = ReadLong(file),
        shaderCount = ReadLong(file), textureCount = ReadLong(file))
    return result

#######################################################################################
# Vertices
#######################################################################################

def ReadMeshVerticesArray(file, chunkEnd):
    verts = []
    while file.tell() < chunkEnd:
        verts.append(ReadVector(file))
    return verts

def ReadMeshVertexInfluences(file, chunkEnd):
    vertInfs = []
    while file.tell()  < chunkEnd:
        vertInf = struct_w3d.MeshVertexInfluences()
        vertInf.boneIdx = ReadShort(file)
        vertInf.xtraIdx = ReadShort(file)
        vertInf.boneInf = ReadShort(file)/100
        vertInf.xtraInf = ReadShort(file)/100
        vertInfs.append(vertInf)
    return vertInfs

#######################################################################################
# Faces
#######################################################################################

def ReadMeshFace(file):
    result = struct_w3d.MeshFace(vertIds = (ReadLong(file), ReadLong(file), ReadLong(file)),
    attrs = ReadLong(file),
    normal = ReadVector(file),
    distance = ReadFloat(file))
    return result

def ReadMeshFaceArray(file, chunkEnd):
    faces = []
    while file.tell() < chunkEnd:
        faces.append(ReadMeshFace(file))
    return faces

#######################################################################################
# Shader
#######################################################################################

def ReadMeshShaderArray(file, chunkEnd):
    shaders = []
    while file.tell() < chunkEnd:
        shader = struct_w3d.MeshShader()
        shader.depthCompare = ReadUnsignedByte(file)
        shader.depthMask = ReadUnsignedByte(file)
        shader.colorMask = ReadUnsignedByte(file)
        shader.destBlend = ReadUnsignedByte(file)
        shader.fogFunc = ReadUnsignedByte(file)
        shader.priGradient = ReadUnsignedByte(file)
        shader.secGradient = ReadUnsignedByte(file)
        shader.srcBlend = ReadUnsignedByte(file)
        shader.texturing = ReadUnsignedByte(file)
        shader.detailColorFunc = ReadUnsignedByte(file)
        shader.detailAlphaFunc = ReadUnsignedByte(file)
        shader.shaderPreset = ReadUnsignedByte(file)
        shader.alphaTest = ReadUnsignedByte(file)
        shader.postDetailColorFunc = ReadUnsignedByte(file)
        shader.postDetailAlphaFunc = ReadUnsignedByte(file)
        shader.pad = ReadUnsignedByte(file)
        shaders.append(shader)
    return shaders

#######################################################################################
# Bump Maps
#######################################################################################

def ReadNormalMapHeader(file, chunkEnd):
    number = ReadSignedByte(file)
    typeName = ReadLongFixedString(file)
    reserved = ReadLong(file)
    return struct_w3d.MeshNormalMapHeader(number = number, typeName = typeName, reserved = reserved)

def ReadNormalMapEntryStruct(file, chunkEnd, entryStruct):
    type = ReadLong(file) #1 texture, 2 bumpScale/ specularExponent, 5 color, 7 alphaTest
    size = ReadLong(file)
    name = ReadString(file)

    if name == "DiffuseTexture":
        entryStruct.unknown = ReadLong(file)
        entryStruct.diffuseTexName = ReadString(file)
    elif name == "NormalMap":
        entryStruct.unknown_nrm = ReadLong(file)
        entryStruct.normalMap = ReadString(file)
    elif name == "BumpScale":
        entryStruct.bumpScale = ReadFloat(file)
    elif name == "AmbientColor":
        entryStruct.ambientColor = (ReadFloat(file), ReadFloat(file), ReadFloat(file), ReadFloat(file))
    elif name == "DiffuseColor":
        entryStruct.diffuseColor = (ReadFloat(file), ReadFloat(file), ReadFloat(file), ReadFloat(file))
    elif name == "SpecularColor":
        entryStruct.specularColor = (ReadFloat(file), ReadFloat(file), ReadFloat(file), ReadFloat(file))
    elif name == "SpecularExponent":
        entryStruct.specularExponent = ReadFloat(file)
    elif name == "AlphaTestEnable":
        entryStruct.alphaTestEnable = ReadUnsignedByte(file)
    else:
        logger.error("unknown NormalMapEntryStruct: %s" % name)
        while file.tell() < chunkEnd:
            file.read(1)
    return entryStruct

def ReadNormalMap(file, chunkEnd):
    Header = struct_w3d.MeshNormalMapHeader()
    EntryStruct = struct_w3d.MeshNormalMapEntryStruct()
    while file.tell() < chunkEnd:
        Chunktype = ReadLong(file)
        Chunksize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + Chunksize
        if Chunktype == 82:
            Header = ReadNormalMapHeader(file, subChunkEnd)
        elif Chunktype == 83:
            EntryStruct = ReadNormalMapEntryStruct(file, subChunkEnd, EntryStruct)
        else:
            logger.error("unknown chunktype in NormalMap: %s" % chunkType)
            file.seek(Chunksize, 1)
    return struct_w3d.MeshNormalMap(header = Header, entryStruct = EntryStruct)

def ReadBumpMapArray(file, chunkEnd):
    NormalMap = struct_w3d.MeshNormalMap()
    while file.tell() < chunkEnd:
        Chunktype = ReadLong(file)
        Chunksize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + Chunksize
        if Chunktype == 81:
            NormalMap = ReadNormalMap(file, subChunkEnd)
        else:
            logger.error("unknown chunktype in BumpMapArray: %s" % chunkType)
            file.seek(Chunksize, 1)
    return struct_w3d.MeshBumpMapArray(normalMap = NormalMap)

#######################################################################################
# AABTree (Axis-aligned-bounding-box)
#######################################################################################

def ReadAABTreeHeader(file, chunkEnd):
    nodeCount = ReadLong(file)
    polyCount = ReadLong(file)
    #padding of the header
    while file.tell() < chunkEnd:
        file.read(4)
    return struct_w3d.AABTreeHeader(nodeCount = nodeCount, polyCount = polyCount)

def ReadAABTreePolyIndices(file, chunkEnd):
    polyIndices = []
    while file.tell() < chunkEnd:
        polyIndices.append(ReadLong(file))
    return polyIndices

def ReadAABTreeNodes(file, chunkEnd):
    nodes = []
    while file.tell() < chunkEnd:
        Min = ReadVector(file) # <-
        Max = ReadVector(file) # <- is mouse within these values
        FrontOrPoly0 = ReadLong(file)     # <- if true check these two
        BackOrPolyCount = ReadLong(file)   # <-
        # if within these, check their children
        #etc bis du irgendwann angekommen bist wos nur noch poly eintraege gibt dann hast du nen index und nen count parameter der dir sagt wo die polys die von dieser bounding box umschlossen sind liegen und wie viele es sind
        # die gehst du dann alle durch wo du halt einfach nen test machst ob deine position xyz in dem poly liegt oder ausserhalb
        nodes.append(struct_w3d.AABTreeNode(min = Min, max = Max, frontOrPoly0 = FrontOrPoly0, backOrPolyCount = BackOrPolyCount))
    return nodes

#Axis-Aligned-Bounding-Box tree
def ReadAABTree(file, chunkEnd):
    aabtree = struct_w3d.MeshAABTree()
    while file.tell() < chunkEnd:
        Chunktype = ReadLong(file)
        Chunksize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + Chunksize
        if Chunktype == 145:
            aabtree.header = ReadAABTreeHeader(file, subChunkEnd)
        elif Chunktype == 146:
            aabtree.polyIndices = ReadAABTreePolyIndices(file, subChunkEnd)
        elif Chunktype == 147:
            aabtree.nodes = ReadAABTreeNodes(file, subChunkEnd)
        else:
            logger.error("unknown chunktype in AABTree: %s" % chunkType)
            file.seek(Chunksize, 1)
    return aabtree

#######################################################################################
# Mesh
#######################################################################################

def ReadMeshHeader(file):
    result = struct_w3d.MeshHeader(version = GetVersion(ReadLong(file)), attrs =  ReadLong(file), meshName = ReadFixedString(file),
        containerName = ReadFixedString(file),faceCount = ReadLong(file),
        vertCount = ReadLong(file), matlCount = ReadLong(file), damageStageCount = ReadLong(file), sortLevel = ReadLong(file),
        prelitVersion = ReadLong(file), futureCount = ReadLong(file),
        vertChannelCount = ReadLong(file), faceChannelCount = ReadLong(file),
        #bounding volumes
        minCorner = ReadVector(file),
        maxCorner = ReadVector(file),
        sphCenter = ReadVector(file),
        sphRadius =  ReadFloat(file))
    return result

def ReadMesh(file, chunkEnd):
    MeshVerticesInfs = []
    MeshVertices = []
    MeshVerticesCopy = []
    MeshNormals = []
    MeshNormalsCopy = []
    MeshVerticeMats = []
    MeshHeader = struct_w3d.MeshHeader()
    MeshMaterialInfo = struct_w3d.MeshMaterialSetInfo()
    MeshFaces = []
    MeshMaterialPass = struct_w3d.MeshMaterialPass()
    MeshShadeIds = []
    MeshShaders = []
    MeshTextures = []
    MeshUsertext = ""
    MeshBumpMaps = struct_w3d.MeshBumpMapArray()
    MeshAABTree = struct_w3d.MeshAABTree()

    #print("\n### NEW MESH: ###")
    while file.tell() < chunkEnd:
        Chunktype = ReadLong(file)
        Chunksize = GetChunkSize(ReadLong(file))
        subChunkEnd = file.tell() + Chunksize

        if Chunktype == 2:
            MeshVertices = ReadMeshVerticesArray(file, subChunkEnd)
#            temp = 0
        elif Chunktype == 3072:
            MeshVerticesCopy = ReadMeshVerticesArray(file, subChunkEnd)

        elif Chunktype == 3:
            MeshNormals = ReadMeshVerticesArray(file, subChunkEnd)

        elif Chunktype == 3073:
            MeshNormalsCopy = ReadMeshVerticesArray(file, subChunkEnd)

        elif Chunktype == 12:
            MeshUsertext = ReadString(file)

        elif Chunktype == 14:
            MeshVerticesInfs = ReadMeshVertexInfluences(file, subChunkEnd)

        elif Chunktype == 31:
            MeshHeader = ReadMeshHeader(file)

        elif Chunktype == 32:
            MeshFaces = ReadMeshFaceArray(file, subChunkEnd)

        elif Chunktype == 34:
            MeshShadeIds = ReadLongArray(file, subChunkEnd)

        elif Chunktype == 40:
            MeshMaterialInfo = ReadMeshMaterialSetInfo(file)

        elif Chunktype == 41:
            MeshShaders = ReadMeshShaderArray(file, subChunkEnd)

        elif Chunktype == 42:
            MeshVerticeMats = ReadMeshMaterialArray(file, subChunkEnd)

        elif Chunktype == 48:
            MeshTextures = ReadTextureArray(file, subChunkEnd)

        elif Chunktype == 56:
            MeshMaterialPass = ReadMeshMaterialPass(file, subChunkEnd)

        elif Chunktype == 80:
            MeshBumpMaps = ReadBumpMapArray(file, subChunkEnd)

        elif Chunktype == 96:
            #seems to be a type of vertex normals occur only in combination with normal maps
            ReadMeshVerticesArray(file, subChunkEnd)

        elif Chunktype == 97:
            #seems to be a type of vertex normals occur only in combination with normal maps
            ReadMeshVerticesArray(file, subChunkEnd)

        elif Chunktype == 144:
            MeshAABTree = ReadAABTree(file, subChunkEnd)

        else:
            logger.error("Unknown chunktype in Mesh: %s" % Chunktype)
            file.seek(Chunksize,1)

    return struct_w3d.Mesh(header = MeshHeader, verts = MeshVertices, verts_copy = MeshVerticesCopy, normals = MeshNormals,
                normals_copy = MeshNormalsCopy, vertInfs = MeshVerticesInfs, faces = MeshFaces, userText = MeshUsertext,
                shadeIds = MeshShadeIds, matInfo = MeshMaterialInfo, shaders = MeshShaders, vertMatls = MeshVerticeMats,
                textures = MeshTextures, matlPass = MeshMaterialPass, bumpMaps = MeshBumpMaps, aabtree = MeshAABTree)

#######################################################################################
# loadTexture
#######################################################################################
"""
def LoadTexture(self, givenfilepath, mesh, texName, tex_type, destBlend):
    script_directory = os.path.dirname(os.path.abspath(__file__))
    default_tex = script_directory + "\default_tex.dds"

    found_img = False

    basename = os.path.splitext(texName)[0]

    #test if image file has already been loaded
    for image in bpy.data.images:
        if basename == os.path.splitext(image.name)[0]:
            img = image
            found_img = True

    # Create texture slot in material
    mTex = mesh.materials[0].texture_slots.add()
    mTex.use_map_alpha = True

    if found_img == False:
        tgapath = os.path.dirname(givenfilepath) + "/" + basename + ".tga"
        ddspath = os.path.dirname(givenfilepath) + "/" + basename + ".dds"
        img = None
        try:
            img = bpy.data.images.load(tgapath)
        except:
            try:
                img = bpy.data.images.load(ddspath)
            except:
                logger.error("Cannot load texture " + basename)
                print("!!! texture file not found " + basename)
                img = bpy.data.images.load(default_tex)

        cTex = bpy.data.textures.new(texName, type = 'IMAGE')
        cTex.image = img

        if destBlend == 0:
            cTex.use_alpha = True
        else:
            cTex.use_alpha = False

        if tex_type == "normal":
            cTex.use_normal_map = True
            cTex.filter_size = 0.1
            cTex.use_filter_size_min = True
        mTex.texture = cTex
    else:
        mTex.texture = bpy.data.textures[texName]

    mTex.texture_coords = 'UV'
    mTex.mapping = 'FLAT'
    if tex_type == "normal":
       mTex.normal_map_space = 'TANGENT'
       mTex.use_map_color_diffuse = False
       mTex.use_map_normal = True
       mTex.normal_factor = 1.0
       mTex.diffuse_color_factor = 0.0
"""
#######################################################################################
# loadSkeleton
#######################################################################################
"""
def LoadSKL(self, sklpath):
    #print("\n### SKELETON: ###")
    Hierarchy = struct_w3d.Hierarchy()
    file = open(sklpath, "rb")
    file.seek(0,2)
    filesize = file.tell()
    file.seek(0,0)

    while file.tell() < filesize:
        chunkType = ReadLong(file)
        Chunksize =  GetChunkSize(ReadLong(file))
        chunkEnd = file.tell() + Chunksize
        if chunkType == 256:
            Hierarchy = ReadHierarchy(file, self, chunkEnd)
            file.seek(chunkEnd, 0)
        else:
            file.seek(Chunksize, 1)
    file.close()
    return Hierarchy
"""
#######################################################################################
# load bone mesh file
#######################################################################################
"""
def loadBoneMesh(self, filepath):
    file = open(filepath,"rb")
    file.seek(0,2)
    filesize = file.tell()
    file.seek(0,0)
    Mesh = struct_w3d.Mesh()

    while file.tell() < filesize:
        Chunktype = ReadLong(file)
        Chunksize =  GetChunkSize(ReadLong(file))
        chunkEnd = file.tell() + Chunksize
        if Chunktype == 0:
            Mesh = ReadMesh(self, file, chunkEnd)
        else:
            file.seek(Chunksize,1)
    file.close()

    Vertices = Mesh.verts
    Faces = []
    for f in Mesh.faces:
        Faces.append(f.vertIds)

    #create the mesh
    mesh = bpy.data.meshes.new("skl_bone")
    mesh.from_pydata(Vertices,[],Faces)
    mesh_ob = bpy.data.objects.new("skl_bone", mesh)
    return mesh
"""
#######################################################################################
# createArmature
#######################################################################################
"""
def createArmature(self, Hierarchy, amtName, subObjects):
    amt = bpy.data.armatures.new(Hierarchy.header.name)
    amt.show_names = True
    rig = bpy.data.objects.new(amtName, amt)
    rig.location = Hierarchy.header.centerPos
    rig.rotation_mode = 'QUATERNION'
    rig.show_x_ray = True
    rig.track_axis = "POS_X"
    bpy.context.scene.objects.link(rig) # Link the object to the active scene
    bpy.context.scene.objects.active = rig
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.context.scene.update()

    non_bone_pivots = []
    for obj in subObjects:
        non_bone_pivots.append(Hierarchy.pivots[obj.boneIndex])

    #create the bones from the pivots
    for pivot in Hierarchy.pivots:
        #test for non_bone_pivots
        if non_bone_pivots.count(pivot) > 0:
                continue #do not create a bone
        bone = amt.edit_bones.new(pivot.name)
        if pivot.parentID > 0:
            parent_pivot =  Hierarchy.pivots[pivot.parentID]
            parent = amt.edit_bones[parent_pivot.name]
            bone.parent = parent
            size = pivot.position.x
        bone.head = Vector((0.0, 0.0, 0.0))
        #has to point in y direction that the rotation is applied correctly
        bone.tail = Vector((0.0, 0.1, 0.0))

    #pose the bones
    bpy.ops.object.mode_set(mode = 'POSE')

    script_directory = os.path.dirname(os.path.abspath(__file__))
    bone_file = script_directory + "\\bone.W3D"

    bone_shape = loadBoneMesh(self, bone_file)

    for pivot in Hierarchy.pivots:
        #test for non_bone_pivots
        if non_bone_pivots.count(pivot) > 0:
                continue #do not create a bone
        bone = rig.pose.bones[pivot.name]
        bone.location = pivot.position
        bone.rotation_mode = 'QUATERNION'
        bone.rotation_euler = pivot.eulerAngles
        bone.rotation_quaternion = pivot.rotation
        #bpy.data.objects["Bone"].scale = (4, 4, 4)
        bone.custom_shape = bpy.data.objects["skl_bone"]

    bpy.ops.object.mode_set(mode = 'OBJECT')

    #delete the mesh afterwards
    for ob in bpy.context.scene.objects:
        if ob.type == 'MESH' and ob.name.startswith("skl_bone"):
            ob.delete()
    return rig
"""
#######################################################################################
# createAnimation
#######################################################################################
"""
def createAnimation(self, Animation, Hierarchy, rig, compressed):
    bpy.data.scenes["Scene"].render.fps = Animation.header.frameRate
    bpy.data.scenes["Scene"].frame_start = 1
    bpy.data.scenes["Scene"].frame_end = Animation.header.numFrames

    #create the data
    translation_data = []
    for pivot in range (0, len(Hierarchy.pivots)):
        pivot = []
        for frame in range (0, Animation.header.numFrames):
            frame = []
            frame.append(None)
            frame.append(None)
            frame.append(None)
            pivot.append(frame)
        translation_data.append(pivot)

    for channel in Animation.channels:
        if (channel.pivot == 0):
            continue   #skip roottransform
        rest_rotation = Hierarchy.pivots[channel.pivot].rotation
        pivot = Hierarchy.pivots[channel.pivot]
        try:
            obj = rig.pose.bones[pivot.name]
        except:
            obj = bpy.data.objects[pivot.name]

        # ANIM_CHANNEL_X
        if channel.type == 0:
            if compressed:
                for key in channel.timeCodedKeys:
                    translation_data[channel.pivot][key.frame][0] = key.value
            else:
                for frame in range(channel.firstFrame, channel.lastFrame):
                    translation_data[channel.pivot][frame][0] = channel.data[frame - channel.firstFrame]
        # ANIM_CHANNEL_Y
        elif channel.type == 1:
            if compressed:
                for key in channel.timeCodedKeys:
                    translation_data[channel.pivot][key.frame][1] = key.value
            else:
                for frame in range(channel.firstFrame, channel.lastFrame):
                    translation_data[channel.pivot][frame][1] = channel.data[frame - channel.firstFrame]
        # ANIM_CHANNEL_Z
        elif channel.type == 2:
            if compressed:
                for key in channel.timeCodedKeys:
                    translation_data[channel.pivot][key.frame][2] = key.value
            else:
                for frame in range(channel.firstFrame, channel.lastFrame):
                    translation_data[channel.pivot][frame][2] = channel.data[frame - channel.firstFrame]

        # ANIM_CHANNEL_Q
        elif channel.type == 6:
            obj.rotation_mode = 'QUATERNION'
            if compressed:
                for key in channel.timeCodedKeys:
                    obj.rotation_quaternion = rest_rotation * key.value
                    obj.keyframe_insert(data_path='rotation_quaternion', frame = key.frame)
            else:
                for frame in range(channel.firstFrame, channel.lastFrame):
                    obj.rotation_quaternion = rest_rotation * channel.data[frame - channel.firstFrame]
                    obj.keyframe_insert(data_path='rotation_quaternion', frame = frame)
        else:
            logger.error("unsupported channel type: %s" %channel.type)
            print("unsupported channel type: %s" %channel.type)

    for pivot in range(1, len(Hierarchy.pivots)):
        rest_location = Hierarchy.pivots[pivot].position
        rest_rotation = Hierarchy.pivots[pivot].rotation
        lastFrameLocation = Vector((0.0, 0.0, 0.0))
        try:
            obj = rig.pose.bones[Hierarchy.pivots[pivot].name]
        except:
            obj = bpy.data.objects[Hierarchy.pivots[pivot].name]

        for frame in range (0, Animation.header.numFrames):
            bpy.context.scene.frame_set(frame)
            pos = Vector((0.0, 0.0, 0.0))

            if not translation_data[pivot][frame][0] == None:
                pos[0] = translation_data[pivot][frame][0]
                if not translation_data[pivot][frame][1] == None:
                    pos[1] = translation_data[pivot][frame][1]
                if not translation_data[pivot][frame][2] == None:
                    pos[2] = translation_data[pivot][frame][2]
                obj.location = rest_location + (rest_rotation * pos)
                obj.keyframe_insert(data_path='location', frame = frame)
                lastFrameLocation = pos

            elif not translation_data[pivot][frame][1] == None:
                pos[1] = translation_data[pivot][frame][1]
                if not translation_data[pivot][frame][2] == None:
                    pos[2] = translation_data[pivot][frame][2]
                obj.location = rest_location + (rest_rotation * pos)
                obj.keyframe_insert(data_path='location', frame = frame)
                lastFrameLocation = pos

            elif not translation_data[pivot][frame][2] == None:
                pos[2] = translation_data[pivot][frame][2]
                obj.location = rest_location + (rest_rotation * pos)
                obj.keyframe_insert(data_path='location', frame = frame)
                lastFrameLocation = pos
"""
