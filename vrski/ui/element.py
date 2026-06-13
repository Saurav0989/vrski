from dataclasses import dataclass, asdict
from typing import Dict, Any
import logging

logger = logging.getLogger("vrski.ui.element")

EDITABLE_TYPES = {
    "EditText",
    "AutoCompleteTextView",
    "MultiAutoCompleteTextView",
    "SearchAutoComplete",
    "TextInputEditText",
    "AppCompatEditText",
}


def is_editable_type(element_type: str) -> bool:
    """True only for real text-input widget classes.

    Deliberately does NOT treat 'focusable non-TextView' as editable — that
    heuristic flagged ordinary clickable Views as input fields (finding #5),
    which made `editable` useless as a signal for agents.
    """
    et = element_type or ""
    return "EditText" in et or et in EDITABLE_TYPES


@dataclass
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self):
        # Gracefully handle non-integer types and convert them if possible
        for field in ["left", "top", "right", "bottom"]:
            val = getattr(self, field)
            try:
                setattr(self, field, int(val))
            except (ValueError, TypeError):
                try:
                    setattr(self, field, int(float(val)))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Malformed coordinate '{field}' value '{val}' in Bounds: {e}. Falling back to 0.")
                    setattr(self, field, 0)

        # Normalize bounds: ensure left <= right and top <= bottom
        if self.left > self.right:
            logger.warning(f"Malformed bounds: left ({self.left}) > right ({self.right}). Swapping them.")
            self.left, self.right = self.right, self.left
        if self.top > self.bottom:
            logger.warning(f"Malformed bounds: top ({self.top}) > bottom ({self.bottom}). Swapping them.")
            self.top, self.bottom = self.bottom, self.top

    @property
    def center_x(self) -> int:
        # Clamp negative center coordinates to 0 to prevent clicking off-screen/errors
        cx = (self.left + self.right) // 2
        return max(0, cx)

    @property
    def center_y(self) -> int:
        cy = (self.top + self.bottom) // 2
        return max(0, cy)

    def to_dict(self) -> Dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom
        }

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "Bounds":
        if not data:
            logger.warning("Empty dictionary passed to Bounds.from_dict, falling back to zeros.")
            return cls(left=0, top=0, right=0, bottom=0)
        return cls(
            left=data.get("left", 0),
            top=data.get("top", 0),
            right=data.get("right", 0),
            bottom=data.get("bottom", 0)
        )


@dataclass
class UIElement:
    element_id: str        # resource-id (e.g. "com.android.settings:id/title")
    element_type: str      # simplified class name ("Button", "EditText", etc.)
    text: str
    content_desc: str
    clickable: bool
    scrollable: bool
    editable: bool
    bounds: Bounds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.element_id,
            "type": self.element_type,
            "text": self.text,
            "content_desc": self.content_desc,
            "clickable": self.clickable,
            "scrollable": self.scrollable,
            "editable": self.editable,
            "bounds": self.bounds.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UIElement":
        return cls(
            element_id=data.get("id", ""),
            element_type=data.get("type", ""),
            text=data.get("text", ""),
            content_desc=data.get("content_desc", ""),
            clickable=bool(data.get("clickable", False)),
            scrollable=bool(data.get("scrollable", False)),
            editable=bool(data.get("editable", False)),
            bounds=Bounds.from_dict(data["bounds"])
        )
