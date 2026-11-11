BOOK = {
    "type": "object",
    "required": [
        "isbn", "title", "subTitle", "author", "publish_date",
        "publisher", "pages", "description", "website",
    ],
    "properties": {
        "isbn": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "subTitle": {"type": "string"},
        "author": {"type": "string", "minLength": 1},
        "publish_date": {"type": "string", "format": "date-time"},
        "publisher": {"type": "string", "minLength": 1},
        "pages": {"type": "number", "minimum": 0},
        "description": {"type": "string"},
        "website": {"type": "string", "format": "uri"},
    },
}
CATALOG = {
    "type": "object", "required": ["books"],
    "properties": {"books": {"type": "array", "items": BOOK}},
}
PROFILE = {
    "type": "object", "required": ["userId", "username", "books"],
    "properties": {
        "userId": {"type": "string", "format": "uuid"},
        "username": {"type": "string", "minLength": 1},
        "books": {"type": "array", "items": BOOK},
    },
}
ERROR = {
    "type": "object", "required": ["code", "message"],
    "properties": {
        "code": {"type": "string", "pattern": "^[0-9]+$"},
        "message": {"type": "string", "minLength": 1},
    },
}
USER_CREATED = {
    "type": "object", "required": ["userID", "username", "books"],
    "properties": {
        "userID": {"type": "string", "format": "uuid"},
        "username": {"type": "string", "minLength": 1},
        "books": {"type": "array", "items": BOOK},
    },
}
TOKEN_RESULT = {
    "type": "object", "required": ["token", "expires", "status", "result"],
    "properties": {
        "token": {"type": ["string", "null"], "minLength": 1},
        "expires": {"type": ["string", "null"], "format": "date-time"},
        "status": {"enum": ["Success", "Failed"]},
        "result": {"type": "string", "minLength": 1},
    },
    "if": {"properties": {"status": {"const": "Success"}}},
    "then": {"properties": {"token": {"type": "string"}, "expires": {"type": "string"}}},
    "else": {"properties": {"token": {"type": "null"}, "expires": {"type": "null"}}},
}
ADDED_BOOKS = {
    "type": "object", "required": ["books"],
    "properties": {
        "books": {"type": "array", "items": {
            "type": "object", "required": ["isbn"],
            "properties": {"isbn": {"type": "string", "minLength": 1}},
        }},
    },
}
