from enum import Enum


class SceneEnum(str, Enum):
    TEXT2VIDEO = "Text2Video"
    TEXT2IMAGE = "Text2Image"
    IMAGE2IMAGE = "Image2Image"


class AlgorithmSceneEnum(str, Enum):
    T2V = "t2v"
    T2I = "t2i"
    I2I = "i2i"


class StoreTypeEnum(str, Enum):
    FOLDER = "Folder"
    DATABASE = "DataBase"
    LONGVIDEO = "LongVideo"


class StoreStatusEnum(str, Enum):
    NOT_READY = "not_ready"
    PREPARING = "preparing"
    READY = "ready"
    FAILED = "failed"


class JobStateEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TERMINATED = "terminated"


class PreprocessModeEnum(str, Enum):
    SEGMENT = "segment"
    FRAME = "frame"


LONGVIDEO_SEGMENT_INTERVAL_OPTIONS = {1, 3, 5, 10, 30, 60}
LONGVIDEO_FRAME_INTERVAL_OPTIONS = {1, 3, 5, 10, 30}


def to_algorithm_scene(scene: str) -> str:
    mapping = {
        SceneEnum.TEXT2VIDEO.value: AlgorithmSceneEnum.T2V.value,
        SceneEnum.TEXT2IMAGE.value: AlgorithmSceneEnum.T2I.value,
        SceneEnum.IMAGE2IMAGE.value: AlgorithmSceneEnum.I2I.value,
        AlgorithmSceneEnum.T2V.value: AlgorithmSceneEnum.T2V.value,
        AlgorithmSceneEnum.T2I.value: AlgorithmSceneEnum.T2I.value,
        AlgorithmSceneEnum.I2I.value: AlgorithmSceneEnum.I2I.value,
    }
    if scene not in mapping:
        raise ValueError(f"Unsupported scene: {scene}")
    return mapping[scene]


def default_preprocess_mode_for_scene(scene: str) -> str:
    if scene == SceneEnum.TEXT2VIDEO.value:
        return PreprocessModeEnum.SEGMENT.value
    if scene in {SceneEnum.TEXT2IMAGE.value, SceneEnum.IMAGE2IMAGE.value}:
        return PreprocessModeEnum.FRAME.value
    raise ValueError(f"Unsupported scene for preprocess mode: {scene}")
