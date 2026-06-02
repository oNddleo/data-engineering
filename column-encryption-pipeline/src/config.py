import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # KMS
    kms_mode: str = field(default_factory=lambda: os.getenv("KMS_MODE", "local"))
    local_kms_store_path: str = field(
        default_factory=lambda: os.getenv("LOCAL_KMS_STORE_PATH", "./data/kms_store.json")
    )
    local_kms_master_key_path: str = field(
        default_factory=lambda: os.getenv("LOCAL_KMS_MASTER_KEY_PATH", "./data/master.key")
    )
    kms_endpoint_url: str | None = field(default_factory=lambda: os.getenv("KMS_ENDPOINT_URL"))
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))
    aws_access_key_id: str = field(default_factory=lambda: os.getenv("AWS_ACCESS_KEY_ID", "test"))
    aws_secret_access_key: str = field(
        default_factory=lambda: os.getenv("AWS_SECRET_ACCESS_KEY", "test")
    )

    # Storage
    storage_mode: str = field(default_factory=lambda: os.getenv("STORAGE_MODE", "local"))
    local_storage_path: str = field(
        default_factory=lambda: os.getenv("LOCAL_STORAGE_PATH", "./data/records")
    )
    s3_endpoint_url: str | None = field(default_factory=lambda: os.getenv("S3_ENDPOINT_URL"))
    s3_bucket: str = field(default_factory=lambda: os.getenv("S3_BUCKET", "encrypted-pii-records"))

    # Key registry
    key_registry_path: str = field(
        default_factory=lambda: os.getenv("KEY_REGISTRY_PATH", "./data/key_registry.json")
    )

    # Rotation
    rotation_batch_size: int = field(
        default_factory=lambda: int(os.getenv("ROTATION_BATCH_SIZE", "50"))
    )
    dual_read_window_seconds: int = field(
        default_factory=lambda: int(os.getenv("DUAL_READ_WINDOW_SECONDS", "30"))
    )


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
