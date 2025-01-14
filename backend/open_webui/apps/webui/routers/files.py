import logging
import multiprocessing
import os
import shutil
import uuid
from datetime import time
from pathlib import Path
from typing import Optional

import oss2
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse

from open_webui.apps.webui.models.files import Files, FileForm, FileModel
from open_webui.config import (
    UPLOAD_DIR,
    MODEL_IMAGES_DIR,
    BACKGROUND_IMAGES_DIR,
    USER_IMAGES_DIR,
    RAG_FILE_MAX_SIZE,
    OSS_ENABLE_STORAGE,
    OSS_ACCESS_KEY,
    OSS_ACCESS_SECRET,
    OSS_ENDPOINT,
    OSS_BUCKET_NAME,
    AppConfig,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.utils import get_verified_user, get_admin_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()
config = AppConfig()
config.FILE_MAX_SIZE = RAG_FILE_MAX_SIZE
config.OSS_ENABLE_STORAGE = OSS_ENABLE_STORAGE
config.OSS_ACCESS_KEY = OSS_ACCESS_KEY
config.OSS_ACCESS_SECRET = OSS_ACCESS_SECRET
config.OSS_ENDPOINT = OSS_ENDPOINT
config.OSS_BUCKET_NAME = OSS_BUCKET_NAME


# 创建 OSS Bucket 对象
auth = oss2.Auth(config.OSS_ACCESS_KEY, config.OSS_ACCESS_SECRET)
bucket = oss2.Bucket(
    auth, config.OSS_ENDPOINT, config.OSS_BUCKET_NAME, connect_timeout=10
)

############################
# Upload File
############################


@router.post("/")
def upload_file(file: UploadFile = File(...), user=Depends(get_verified_user)):
    log.info(f"file.content_type: {file.content_type}")
    try:
        # Check file size without reading into memory
        file_size = os.fstat(file.file.fileno()).st_size
        if file_size > config.FILE_MAX_SIZE * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=ERROR_MESSAGES.DEFAULT("Uploaded file is too large."),
            )

        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)

        # Replace filename with UUID
        id = str(uuid.uuid4())
        name = filename
        filename = f"{id}_{filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with file.file as source_file:
            contents = source_file.read()

        with open(file_path, "wb") as f:
            f.write(contents)

        # Insert file record into the database
        file_record = Files.insert_new_file(
            user.id,
            FileForm(
                **{
                    "id": id,
                    "filename": filename,
                    "meta": {
                        "name": name,
                        "content_type": file.content_type,
                        "size": file_size,
                        "path": file_path,
                    },
                }
            ),
        )

        if file_record:
            return file_record
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error uploading file."),
            )

    except HTTPException as http_exc:
        log.error(f"HTTP error during file upload: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        log.exception(f"Unexpected error during file upload for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT("An unexpected error occurred."),
        )


# background Images
def save_file(file: UploadFile, oss_directory: str) -> dict:
    log.info(f"file.content_type: {file.content_type}")
    try:
        # 获取文件名并拼接 OSS 路径
        filename = os.path.basename(file.filename)
        oss_file_path = os.path.join(oss_directory, filename)

        # 读取文件内容
        with file.file as source_file:
            contents = source_file.read()

        with open(oss_file_path, "wb") as f:
            f.write(contents)

        # 获取文件元信息
        file_size = len(contents)

        if config.OSS_ENABLE_STORAGE:
            # 上传文件到 OSS，带有超时控制
            bucket.put_object_from_file(filename, oss_file_path)

            # 设置文件为公共读
            bucket.put_object_acl(filename, "public-read")

            # 生成文件的 URL
            oss_file_url = f"https://{config.OSS_BUCKET_NAME}.{config.OSS_ENDPOINT.replace('https://', '')}/{filename}"

            log.info(f"File uploaded to OSS: {oss_file_path}, Size: {file_size} bytes")

            # 返回上传结果
            return {
                "filename": filename,
                "meta": {
                    "name": filename,
                    "content_type": file.content_type,
                    "size": file_size,
                    "path": oss_file_path,
                    "oss_path": oss_file_path,
                    "oss_url": oss_file_url,
                },
            }
        else:
            return {
                "filename": filename,
                "meta": {
                    "name": filename,
                    "content_type": file.content_type,
                    "size": len(contents),
                    "path": oss_file_path,
                },
            }

    except oss2.exceptions.RequestError as e:
        log.error(f"File upload request error: {str(e)}")
        return {
            "filename": filename,
            "meta": {
                "name": filename,
                "content_type": file.content_type,
                "size": len(contents),
                "path": oss_file_path,
            },
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error uploading file to OSS: {str(e)}",
        )


