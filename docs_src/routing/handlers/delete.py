from lilya.app import Lilya
from lilya.routing import Include, Path


def delete_item(item_id: int):
    # logic that deletes an item
    ...


def another_delete(item_id: int):
    # logic that deletes an item
    ...


app = Lilya(
    routes=[
        Include(
            "/delete",
            routes=[
                Path(
                    "/{item_id:int}",
                    handler=delete_item,
                    methods=["DELETE"],
                ),
                Path(
                    "/last/{item_id:int}",
                    handler=another_delete,
                    methods=["DELETE"],
                ),
            ],
        ),
    ]
)
