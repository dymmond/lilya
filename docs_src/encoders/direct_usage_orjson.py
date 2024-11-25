from lilya.encoders import json_encode
import orjson

# orjson serializes to bytes, so apply str
json_string = json_encode({"hello": "world"}, json_encode_fn=orjson.dumps, post_transform_fn=str)
# or for simplifying
json_simplified = json_encode({"hello": "world"}, json_encode_fn=orjson.dumps, post_transform_fn=orjson.loads)
