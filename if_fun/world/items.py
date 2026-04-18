"""Item definitions.

ItemDef is the minimal static metadata a Phase A world needs to render
item prose. WorldState holds a `dict[ItemId, ItemDef]` registry; rooms and
inventories still only carry ItemId references, so the registry is the
single source of truth for display name and examine text.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from if_fun.ids import ItemId

Article = Literal["a", "an", "the", ""]


class ItemDef(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: ItemId
    display_name: str
    article: Article
    short_description: str

    def indefinite(self) -> str:
        """Render as article + display_name, collapsing empty articles."""
        return f"{self.article} {self.display_name}".strip()
