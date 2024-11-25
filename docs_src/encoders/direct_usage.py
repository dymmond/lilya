from lilya.encoders import json_encode

json_string = json_encode({"hello": "world"}, post_transform_fn=None)
# or
json_string = json_encode({"hello": "world"}, post_transform_fn=lambda x: x)