# Model Images
@router.post("/model/images")
def upload_model_image(file: UploadFile = File(...), user=Depends(get_admin_user)):
    return save_file(file, MODEL_IMAGES_DIR)


# Background Images
@router.post("/background/images")
def upload_background_image(
    file: UploadFile = File(...), user=Depends(get_verified_user)
):
    return save_file(file, BACKGROUND_IMAGES_DIR)


# User Images
@router.post("/user/images")
def upload_user_image(file: UploadFile = File(...), user=Depends(get_verified_user)):
    return save_file(file, USER_IMAGES_DIR)


############################
# List Files
############################


@router.get("/", response_model=list[FileModel])
async def list_files(user=Depends(get_verified_user)):
    if user.role == "admin":
        files = Files.get_files()
    else:
        files = Files.get_files_by_user_id(user.id)
    return files


############################
# Delete All Files
############################


@router.delete("/all")
async def delete_all_files(user=Depends(get_admin_user)):
    result = Files.delete_all_files()

    if result:
        folder = f"{UPLOAD_DIR}"
        try:
            # Check if the directory exists
            if os.path.exists(folder):
                # Iterate over all the files and directories in the specified directory
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)  # Remove the file or link
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)  # Remove the directory
                    except Exception as e:
                        print(f"Failed to delete {file_path}. Reason: {e}")
            else:
                print(f"The directory {folder} does not exist")
        except Exception as e:
            print(f"Failed to process the directory {folder}. Reason: {e}")

        return {"message": "All files deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
        )


############################
# Get File By Id
############################


@router.get("/{id}", response_model=Optional[FileModel])
async def get_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if file and (file.user_id == user.id or user.role == "admin"):
        return file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Content By Id
############################


@router.get("/{id}/content", response_model=Optional[FileModel])
async def get_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if file and (file.user_id == user.id or user.role == "admin"):
        file_path = Path(file.meta["path"])

        # Check if the file already exists in the cache
        if file_path.is_file():
            log.debug(f"file_path: {file_path}")
            return FileResponse(file_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/preview", response_model=Optional[FileModel])
async def get_file_content_by_id(id: str):
    file = Files.get_file_by_id(id)

    if file:
        file_path = Path(file.meta["path"])

        # Check if the file already exists in the cache
        if file_path.is_file():
            log.debug(f"file_path: {file_path}")
            return FileResponse(file_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


# Get File Response
def get_file_response(directory: str, filename: str) -> FileResponse:
    file_path = Path(directory) / filename
    if file_path.is_file():
        return FileResponse(file_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


# Model Images
@router.get("/model/images/{filename}", response_model=Optional[FileModel])
async def get_model_image_by_filename(filename: str):
    return get_file_response(MODEL_IMAGES_DIR, filename)


# Background Images
@router.get("/background/images/{filename}", response_model=Optional[FileModel])
async def get_background_image_by_filename(filename: str):
    return get_file_response(BACKGROUND_IMAGES_DIR, filename)


# User Images
@router.get("/user/images/{filename}", response_model=Optional[FileModel])
async def get_user_image_by_filename(filename: str):
    return get_file_response(USER_IMAGES_DIR, filename)


@router.get("/{id}/content/{file_name}", response_model=Optional[FileModel])
async def get_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if file and (file.user_id == user.id or user.role == "admin"):
        file_path = Path(file.meta["path"])

        # Check if the file already exists in the cache
        if file_path.is_file():
            log.debug(f"file_path: {file_path}")
            return FileResponse(file_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Delete File By Id
############################


@router.delete("/{id}")
async def delete_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)
    if file and (file.user_id == user.id or user.role == "admin"):
        result = Files.delete_file_by_id(id)
        if result:
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting file"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
