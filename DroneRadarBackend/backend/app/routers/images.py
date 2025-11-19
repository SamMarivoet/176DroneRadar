from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
from bson import ObjectId
from .. import database

router = APIRouter(prefix="/images", tags=["images"])


@router.post('')
async def upload_image(file: UploadFile = File(...), icao: Optional[str] = Form(None)):
    """Upload an image and store it in GridFS. Returns an image_id string."""
    try:
        bucket = database.gridfs_bucket
        if bucket is None:
            raise HTTPException(status_code=500, detail='GridFS not initialized')

        oid = await bucket.upload_from_stream(
            file.filename or 'image',
            file.file,
            metadata={'contentType': file.content_type, 'icao': icao}
        )
        return {'image_id': str(oid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{image_id}')
async def get_image(image_id: str):
    """Stream an image stored in GridFS by its id."""
    try:
        oid = ObjectId(image_id)
    except Exception:
        raise HTTPException(status_code=400, detail='invalid id')

    try:
        files_coll = database.db['fs.files']
        info = await files_coll.find_one({'_id': oid})
        if not info:
            raise HTTPException(status_code=404, detail='not found')

        content_type = (info.get('metadata') or {}).get('contentType') or info.get('contentType') or 'application/octet-stream'
        stream = await database.gridfs_bucket.open_download_stream(oid)

        async def streamer():
            chunk_size = 8192
            while True:
                chunk = await stream.read(chunk_size)
                if not chunk:
                    break
                yield chunk

        return StreamingResponse(streamer(), media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))