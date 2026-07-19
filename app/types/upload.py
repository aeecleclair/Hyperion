from typing import Annotated, Any

from fastapi import File
from fastapi import UploadFile as _UploadFile
from pydantic import WithJsonSchema

# Drop-in replacement for `fastapi.UploadFile` for a **required** uploaded file.
# Use it bare in a path operation, no `File(...)` default needed:
#
#     from app.types.upload import UploadFile
#
#     async def endpoint(image: UploadFile): ...
#
# Two things are baked in:
#
# 1. `File()` — so the parameter is read from multipart/form-data. Keeping it
#    inside `Annotated` (rather than as a `= File(...)` default) is required:
#    a default value drops the annotation metadata below, which would revert the
#    schema to the broken form for single-file parameters.
#
# 2. `WithJsonSchema({"type": "string", "format": "binary"})` — since FastAPI
#    0.129.1 (PR fastapi/fastapi#14953) `UploadFile` fields are serialized with
#    the JSON Schema 2020-12 / OAS 3.1 form
#    `{"type": "string", "contentMediaType": "application/octet-stream"}` instead
#    of the OAS 3.0 `{"type": "string", "format": "binary"}`. That is
#    spec-compliant and will not be reverted upstream, but Swagger UI and several
#    OpenAPI client generators still rely on `format: "binary"` to recognize a
#    file field; without it they render a plain text input and generate `string`
#    instead of a file type. We restore it with the recommended workaround from
#    fastapi/fastapi#14975.
UploadFile = Annotated[
    _UploadFile,
    File(),
    WithJsonSchema({"type": "string", "format": "binary"}),
]


# OpenAPI `responses=` entry for path operations that stream a binary file with
# FastAPI's `FileResponse`. FastAPI cannot infer a media type for `FileResponse`
# (it is resolved at runtime from the served file), so the generated success
# response has no `content` block at all, and OpenAPI/Swagger client generators
# fail on it. We declare a generic binary body explicitly, mirroring the
# `format: "binary"` handling used for `UploadFile` above.
#
# Runtime behaviour is unaffected: the endpoints return their own `FileResponse`
# with the real media type; this only documents the response in the schema.
#
# Usage:
#     @router.get(..., response_class=FileResponse, responses=FILE_RESPONSE)
FILE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {
            "application/octet-stream": {
                "schema": {"type": "string", "format": "binary"},
            },
        },
    },
}
