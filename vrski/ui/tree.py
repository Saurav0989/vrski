"""
Thin public interface for the UI tree.

DeviceDriver.get_tree() is the actual implementation. This module re-exports
the parser and provides a standalone parse_tree() function for callers that
have raw XML but no live device connection.
"""
from typing import List
from vrski.ui.driver import parse_bounds
from vrski.ui.element import UIElement, Bounds
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger("vrski.ui.tree")


def parse_tree(xml_str: str) -> List[UIElement]:
    """Parses a raw uiautomator2 XML hierarchy string into a list of UIElements."""
    elements = []
    try:
        root = ET.fromstring(xml_str)
        for node in root.iter("node"):
            attrib = node.attrib
            bounds_str = attrib.get("bounds", "")
            bounds = parse_bounds(bounds_str)
            if not bounds:
                continue

            element_id = attrib.get("resource-id", "")
            class_name = attrib.get("class", "")
            element_type = class_name.split(".")[-1] if class_name else "View"
            text = attrib.get("text", "")
            content_desc = attrib.get("content-desc", "")

            clickable = attrib.get("clickable", "false").lower() == "true"
            scrollable = attrib.get("scrollable", "false").lower() == "true"
            editable = (
                "EditText" in element_type
                or element_type in ["AutoCompleteTextView", "MultiAutoCompleteTextView", "SearchAutoComplete"]
                or (attrib.get("focusable", "false").lower() == "true" and "TextView" not in element_type)
            )

            elements.append(UIElement(
                element_id=element_id,
                element_type=element_type,
                text=text,
                content_desc=content_desc,
                clickable=clickable,
                scrollable=scrollable,
                editable=editable,
                bounds=bounds,
            ))
    except Exception as e:
        logger.error(f"Failed to parse hierarchy XML: {e}")
    return elements
